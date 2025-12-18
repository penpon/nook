"""TrendRadar Explorer 基底クラス.

このモジュールは、TrendRadar系Explorer（Zhihu, Juejin等）の
共通機能を提供する基底クラスを定義します。
"""

import asyncio
from abc import abstractmethod
from datetime import date, datetime, timezone
from typing import Any

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.base.base_service import BaseService
from nook.services.explorers.trendradar.trendradar_client import TrendRadarClient
from nook.services.explorers.trendradar.utils import (
    create_empty_soup,
    escape_markdown_text,
    escape_markdown_url,
    parse_popularity_score,
    parse_published_at,
    sanitize_prompt_input,
)


class BaseTrendRadarExplorer(BaseService):
    """TrendRadar系Explorerの共通基底クラス.

    TrendRadar MCPサーバーと通信し、各プラットフォームのホットトピックを
    取得・要約・保存する共通機能を提供します。

    サブクラスでオーバーライドすべき属性:
    - PLATFORM_NAME: TrendRadar APIで使用するプラットフォーム名
    - FEED_NAME: Articleのfeed_nameフィールドに使用する名前
    - MARKDOWN_HEADER: Markdownレンダリング時のヘッダータイトル

    サブクラスで実装すべきメソッド:
    - _get_summary_prompt(): GPT要約用のプロンプトを生成
    - _get_system_instruction(): GPT要約用のシステム指示を取得
    """

    # サブクラスでオーバーライドする属性
    PLATFORM_NAME: str = ""
    FEED_NAME: str = ""
    MARKDOWN_HEADER: str = ""

    # 共通設定
    TOTAL_LIMIT = 5
    GPT_TEMPERATURE = 0.3
    GPT_MAX_TOKENS = 600
    MAX_CONCURRENT_REQUESTS = 5

    # エラーメッセージ定数
    ERROR_MSG_EMPTY_SUMMARY = "要約を生成できませんでした（空のレスポンス）"
    ERROR_MSG_GENERATION_FAILED = "要約生成に失敗しました"

    def __init__(
        self,
        service_name: str,
        storage_dir: str = "var/data",
        config: BaseConfig | None = None,
    ):
        """BaseTrendRadarExplorerを初期化.

        Parameters
        ----------
        service_name : str
            サービス名（例: "trendradar-zhihu"）。
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        if config is None:
            config = BaseConfig(DATA_DIR=storage_dir)
        else:
            config = config.model_copy(update={"DATA_DIR": storage_dir})

        super().__init__(service_name, config=config)
        if not self.PLATFORM_NAME or not self.FEED_NAME or not self.MARKDOWN_HEADER:
            raise ValueError(
                f"{self.__class__.__name__}でPLATFORM_NAME、FEED_NAME、"
                "MARKDOWN_HEADERを設定する必要があります"
            )
        self.client = TrendRadarClient()

    async def close(self) -> None:
        """リソースを開放."""
        await self.client.close()

    async def __aenter__(self) -> "BaseTrendRadarExplorer":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def run(self, days: int = 1, limit: int | None = None) -> None:
        """ホットトピックを収集して保存（同期版）.

        Parameters
        ----------
        days : int, default=1
            何日分のデータを処理するか。
        limit : int | None, default=None
            取得するトピック数。Noneの場合はデフォルト値。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._run_with_cleanup(days=days, limit=limit))
        else:
            raise RuntimeError(
                "run() はイベントループ実行中には使用できません。"
                "asyncコンテキストでは await collect(...) を使用してください。"
            )

    async def _run_with_cleanup(
        self, days: int = 1, limit: int | None = None
    ) -> list[tuple[str, str]]:
        """collect実行後にクライアントをクリーンアップするラッパー."""
        try:
            return await self.collect(days=days, limit=limit)
        finally:
            await self.close()

    async def collect(
        self,
        days: int = 1,
        limit: int | None = None,
        *,
        target_dates: list[date] | None = None,
    ) -> list[tuple[str, str]]:
        """ホットトピックを収集して保存（非同期版）.

        Parameters
        ----------
        days : int, default=1
            何日分のデータを処理するか。
        limit : int | None, default=None
            取得するトピック数。Noneの場合はTOTAL_LIMITを使用。
        target_dates : list[date] | None, default=None
            対象日付のリスト（将来の拡張用）。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        if days != 1:
            raise ValueError(
                "複数日の収集 (days > 1) はまだ実装されていません。"
                "days=1 を指定するか、パラメータを省略してください。"
            )

        if target_dates is not None:
            if len(target_dates) == 0:
                raise ValueError(
                    "target_dates には少なくとも1つの日付を指定してください"
                )
            if len(target_dates) > 1:
                raise NotImplementedError(
                    "複数日の収集 (len(target_dates) > 1) はまだ実装されていません。"
                    "単一の日付を指定するか、days=1 を使用してください。"
                )
            target_date = target_dates[0]
        else:
            target_date = datetime.now(timezone.utc).date()

        if limit is not None:
            if (
                not isinstance(limit, int)
                or isinstance(limit, bool)
                or limit < 1
                or limit > 100
            ):
                raise ValueError(
                    f"limit は 1 から 100 の整数である必要があります。指定値: {limit}"
                )
            effective_limit = limit
        else:
            effective_limit = self.TOTAL_LIMIT

        news_items = await self.client.get_latest_news(
            platform=self.PLATFORM_NAME, limit=effective_limit
        )

        if not news_items:
            self.logger.info("TrendRadarから取得したニュース項目がありません")
            return []

        articles = [self._transform_to_article(item) for item in news_items]

        sem = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        async def bounded_summarize(article: Article) -> None:
            async with sem:
                await self._summarize_article(article)

        results = await asyncio.gather(
            *[bounded_summarize(article) for article in articles],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                self.logger.error(
                    f"Unexpected error in summary generation for article "
                    f"'{articles[i].title}': {result}",
                    exc_info=(type(result), result, result.__traceback__),
                )
                if not articles[i].summary:
                    articles[i].summary = self.ERROR_MSG_GENERATION_FAILED

        date_str = target_date.strftime("%Y-%m-%d")
        saved_files = await self._store_articles(articles, date_str)

        return saved_files

    def _transform_to_article(self, item: dict[str, Any]) -> Article:
        """TrendRadar形式のアイテムをArticleオブジェクトに変換."""
        raw_popularity = item.get("hot")
        if raw_popularity is None:
            raw_popularity = item.get("rank", 0)

        return Article(
            feed_name=self.FEED_NAME,
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            text=str(item.get("desc") or item.get("description") or ""),
            soup=create_empty_soup(),
            category="hot",
            popularity_score=self._parse_popularity_score(raw_popularity),
            published_at=self._parse_published_at(item),
        )

    def _parse_popularity_score(self, value: object) -> float:
        """人気スコアを安全にパース."""
        return parse_popularity_score(value)

    def _sanitize_prompt_input(self, text: str, max_length: int = 500) -> str:
        """プロンプト入力用のサニタイズ処理."""
        return sanitize_prompt_input(text, max_length)

    def _parse_published_at(self, item: dict[str, Any]) -> datetime:
        """記事の公開日時を解析."""
        return parse_published_at(item)

    def _escape_markdown_text(self, text: str) -> str:
        """Markdownテキスト用のエスケープ処理."""
        return escape_markdown_text(text)

    def _escape_markdown_url(self, url: str) -> str:
        """MarkdownリンクのURL用エスケープ処理."""
        return escape_markdown_url(url)

    @abstractmethod
    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成.

        Parameters
        ----------
        article : Article
            要約対象の記事。

        Returns
        -------
        str
            GPTに送信するプロンプト。
        """

    @abstractmethod
    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得.

        Returns
        -------
        str
            GPTのシステム指示。
        """

    def _get_default_summary_prompt(
        self,
        article: Article,
        platform_label: str,
        content_label: str,
        sections: list[str],
    ) -> str:
        """共通のGPT要約用プロンプトテンプレートを生成.

        Parameters
        ----------
        article : Article
            要約対象の記事。
        platform_label : str
            プラットフォームの表示名（例: "知乎（Zhihu）"）。
        content_label : str
            コンテンツの種類（例: "ホットトピック", "ホットニュース"）。
        sections : list[str]
            要求するセクションのリスト。

        Returns
        -------
        str
            生成されたプロンプト。
        """
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        prompt = (
            f"以下の{platform_label}{content_label}を日本語で詳細に要約してください。\n\n"
            f"タイトル: {safe_title}\n"
            f"URL: {safe_url}\n"
            f"説明: {safe_text}\n\n"
            "以下のフォーマットで出力してください：\n\n"
        )

        for i, section in enumerate(sections, 1):
            prompt += f"{i}. {section}\n"

        return prompt

    async def _summarize_article(self, article: Article) -> None:
        """記事の要約を生成（破壊的変更）."""
        prompt = self._get_summary_prompt(article)
        system_instruction = self._get_system_instruction()

        try:
            summary = await self.gpt_client.generate_async(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=self.GPT_TEMPERATURE,
                max_tokens=self.GPT_MAX_TOKENS,
            )
            if summary and summary.strip():
                article.summary = summary
            else:
                self.logger.warning(
                    f"GPT returned empty summary for article: {article.title}"
                )
                article.summary = self.ERROR_MSG_EMPTY_SUMMARY
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.exception(f"要約生成に失敗 (article: {article.title})")
            article.summary = self.ERROR_MSG_GENERATION_FAILED

    async def _store_articles(
        self, articles: list[Article], date_str: str
    ) -> list[tuple[str, str]]:
        """記事をJSON/Markdown形式で保存."""
        if not articles:
            return []

        records = []
        for article in articles:
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
                    "category": article.category,
                }
            )

        filename_json = f"{date_str}.json"
        json_path = await self.save_json(records, filename_json)

        markdown = self._render_markdown(records, date_str)
        filename_md = f"{date_str}.md"
        md_path = await self.save_markdown(markdown, filename_md)

        self.logger.info(f"{len(articles)}件の記事を保存しました: {date_str}")

        return [(str(json_path), str(md_path))]

    def _render_markdown(self, records: list[dict], date_str: str) -> str:
        """記事をMarkdown形式でレンダリング."""
        content = f"# {self.MARKDOWN_HEADER} ({date_str})\n\n"

        for i, record in enumerate(records, 1):
            title = self._escape_markdown_text(record.get("title", ""))
            url = self._escape_markdown_url(record.get("url", ""))
            summary = record.get("summary", "")
            hot = self._parse_popularity_score(record.get("popularity_score"))

            content += f"## {i}. [{title}]({url})\n\n"
            content += f"**人気度**: {hot:,.0f}\n\n"
            content += f"**要約**:\n\n{summary}\n\n"
            content += "---\n\n"

        return content
