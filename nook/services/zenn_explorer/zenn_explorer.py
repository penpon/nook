"""ZennのRSSフィードを監視・収集・要約するサービス。"""

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

    async def collect(self, days: int = 1, limit: int | None = None) -> None:
        """
        ZennのRSSフィードを監視・収集・要約して保存します（非同期版）。
        
        Parameters
        ----------
        days : int, default=1
            何日前までの記事を取得するか。
        limit : Optional[int], default=None
            各フィードから取得する記事数。Noneの場合は制限なし。
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_articles: list[Article] = []
        dedup_tracker = DedupTracker()  # カテゴリ横断のタイトル重複チェック用

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

                        current_limit = limit
                        if current_limit is None:
                            self.logger.info(f"フィード {feed_url} は制限なしで取得します")

                        entries = self._filter_entries(
                            feed.entries, days, current_limit
                        )
                        self.logger.info(
                            f"フィード {feed_name} から {len(entries)} 件のエントリを取得しました"
                        )

                        for entry in entries:
                            # 記事を取得
                            article = await self._retrieve_article(
                                entry, feed_name, category
                            )
                            if article:
                                # 重複タイトルをスキップ（カテゴリ横断・正規化済み）
                                is_dup, normalized_title = dedup_tracker.is_duplicate(article.title)
                                if is_dup:
                                    original = dedup_tracker.get_original_title(normalized_title)
                                    self.logger.info(
                                        f"重複記事をスキップ: '{article.title}' "
                                        f"(正規化後: '{normalized_title}', 初出: '{original}')"
                                    )
                                    continue
                                dedup_tracker.add(article.title)

                                candidate_articles.append(article)

                    except Exception as e:
                        self.logger.error(f"フィード {feed_url} の処理中にエラーが発生しました: {str(e)}")

            self.logger.info(f"合計 {len(candidate_articles)} 件の記事候補を取得しました")

            selected_articles = self._select_top_articles(candidate_articles)
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
        self, entries: list[dict], days: int, limit: int | None = None
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
            published_at = self._parse_entry_date(entry)

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
            self.logger.error(f"記事 {entry.get('link', '不明')} の取得中にエラーが発生しました: {str(e)}")
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
        content = f"# Zenn記事 ({today.strftime('%Y-%m-%d')})\n\n"

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
        self.logger.info(f"zenn_explorer ディレクトリに保存します: {today.strftime('%Y-%m-%d')}.md")
        try:
            self.storage.save_markdown(content, "", today)
            self.logger.info("保存が完了しました")
        except Exception as e:
            self.logger.error(f"保存中にエラーが発生しました: {str(e)}")
            # ディレクトリを作成して再試行
            try:
                zenn_explorer_dir = Path(self.storage.base_dir) / "zenn_explorer"
                zenn_explorer_dir.mkdir(parents=True, exist_ok=True)

                file_path = zenn_explorer_dir / f"{today.strftime('%Y-%m-%d')}.md"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info(f"再試行で保存に成功しました: {file_path}")
            except Exception as e2:
                self.logger.error(f"再試行でも保存に失敗しました: {str(e2)}")

    def _parse_entry_date(self, entry) -> datetime | None:
        """フィードエントリから公開日時を抽出します。"""
        try:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception as exc:
            self.logger.debug(f"公開日時の解析に失敗しました: {exc}")
        return None

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
            like_candidate = getattr(entry, "likes", None) or getattr(entry, "likes_count", None)
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
