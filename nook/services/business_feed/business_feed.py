"""ビジネスニュースのRSSフィードを監視・収集・要約するサービス。"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import tomli
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.dedup import DedupTracker


@dataclass
class Article:
    """
    ビジネスニュースの記事情報。
    
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


class BusinessFeed(BaseService):
    """
    ビジネスニュースのRSSフィードを監視・収集・要約するクラス。
    
    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    TOTAL_LIMIT = 15

    def __init__(self, storage_dir: str = "data"):
        """
        BusinessFeedを初期化します。
        
        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("business_feed")
        self.http_client = None  # setup_http_clientで初期化

        # フィードの設定を読み込む
        script_dir = Path(__file__).parent
        with open(script_dir / "feed.toml", "rb") as f:
            self.feed_config = tomli.load(f)

    def run(self, days: int = 1, limit: int | None = None) -> None:
        """
        ビジネスニュースのRSSフィードを監視・収集・要約して保存します。
        
        Parameters
        ----------
        days : int, default=1
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            各フィードから取得する記事数。Noneの場合は制限なし。
        """
        asyncio.run(self.collect(days, limit))

    async def collect(self, days: int = 1, limit: int | None = None) -> None:
        """
        ビジネスニュースのRSSフィードを監視・収集・要約して保存します（非同期版）。
        
        Parameters
        ----------
        days : int, default=1
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            各フィードから取得する記事数。Noneの場合は制限なし。
        """
        total_limit = self.TOTAL_LIMIT
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_articles: list[Article] = []
        dedup_tracker = self._load_existing_titles()

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
                        entries = self._filter_entries(
                            feed.entries, days, limit
                        )
                        self.logger.info(
                            f"フィード {feed_name} から {len(entries)} 件のエントリを取得しました"
                        )

                        for entry in entries:
                            entry_title = (
                                entry.title if hasattr(entry, "title") else "無題"
                            )

                            is_dup, normalized = dedup_tracker.is_duplicate(
                                entry_title
                            )
                            if is_dup:
                                original = dedup_tracker.get_original_title(
                                    normalized
                                ) or entry_title
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
                                dedup_tracker.add(article.title)
                                candidate_articles.append(article)

                    except Exception as e:
                        self.logger.error(f"フィード {feed_url} の処理中にエラーが発生しました: {str(e)}")

            self.logger.info(f"合計 {len(candidate_articles)} 件の記事候補を取得しました")

            selected_articles = self._select_top_articles(candidate_articles, total_limit)
            self.logger.info(
                f"人気スコア上位 {len(selected_articles)} 件の記事を要約します"
            )

            for article in selected_articles:
                await self._summarize_article(article)

            # 要約を保存
            if selected_articles:
                await self._store_summaries(selected_articles)
                self.logger.info("記事の要約を保存しました")
            else:
                self.logger.info("保存する記事がありません")

        finally:
            # グローバルクライアントなのでクローズ不要
            pass

    def _filter_entries(
        self, entries: list[dict], days: int, limit: int | None
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
        self.logger.info(f"エントリのフィルタリングを開始します（{len(entries)}件）...")

        # 日付でフィルタリング
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_entries = []

        for entry in entries:
            entry_date = None

            if hasattr(entry, "published_parsed") and entry.published_parsed:
                entry_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                entry_date = datetime(*entry.updated_parsed[:6])

            if entry_date:
                self.logger.debug(f"エントリ日付: {entry_date}, カットオフ日付: {cutoff_date}")
                if entry_date >= cutoff_date:
                    recent_entries.append(entry)
            else:
                # 日付が取得できない場合は含める
                self.logger.debug("エントリに日付情報がありません。含めます。")
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

            published_at = self._parse_entry_date(entry)
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
            self.logger.error(f"記事 {entry.get('link', '不明')} の取得中にエラーが発生しました: {str(e)}")
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

    def _parse_entry_date(self, entry) -> datetime | None:
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception:
            self.logger.debug("公開日時の解析に失敗しました")
        return None

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

        published = self._parse_entry_date(entry)
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
            "nikkei.com",
            "toyokeizai.net",
            "businessinsider.jp",
            "bloomberg.co.jp",
            "reuters.co.jp",
            "diamond.jp",
            "jbpress.co.jp",
            "president.jp",
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
        以下のビジネスニュースの記事を要約してください。

        タイトル: {article.title}
        本文: {article.text[:2000]}

        要約は以下の形式で行い、日本語で回答してください:
        1. 記事の主な内容（1-2文）
        2. 重要なポイント（箇条書き3-5点）
        3. ビジネスインパクト
        """

        system_instruction = """
        あなたはビジネスニュースの記事の要約を行うアシスタントです。
        与えられた記事を分析し、簡潔で情報量の多い要約を作成してください。
        経済・ビジネス用語は正確に、一般的な内容は分かりやすく要約してください。
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

    async def _store_summaries(self, articles: list[Article]) -> None:
        """
        要約を保存します。
    
        Parameters
        ----------
        articles : List[Article]
            保存する記事のリスト。
        """
        if not articles:
            self.logger.info("保存する記事がありません")
            return

        today = datetime.now()
        content = f"# ビジネスニュース記事 ({today.strftime('%Y-%m-%d')})\n\n"

        # カテゴリごとに整理
        categories = {}
        for article in articles:
            if article.category not in categories:
                categories[article.category] = []

            categories[article.category].append(article)

        # Markdownを生成
        for category, category_articles in categories.items():
            content += f"## {category.replace('_', ' ').capitalize()}\n\n"

            for article in category_articles:
                content += f"### [{article.title}]({article.url})\n\n"
                content += f"**フィード**: {article.feed_name}\n\n"
                content += f"**要約**:\n{article.summary}\n\n"

                content += "---\n\n"

        # 保存
        self.logger.info(f"business_feed ディレクトリに保存します: {today.strftime('%Y-%m-%d')}.md")
        try:
            self.storage.save_markdown(content, "", today)
            self.logger.info("保存が完了しました")
        except Exception as e:
            self.logger.error(f"保存中にエラーが発生しました: {str(e)}")
            # ディレクトリを作成して再試行
            try:
                business_feed_dir = Path(self.storage.base_dir) / "business_feed"
                business_feed_dir.mkdir(parents=True, exist_ok=True)

                file_path = business_feed_dir / f"{today.strftime('%Y-%m-%d')}.md"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info(f"再試行で保存に成功しました: {file_path}")
            except Exception as e2:
                self.logger.error(f"再試行でも保存に失敗しました: {str(e2)}")
