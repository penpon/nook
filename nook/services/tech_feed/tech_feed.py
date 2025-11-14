"""技術ニュースのRSSフィードを監視・収集・要約するサービス。"""

import asyncio
import json
from datetime import date, datetime
from pathlib import Path

import feedparser
import tomli
from bs4 import BeautifulSoup

from nook.common.daily_snapshot import group_records_by_date
from nook.common.date_utils import is_within_target_dates, target_dates_set
from nook.common.dedup import load_existing_titles_from_storage
from nook.common.feed_utils import parse_entry_datetime
from nook.common.logging_utils import (
    log_article_counts,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)
from nook.services.base_feed_service import Article, BaseFeedService


class TechFeed(BaseFeedService):
    """
    技術ニュースのRSSフィードを監視・収集・要約するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    TOTAL_LIMIT = 15
    SUMMARY_LIMIT = 15

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
        target_dates: list[date] | None = None,
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
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_articles: list[Article] = []
        effective_target_dates = target_dates or target_dates_set(days)

        # カテゴリ横断のタイトル重複チェック用（既存ファイルからロード）
        # バグ修正：全ての既存ファイルから重複チェック
        all_existing_dates = await self._get_all_existing_dates()
        dedup_tracker = await load_existing_titles_from_storage(
            self.storage, all_existing_dates, self.logger
        )

        self.logger.info("\n📡 フィード取得中...")

        try:
            # 各カテゴリのフィードから記事を取得
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
                                        f"(正規化後: '{normalized_title}', 初出: '{original}')"  # noqa: E501
                                    )
                                    continue

                                # 日付範囲チェック
                                if not is_within_target_dates(
                                    article.published_at, effective_target_dates
                                ):
                                    continue

                                dedup_tracker.add(article.title)
                                candidate_articles.append(article)

                    except Exception as e:
                        self.logger.error(
                            f"フィード {feed_url} の処理中にエラーが発生しました: {str(e)}"  # noqa: E501
                        )

            # 日付ごとにグループ化
            articles_by_date = self._group_articles_by_date(candidate_articles)

            # 日付ごとに上位N件を選択して要約
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
                    self.logger.debug(
                        f"既存記事ファイル {date_str}.json の読み込みに失敗しました: {e}"  # noqa: E501
                    )

                # 既存/新規記事数をカウント
                existing_count = len(existing_titles_for_date)
                new_count = len(date_articles)

                # ログ改善：真に新規の記事を確認
                truly_new_articles = [
                    article
                    for article in date_articles
                    if article.title not in existing_titles_for_date
                ]

                # 日付情報を先頭に表示（ログ改善版）
                log_processing_start(self.logger, date_str)
                log_article_counts(self.logger, existing_count, len(truly_new_articles))

                # 新規記事のみを要約対象として選択
                selected = self._select_top_articles(truly_new_articles, limit)

                if selected:
                    log_summary_candidates(self.logger, selected)

                    # 要約生成
                    log_summarization_start(self.logger)
                    for idx, article in enumerate(selected, 1):
                        await self._summarize_article(article)
                        log_summarization_progress(
                            self.logger, idx, len(selected), article.title
                        )

                    # ログ改善：保存完了の前に改行
                    json_path, md_path = await self._store_summaries_for_date(
                        selected, date_str
                    )
                    log_storage_complete(self.logger, json_path, md_path)
                    saved_files.append((json_path, md_path))
                else:
                    log_no_new_articles(self.logger)

            # 処理完了メッセージ
            if saved_files:
                self.logger.info(f"\n💾 {len(saved_files)}日分のデータを保存完了")
            else:
                self.logger.info("\n保存する記事がありません")

            return saved_files

        finally:
            pass

    def _select_top_articles(
        self, articles: list[Article], limit: int | None = None
    ) -> list[Article]:
        """
        記事を人気スコアでソートし、上位N件を選択します。

        Parameters
        ----------
        articles : list[Article]
            選択対象の記事リスト
        limit : Optional[int]
            選択する記事数。Noneの場合はSUMMARY_LIMITを使用

        Returns
        -------
        list[Article]
            選択された記事リスト
        """
        if not articles:
            return []

        # 人気スコアで降順ソート
        sorted_articles = sorted(
            articles, key=lambda x: x.popularity_score, reverse=True
        )

        # 上位N件を選択（limitが指定されていればそれを使用、なければSUMMARY_LIMIT）
        selection_limit = limit if limit is not None else self.SUMMARY_LIMIT
        return sorted_articles[:selection_limit]

    async def _retrieve_article(
        self, entry: dict, feed_name: str, category: str
    ) -> Article | None:
        """
        記事を取得します（日本語判定含む）。

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

            # 日本語判定（tech_feed特有）
            if not self._detect_japanese_content(soup, title, entry):
                self.logger.debug(f"非日本語記事をスキップ: {title}")
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
                f"記事 {entry.get('link', '不明')} の取得中にエラーが発生しました: {str(e)}"  # noqa: E501
            )
            return None

    async def _store_summaries(
        self, articles: list[Article], target_dates: list[date]
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

        from nook.common.daily_snapshot import store_daily_snapshots

        saved_files = await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_articles,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("title", ""),
            sort_key=self._article_sort_key,
            limit=self.TOTAL_LIMIT,
            logger=None,
        )

        return saved_files

    # ========================================
    # 抽象メソッドの実装
    # ========================================

    def _extract_popularity(self, entry, soup: BeautifulSoup) -> float:
        """記事の人気指標を抽出します。"""
        # 1. メタタグから抽出
        meta_tags = [
            ("property", "article:reaction_count"),
            ("name", "reaction-count"),
            ("property", "og:reaction_count"),
        ]

        for attr, value in meta_tags:
            meta = soup.find("meta", attrs={attr: value})
            if meta and meta.get("content"):
                parsed = self._safe_parse_int(meta.get("content"))
                if parsed is not None:
                    return float(parsed)

        candidates: list[int] = []

        # 2. data属性を持つ要素
        for element in soup.select("[data-reaction-count], [data-like-count]"):
            value = element.get("data-reaction-count") or element.get("data-like-count")
            parsed = self._safe_parse_int(value)
            if parsed is not None:
                candidates.append(parsed)

        # 3. ボタンやスパンのテキストから抽出
        for selector in ["button", "span", "div"]:
            for element in soup.select(selector):
                text = element.get_text(strip=True)
                if any(keyword in text for keyword in ["いいね", "Like", "Reaction"]):
                    parsed = self._safe_parse_int(text)
                    if parsed is not None:
                        candidates.append(parsed)

        if candidates:
            return float(max(candidates))

        return 0.0

    def _get_markdown_header(self) -> str:
        """Markdownファイルのヘッダーテキストを返します。"""
        return "技術ニュース記事"

    def _get_summary_system_instruction(self) -> str:
        """要約生成用のシステムインストラクションを返します。"""
        return """
        あなたは技術ニュースの要約を行うアシスタントです。
        与えられた記事を分析し、簡潔で情報量の多い要約を作成してください。
        技術的な内容は正確に、一般的な内容は分かりやすく要約してください。
        回答は必ず日本語で行ってください。
        """

    def _get_summary_prompt_template(self, article: Article) -> str:
        """要約生成用のプロンプトテンプレートを返します。"""
        return f"""
        以下の技術ニュース記事を要約してください。

        タイトル: {article.title}
        本文: {article.text[:2000]}

        要約は以下の形式で行い、日本語で回答してください:
        1. 記事の主な内容（1-2文）
        2. 技術的な重要ポイント（箇条書き3-5点）
        3. 開発者や業界への影響
        """

    def _needs_japanese_check(self) -> bool:
        """日本語判定が必要（tech_feed特有）。"""
        return True
