"""技術ニュースのRSSフィードを監視・収集・要約するサービス。"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import feedparser
import tomli
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.daily_merge import merge_records
from nook.common.date_utils import is_within_target_dates, target_dates_set
from nook.common.dedup import DedupTracker, load_existing_titles_from_storage
from nook.common.feed_utils import parse_entry_datetime


@dataclass
class Article:
    """
    技術ニュースの記事情報。

    Parameters
    ----------
    feed_name : str
        フィード名。
    title : str
        タイトル。
    url : str
        URL。
    text : str
        本文。
    soup : BeautifulSoup
        BeautifulSoupオブジェクト。
    category : str | None
        カテゴリ。
    """

    feed_name: str
    title: str
    url: str
    text: str
    soup: BeautifulSoup
    category: str | None = None
    summary: str = field(default="")
    popularity_score: float = field(default=0.0)
    published_at: datetime | None = None


class TechFeed(BaseService):
    """
    技術ニュースのRSSフィードを監視・収集・要約するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    TOTAL_LIMIT = 15

    def __init__(self, storage_dir: str = "data"):
        """
        TechFeedを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("tech_feed")
        self.http_client = None  # setup_http_clientで初期化

        # フィードの設定を読み込む
        script_dir = Path(__file__).parent
        with open(script_dir / "feed.toml", "rb") as f:
            self.feed_config = tomli.load(f)

    def run(self, days: int = 1, limit: int | None = None) -> None:
        """
        技術ニュースのRSSフィードを監視・収集・要約して保存します。

        Parameters
        ----------
        days : int, default=1
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            各フィードから取得する記事数。Noneの場合は制限なし。
        """
        asyncio.run(self.collect(days, limit))

    async def collect(
        self,
        days: int = 1,
        limit: int | None = None,
        *,
        target_dates: set[date] | None = None,
    ) -> list[tuple[str, str]]:
        """
        技術ニュースのRSSフィードを監視・収集・要約して保存します（非同期版）。

        Parameters
        ----------
        days : int, default=1
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            各フィードから取得する記事数。Noneの場合は制限なし。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        total_limit = self.TOTAL_LIMIT
        effective_target_dates = target_dates or target_dates_set(days)
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_articles: list[Article] = []

        # カテゴリ横断のタイトル重複チェック用（既存ファイルからロード）
        dedup_tracker = await load_existing_titles_from_storage(
            self.storage, effective_target_dates, self.logger
        )

        try:
            # 各カテゴリのフィードから記事を取得
            for category, feeds in self.feed_config.items():
                self.logger.info(f"カテゴリ {category} の処理を開始します...")
                for feed_url in feeds:
                    try:
                        # フィードを解析
                        self.logger.info(f"フィード {feed_url} を解析しています...")
                        feed = feedparser.parse(feed_url)
                        feed_name = (
                            feed.feed.title
                            if hasattr(feed, "feed") and hasattr(feed.feed, "title")
                            else feed_url
                        )

                        # 新しいエントリをフィルタリング
                        effective_limit = limit
                        if effective_limit is not None:
                            effective_limit = effective_limit * max(days, 1)

                        entries = self._filter_entries(
                            feed.entries,
                            effective_target_dates,
                            effective_limit,
                        )
                        self.logger.info(
                            f"フィード {feed_name} から {len(entries)} 件のエントリを取得しました"
                        )

                        for entry in entries:
                            entry_title = (
                                entry.title if hasattr(entry, "title") else "無題"
                            )

                            is_dup, normalized = dedup_tracker.is_duplicate(entry_title)
                            if is_dup:
                                original = (
                                    dedup_tracker.get_original_title(normalized)
                                    or entry_title
                                )
                                self.logger.info(
                                    "重複記事をスキップ: '%s' (初出: '%s')",
                                    entry_title,
                                    original,
                                )
                                continue

                            article = await self._retrieve_article(
                                entry, feed_name, category
                            )
                            if article:
                                if not is_within_target_dates(
                                    article.published_at, effective_target_dates
                                ):
                                    continue
                                dedup_tracker.add(article.title)
                                candidate_articles.append(article)

                    except Exception as e:
                        self.logger.error(f"Error processing feed {feed_url}: {str(e)}")

            self.logger.info(
                f"合計 {len(candidate_articles)} 件の記事候補を取得しました"
            )

            # 日付ごとにグループ化
            articles_by_date = self._group_articles_by_date(candidate_articles)

            # 日付ごとに上位N件を選択して要約（古い日付から新しい日付へ）
            saved_files: list[tuple[str, str]] = []
            for date_str in sorted(articles_by_date.keys()):
                date_articles = articles_by_date[date_str]

                # その日の既存記事タイトルを取得
                existing_titles_for_date = set()
                try:
                    json_content = await self.storage.load(f"{date_str}.json")
                    if json_content:
                        existing_articles = json.loads(json_content)
                        existing_titles_for_date = {
                            article.get("title", "") for article in existing_articles
                        }
                except Exception as e:
                    # ファイルが存在しない場合は空のセット
                    self.logger.debug(
                        f"既存記事ファイル {date_str}.json の読み込みに失敗しました: {e}"
                    )

                # 既存/新規記事数をカウント
                existing_count = len(existing_titles_for_date)
                new_count = len(date_articles)

                # 日付情報を先頭に表示
                self.logger.info(
                    f"\n📰 [{date_str}] の記事を処理中... (既存: {existing_count}件, 新規: {new_count}件)"
                )

                # 新規記事のみを要約対象として選択
                selected = self._select_top_articles(date_articles, total_limit)

                if selected:
                    self.logger.info(f"   ✅ 選択: {len(selected)}件")
                    for article in selected:
                        await self._summarize_article(article)

                    # この日付の記事をすぐに保存
                    json_path, md_path = await self._store_summaries_for_date(
                        selected, date_str
                    )
                    self.logger.info(f"   💾 保存完了: {json_path}, {md_path}")
                    saved_files.append((json_path, md_path))
                else:
                    self.logger.info(f"   ℹ️  新規記事がありません")

            # 処理完了メッセージ
            if saved_files:
                self.logger.info(f"\n💾 {len(saved_files)}日分のデータを保存完了")
            else:
                self.logger.info("\n保存する記事がありません")

            return saved_files

        finally:
            # グローバルクライアントなのでクローズ不要
            pass

    def _group_articles_by_date(
        self, articles: list[Article]
    ) -> dict[str, list[Article]]:
        """記事を日付ごとにグループ化します。"""
        by_date: dict[str, list[Article]] = {}
        default_date = datetime.now().strftime("%Y-%m-%d")

        for article in articles:
            date_key = (
                article.published_at.strftime("%Y-%m-%d")
                if article.published_at
                else default_date
            )
            by_date.setdefault(date_key, []).append(article)

        return by_date

    def _filter_entries(
        self, entries: list[dict], target_dates: set[date], limit: int | None
    ) -> list[dict]:
        """
        新しいエントリをフィルタリングします。

        Parameters
        ----------
        entries : List[dict]
            エントリのリスト。
        days : int
            何日前までの記事を取得するか。
        limit : Optional[int]
            取得する記事数。Noneの場合は制限なし。

        Returns
        -------
        List[dict]
            フィルタリングされたエントリのリスト。
        """
        self.logger.info(f"エントリのフィルタリングを開始します({len(entries)}件)...")

        # 日付でフィルタリング
        recent_entries = []

        for entry in entries:
            entry_date = parse_entry_datetime(entry)

            if entry_date:
                if is_within_target_dates(entry_date, target_dates):
                    recent_entries.append(entry)
                else:
                    self.logger.debug(
                        "対象外日付の記事をスキップします。 raw=%s",
                        getattr(entry, "published", getattr(entry, "updated", "")),
                    )
            else:
                self.logger.debug(
                    "エントリに日付情報がありません。含めます。 raw=%s",
                    getattr(entry, "published", getattr(entry, "updated", "")),
                )
                recent_entries.append(entry)

        self.logger.info(f"フィルタリング後のエントリ数: {len(recent_entries)}")

        if limit is None:
            return recent_entries

        return recent_entries[:limit]

    async def _retrieve_article(
        self, entry: dict, feed_name: str, category: str
    ) -> Article | None:
        """
        記事を取得します。

        Parameters
        ----------
        entry : dict
            エントリ情報。
        feed_name : str
            フィード名。
        category : str
            カテゴリ。

        Returns
        -------
        Article or None
            取得した記事。取得に失敗した場合はNone。
        """
        try:
            # URLを取得
            url = entry.link if hasattr(entry, "link") else None
            if not url:
                return None

            # タイトルを取得
            title = entry.title if hasattr(entry, "title") else "無題"

            # 記事の内容を取得
            response = await self.http_client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # 日本語記事かどうかを判定
            is_japanese = self._detect_japanese_content(soup, title, entry)

            if not is_japanese:
                self.logger.debug(f"日本語でない記事をスキップします: {title}")
                return None

            # 本文を抽出
            text = ""

            # まずはエントリの要約を使用
            if hasattr(entry, "summary"):
                text = entry.summary

            # 次に記事の本文を抽出
            if not text:
                # メタディスクリプションを取得
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    text = meta_desc.get("content")
                else:
                    # 本文の最初の段落を取得
                    paragraphs = soup.find_all("p")
                    if paragraphs:
                        text = "\n".join([p.get_text() for p in paragraphs[:5]])

            published_at = parse_entry_datetime(entry)
            popularity_score = self._extract_popularity(entry, soup)

            return Article(
                feed_name=feed_name,
                title=title,
                url=url,
                text=text,
                soup=soup,
                category=category,
                popularity_score=popularity_score,
                published_at=published_at,
            )

        except Exception as e:
            self.logger.error(
                f"Error retrieving article {entry.get('link', 'unknown')}: {str(e)}"
            )
            return None

    def _load_existing_titles(self) -> DedupTracker:
        tracker = DedupTracker()
        try:
            content = self.storage.load_markdown("", datetime.now())
            if content:
                for match in re.finditer(r"^### \[(.+?)\]", content, re.MULTILINE):
                    tracker.add(match.group(1))
        except Exception as exc:
            self.logger.debug(f"既存タイトルの読み込みに失敗しました: {exc}")
        return tracker

    def _extract_popularity(self, entry, soup: BeautifulSoup) -> float:
        candidates: list[int] = []

        for attr in [
            "slash_comments",
            "comments",
            "engagement",
            "likes",
            "favorites",
        ]:
            value = getattr(entry, attr, None)
            if value is None and isinstance(entry, dict):
                value = entry.get(attr)
            parsed = self._safe_parse_int(value)
            if parsed is not None:
                candidates.append(parsed)

        for meta_name in [
            "og:likes",
            "og:rating",
            "twitter:data1",
            "likes",
            "favorites",
        ]:
            meta_tag = soup.find("meta", attrs={"name": meta_name}) or soup.find(
                "meta", attrs={"property": meta_name}
            )
            if meta_tag and meta_tag.get("content"):
                parsed = self._safe_parse_int(meta_tag.get("content"))
                if parsed is not None:
                    candidates.append(parsed)

        for attr in ["data-like-count", "data-favorite-count", "data-score"]:
            for element in soup.select(f"[{attr}]"):
                parsed = self._safe_parse_int(element.get(attr))
                if parsed is not None:
                    candidates.append(parsed)

        if candidates:
            return float(max(candidates))

        published = parse_entry_datetime(entry)
        if published:
            return published.timestamp()

        return 0.0

    def _safe_parse_int(self, value) -> int | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "")
            digits = ""
            for char in cleaned:
                if char.isdigit() or (char == "-" and not digits):
                    digits += char
                elif digits:
                    break
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return None
        return None

    def _select_top_articles(
        self, articles: list[Article], limit: int
    ) -> list[Article]:
        if not articles:
            return []

        if len(articles) <= limit:
            return articles

        def sort_key(article: Article):
            published = article.published_at or datetime.min
            return (article.popularity_score, published)

        sorted_articles = sorted(articles, key=sort_key, reverse=True)
        return sorted_articles[:limit]

    def _detect_japanese_content(self, soup, title, entry) -> bool:
        """
        記事が日本語であるかどうかを判定します。

        Parameters
        ----------
        soup : BeautifulSoup
            記事のHTMLパーサー。
        title : str
            記事のタイトル。
        entry : dict
            エントリ情報。

        Returns
        -------
        bool
            日本語記事であればTrue、そうでなければFalse。
        """
        # 方法1: HTMLのlang属性をチェック
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            lang = html_tag.get("lang").lower()
            if lang.startswith("ja") or lang == "jp":
                return True

        # 方法2: meta タグの言語情報をチェック
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            if meta_lang.get("content").lower().startswith("ja"):
                return True

        # 方法3: 日本語の文字コードパターンをチェック
        # ひらがな、カタカナ、漢字の文字コード範囲
        hiragana_pattern = range(0x3040, 0x309F)
        katakana_pattern = range(0x30A0, 0x30FF)
        kanji_pattern = range(0x4E00, 0x9FBF)

        # タイトルをチェック
        japanese_chars_count = 0
        for char in title:
            code = ord(char)
            if (
                code in hiragana_pattern
                or code in katakana_pattern
                or code in kanji_pattern
            ):
                japanese_chars_count += 1

        if japanese_chars_count > 2:  # 複数の日本語文字があれば日本語とみなす
            return True

        # 方法4: サマリーやディスクリプションもチェック
        text_to_check = ""
        if hasattr(entry, "summary"):
            text_to_check += entry.summary

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            text_to_check += meta_desc.get("content")

        # 最初の段落をサンプリング
        paragraphs = soup.find_all("p")
        if paragraphs and len(paragraphs) > 0:
            text_to_check += paragraphs[0].get_text()

        # サンプリングしたテキストで日本語文字をチェック
        japanese_chars_count = 0
        for char in text_to_check[:100]:  # 最初の100文字だけチェック
            code = ord(char)
            if (
                code in hiragana_pattern
                or code in katakana_pattern
                or code in kanji_pattern
            ):
                japanese_chars_count += 1

        if japanese_chars_count > 5:  # 複数の日本語文字があれば日本語とみなす
            return True

        # 方法5: 特定の日本語サイトのドメインリスト（バックアップとして）
        japanese_domains = [
            "zenn.dev",
            "qiita.com",
            "gihyo.jp",
            "codezine.jp",
            "techplay.jp",
            "itmedia.co.jp",
            "atmarkit.co.jp",
        ]

        url = entry.link if hasattr(entry, "link") else ""
        for domain in japanese_domains:
            if domain in url:
                return True

        # デフォルトでは非日本語と判定
        return False

    async def _summarize_article(self, article: Article) -> None:
        """
        記事を要約します。

        Parameters
        ----------
        article : Article
            要約する記事。
        """
        prompt = f"""
        以下の技術ニュースの記事を要約してください。

        タイトル: {article.title}
        本文: {article.text[:2000]}

        要約は以下の形式で行い、日本語で回答してください:
        1. 記事の主な内容（1-2文）
        2. 重要なポイント（箇条書き3-5点）
        3. 技術的な洞察
        """

        system_instruction = """
        あなたは技術ニュースの記事の要約を行うアシスタントです。
        与えられた記事を分析し、簡潔で情報量の多い要約を作成してください。
        技術的な内容は正確に、一般的な内容は分かりやすく要約してください。
        回答は必ず日本語で行ってください。
        """

        try:
            summary = self.gpt_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=1000,
            )
            article.summary = summary
        except Exception as e:
            self.logger.error(f"要約の生成中にエラーが発生しました: {str(e)}")
            article.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries_for_date(
        self, articles: list[Article], date_str: str
    ) -> tuple[str, str]:
        """
        単一日付の記事をJSONとMarkdownファイルに保存します。

        Parameters
        ----------
        articles : list[Article]
            保存する記事のリスト。
        date_str : str
            日付文字列（"YYYY-MM-DD" 形式）。

        Returns
        -------
        tuple[str, str]
            保存されたファイルパスの組み合わせ (json_path, md_path)
        """
        if not articles:
            return ("", "")

        # 日付をdatetimeに変換
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        snapshot_datetime = datetime.combine(target_date, time.min)

        # 記事をシリアライズ
        records = self._serialize_articles(articles)

        # 既存記事を読み込んでマージ
        existing = await self._load_existing_articles(snapshot_datetime)

        merged = merge_records(
            existing,
            records,
            key=lambda item: item.get("title", ""),
            sort_key=self._article_sort_key,
            limit=self.TOTAL_LIMIT,
            reverse=True,
        )

        # JSONファイルを保存
        filename_json = f"{date_str}.json"
        json_path = await self.save_json(merged, filename_json)

        # Markdownファイルを保存
        filename_md = f"{date_str}.md"
        markdown = self._render_markdown(merged, snapshot_datetime)
        md_path = await self.save_markdown(markdown, filename_md)

        return (str(json_path), str(md_path))

    async def _store_summaries(
        self, articles: list[Article], target_dates: set[date]
    ) -> list[tuple[str, str]]:
        """
        要約を保存します。

        Parameters
        ----------
        articles : List[Article]
            保存する記事のリスト。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        if not articles:
            self.logger.info("保存する記事がありません")
            return []

        default_date = max(target_dates) if target_dates else datetime.now().date()
        incoming_records = self._serialize_articles(articles)
        records_by_date = group_records_by_date(
            incoming_records,
            default_date=default_date,
        )

        saved_files = await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_articles,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("title", ""),
            sort_key=self._article_sort_key,
            limit=self.TOTAL_LIMIT,
            logger=None,  # 日付情報の二重表示を防ぐ
        )

        return saved_files

    def _serialize_articles(self, articles: list[Article]) -> list[dict]:
        records: list[dict] = []
        for article in articles:
            category = article.category or "uncategorized"
            records.append(
                {
                    "title": article.title,
                    "url": article.url,
                    "feed_name": article.feed_name,
                    "summary": article.summary,
                    "popularity_score": article.popularity_score,
                    "published_at": (
                        article.published_at.isoformat()
                        if article.published_at
                        else None
                    ),
                    "category": category,
                }
            )
        return records

    async def _load_existing_articles(self, target_date: datetime) -> list[dict]:
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        filename_md = f"{date_str}.md"

        existing_json = await self.load_json(filename_json)
        if existing_json:
            return existing_json

        markdown = await self.storage.load(filename_md)
        if not markdown:
            return []

        return self._parse_markdown(markdown)

    def _article_sort_key(self, item: dict) -> tuple[float, datetime]:
        popularity = float(item.get("popularity_score", 0.0) or 0.0)
        published_raw = item.get("published_at")
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw)
            except ValueError:
                published = datetime.min
        else:
            published = datetime.min
        return (popularity, published)

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        content = f"# 技術ニュース記事 ({today.strftime('%Y-%m-%d')})\n\n"
        grouped: dict[str, list[dict]] = {}
        for record in records:
            category = record.get("category", "uncategorized")
            grouped.setdefault(category, []).append(record)

        for category, articles in grouped.items():
            heading = category.replace("_", " ").capitalize()
            content += f"## {heading}\n\n"
            for article in articles:
                content += f"### [{article['title']}]({article['url']})\n\n"
                content += f"**フィード**: {article.get('feed_name', '')}\n\n"
                content += f"**要約**:\n{article.get('summary', '')}\n\n"
                content += "---\n\n"
        return content

    def _parse_markdown(self, markdown: str) -> list[dict]:
        result: list[dict] = []
        category_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        article_pattern = re.compile(
            r"### \[(?P<title>.+?)\]\((?P<url>[^\)]+)\)\n\n"
            r"\*\*フィード\*\*: (?P<feed>.+?)\n\n"
            r"\*\*要約\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        sections = list(category_pattern.finditer(markdown))
        for idx, match in enumerate(sections):
            start = match.end()
            end = (
                sections[idx + 1].start() if idx + 1 < len(sections) else len(markdown)
            )
            block = markdown[start:end]
            category = match.group(1).strip().lower().replace(" ", "_")

            for article_match in article_pattern.finditer(block + "---"):
                result.append(
                    {
                        "title": article_match.group("title").strip(),
                        "url": article_match.group("url").strip(),
                        "feed_name": article_match.group("feed").strip(),
                        "summary": article_match.group("summary").strip(),
                        "popularity_score": 0.0,
                        "published_at": None,
                        "category": category,
                    }
                )

        return result
