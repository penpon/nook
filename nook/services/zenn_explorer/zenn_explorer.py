"""ZennのRSSフィードを監視・収集・要約するサービス。"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import feedparser
import tomli
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.dedup import DedupTracker
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.date_utils import is_within_target_dates, target_dates_set
from nook.common.feed_utils import parse_entry_datetime


@dataclass
class Article:
    """
    Zenn記事の情報。

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


class ZennExplorer(BaseService):
    """
    ZennのRSSフィードを監視・収集・要約するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    SUMMARY_LIMIT = 15

    def __init__(self, storage_dir: str = "data"):
        """
        ZennExplorerを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("zenn_explorer")
        self.http_client = None  # setup_http_clientで初期化

        # フィードの設定を読み込む
        script_dir = Path(__file__).parent
        with open(script_dir / "feed.toml", "rb") as f:
            self.feed_config = tomli.load(f)

    def run(self, days: int = 1, limit: int | None = None) -> None:
        """
        ZennのRSSフィードを監視・収集・要約して保存します。

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
        ZennのRSSフィードを監視・収集・要約して保存します（非同期版）。

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
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_articles: list[Article] = []
        dedup_tracker = (
            self._load_existing_titles()
        )  # カテゴリ横断のタイトル重複チェック用
        effective_target_dates = target_dates or target_dates_set(days)

        self.logger.info("\n📡 フィード取得中...")

        try:
            # 各カテゴリのフィードから記事を取得
            total_entries = 0
            for category, feeds in self.feed_config.items():
                for feed_url in feeds:
                    try:
                        # フィードを解析
                        feed = feedparser.parse(feed_url)
                        feed_name = (
                            feed.feed.title
                            if hasattr(feed, "feed") and hasattr(feed.feed, "title")
                            else feed_url
                        )

                        effective_limit = None
                        if limit is not None:
                            effective_limit = limit * max(days, 1)

                        entries = self._filter_entries(
                            feed.entries, effective_target_dates, effective_limit
                        )
                        total_entries += len(entries)
                        self.logger.info(f"   • {feed_name}: {len(entries)}件取得")

                        for entry in entries:
                            # 記事を取得
                            article = await self._retrieve_article(
                                entry, feed_name, category
                            )
                            if article:
                                # 重複タイトルをスキップ（カテゴリ横断・正規化済み）
                                is_dup, normalized_title = dedup_tracker.is_duplicate(
                                    article.title
                                )
                                if is_dup:
                                    original = dedup_tracker.get_original_title(
                                        normalized_title
                                    )
                                    self.logger.info(
                                        f"重複記事をスキップ: '{article.title}' "
                                        f"(正規化後: '{normalized_title}', 初出: '{original}')"
                                    )
                                    continue

                                # 日付範囲チェックを重複トラッキングの前に実行
                                if not is_within_target_dates(
                                    article.published_at, effective_target_dates
                                ):
                                    continue

                                dedup_tracker.add(article.title)
                                candidate_articles.append(article)

                    except Exception as e:
                        self.logger.error(
                            f"フィード {feed_url} の処理中にエラーが発生しました: {str(e)}"
                        )

            # 日付ごとにグループ化
            articles_by_date = self._group_articles_by_date(candidate_articles)

            # 日付ごとに上位N件を選択して要約（古い日付から新しい日付へ）
            all_selected_articles = []
            for date_str in sorted(articles_by_date.keys()):
                date_articles = articles_by_date[date_str]

                # 日付情報を先頭に表示
                self.logger.info(f"\n📰 [{date_str}] の記事を処理中...")
                self.logger.info(f"   🔍 候補記事: {len(date_articles)}件")

                selected = self._select_top_articles(date_articles)

                self.logger.info(
                    f"   ✅ 選択された記事 ({len(selected)}/{len(date_articles)}):"
                )
                for idx, article in enumerate(selected, 1):
                    self.logger.info(
                        f"      {idx}. 「{article.title}」(スコア: {article.popularity_score:.0f})"
                    )

                # 要約生成
                if selected:
                    self.logger.info(f"\n   🤖 要約生成中...")
                    for idx, article in enumerate(selected, 1):
                        await self._summarize_article(article)
                        self.logger.info(
                            f"      ✓ {idx}/{len(selected)}: 「{article.title[:50]}...」"
                        )

                all_selected_articles.extend(selected)

            # 要約を保存
            saved_files: list[tuple[str, str]] = []
            if all_selected_articles:
                saved_files = await self._store_summaries(
                    all_selected_articles, effective_target_dates
                )
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

    def _filter_entries(
        self,
        entries: list[dict],
        target_dates: set[date],
        limit: int | None = None,
    ) -> list[dict]:
        """
        新しいエントリをフィルタリングします。

        Parameters
        ----------
        entries : List[dict]
            エントリのリスト。
        days : int
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            取得する記事数。Noneの場合は全て取得。

        Returns
        -------
        List[dict]
            フィルタリングされたエントリのリスト。
        """
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

        # limitがNoneの場合は全てのエントリを返す
        if limit is None:
            return recent_entries
        # そうでなければ指定された数だけ返す
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

            popularity = self._extract_popularity(entry, soup)
            published_at = parse_entry_datetime(entry)

            return Article(
                feed_name=feed_name,
                title=title,
                url=url,
                text=text,
                soup=soup,
                category=category,
                popularity_score=popularity,
                published_at=published_at,
            )

        except Exception as e:
            self.logger.error(
                f"記事 {entry.get('link', '不明')} の取得中にエラーが発生しました: {str(e)}"
            )
            return None

    async def _summarize_article(self, article: Article) -> None:
        """
        記事を要約します。

        Parameters
        ----------
        article : Article
            要約する記事。
        """
        prompt = f"""
        以下のZenn記事を要約してください。

        タイトル: {article.title}
        本文: {article.text[:2000]}

        要約は以下の形式で行い、日本語で回答してください:
        1. 記事の主な内容（1-2文）
        2. 重要なポイント（箇条書き3-5点）
        3. 技術的な洞察
        """

        system_instruction = """
        あなたはZennの技術記事の要約を行うアシスタントです。
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

    async def _store_summaries(
        self, articles: list[Article], target_dates: set[date]
    ) -> list[tuple[str, str]]:
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
            limit=self.SUMMARY_LIMIT,
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
        content = f"# Zenn記事 ({today.strftime('%Y-%m-%d')})\n\n"
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

    def _extract_popularity(self, entry, soup: BeautifulSoup) -> float:
        """記事の人気指標（いいね数）を抽出します。"""
        # 1. メタタグ（最優先）
        meta_like = soup.find("meta", attrs={"property": "zenn:likes_count"})
        if meta_like and meta_like.get("content"):
            value = self._safe_parse_int(meta_like.get("content"))
            if value is not None:
                return float(value)

        candidates: list[int] = []

        # 2. data属性を持つ要素
        for element in soup.select("[data-like-count]"):
            value = self._safe_parse_int(element.get("data-like-count"))
            if value is not None:
                candidates.append(value)

        # 3. ボタンやスパンのテキストから抽出
        for selector in ["button", "span", "div"]:
            for element in soup.select(selector):
                text = element.get_text(strip=True)
                if not text:
                    continue
                if "いいね" in text:
                    value = self._safe_parse_int(text)
                    if value is not None:
                        candidates.append(value)

        if candidates:
            return float(max(candidates))

        # 4. フィードエントリに含まれる既知フィールド
        try:
            like_candidate = getattr(entry, "likes", None) or getattr(
                entry, "likes_count", None
            )
            if like_candidate is None and hasattr(entry, "zenn_likes_count"):
                like_candidate = getattr(entry, "zenn_likes_count")
            value = self._safe_parse_int(like_candidate)
            if value is not None:
                return float(value)
        except Exception as exc:
            self.logger.debug(f"フィード内人気情報の抽出に失敗しました: {exc}")

        return 0.0

    def _safe_parse_int(self, value) -> int | None:
        """さまざまな値から整数を抽出します。"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(-?\d+)", value.replace(",", ""))
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    def _select_top_articles(self, articles: list[Article]) -> list[Article]:
        """人気スコア順に記事をソートし、上位のみ返します。"""
        if not articles:
            return []

        if len(articles) <= self.SUMMARY_LIMIT:
            return articles

        def sort_key(article: Article):
            published = article.published_at or datetime.min
            return (article.popularity_score, published)

        sorted_articles = sorted(articles, key=sort_key, reverse=True)
        return sorted_articles[: self.SUMMARY_LIMIT]
