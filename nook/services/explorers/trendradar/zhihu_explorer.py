"""Zhihu Explorer - TrendRadar経由で知乎のホットトピックを取得.

This module provides the ZhihuExplorer class that retrieves hot topics
from Zhihu via the TrendRadar MCP server.
"""

import asyncio
import copy
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser

from nook.core.config import BaseConfig
from nook.services.base.base_service import BaseService
from nook.services.explorers.trendradar.trendradar_client import TrendRadarClient


@dataclass
class Article:
    """知乎記事のデータクラス.

    TrendRadarから取得した知乎のホットトピックを表現します。
    """

    feed_name: str
    title: str
    url: str
    text: str = ""
    soup: BeautifulSoup = field(
        default_factory=lambda: BeautifulSoup("", "html.parser")
    )
    category: str | None = None
    summary: str = field(default="")
    popularity_score: float = field(default=0.0)
    published_at: datetime | None = None


class ZhihuExplorer(BaseService):
    """知乎のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、知乎（Zhihu）のホットトピックを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = ZhihuExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    TOTAL_LIMIT = 15

    def __init__(self, storage_dir: str = "data", config: BaseConfig | None = None):
        """ZhihuExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        # カスタムストレージディレクトリを設定に反映
        if config is None:
            config = BaseConfig()
        else:
            config = copy.copy(config)
        config.DATA_DIR = storage_dir

        super().__init__("trendradar-zhihu", config=config)
        self.client = TrendRadarClient()

    async def close(self) -> None:
        """リソースを開放."""
        await self.client.close()

    async def __aenter__(self) -> "ZhihuExplorer":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def run(self, days: int = 1, limit: int | None = None) -> None:
        """知乎のホットトピックを収集して保存（同期版）.

        Parameters
        ----------
        days : int, default=1
            何日分のデータを処理するか。
        limit : int | None, default=None
            取得するトピック数。Noneの場合はデフォルト値。
        """
        asyncio.run(self._run_with_cleanup(days=days, limit=limit))

    async def _run_with_cleanup(
        self, days: int = 1, limit: int | None = None
    ) -> list[tuple[str, str]]:
        """collect実行後にクライアントをクリーンアップするラッパー.

        Parameters
        ----------
        days : int, default=1
            何日分のデータを処理するか。
        limit : int | None, default=None
            取得するトピック数。Noneの場合はデフォルト値。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
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
        """知乎のホットトピックを収集して保存（非同期版）.

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
            raise NotImplementedError("Multi-day collection not yet implemented")

        effective_limit = limit or self.TOTAL_LIMIT

        # TrendRadarからデータ取得
        news_items = await self.client.get_latest_news(
            platform="zhihu", limit=effective_limit
        )

        if not news_items:
            self.logger.info("取得したホットトピックがありません")
            return []

        # Article オブジェクトに変換
        articles = [self._transform_to_article(item) for item in news_items]

        # GPT要約を生成
        for article in articles:
            await self._summarize_article(article)

        # 日付別にグループ化して保存
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        saved_files = await self._store_articles(articles, today)

        return saved_files

    def _transform_to_article(self, item: dict[str, Any]) -> Article:
        """TrendRadar形式のアイテムをArticleオブジェクトに変換.

        Parameters
        ----------
        item : dict[str, Any]
            TrendRadarから取得したニュースアイテム。

        Returns
        -------
        Article
            変換されたArticleオブジェクト。
        """
        return Article(
            feed_name="zhihu",
            title=item.get("title", ""),
            url=item.get("url", ""),
            text=item.get("desc", ""),
            category="hot",
            popularity_score=float(item.get("hot", 0)),
            published_at=self._parse_published_at(item),
        )

    def _parse_published_at(self, item: dict[str, Any]) -> datetime:
        """記事の公開日時を解析.

        Parameters
        ----------
        item : dict[str, Any]
            TrendRadarアイテム。

        Returns
        -------
        datetime
            解析された公開日時、または現在日時。
        """
        # 候補フィールド
        candidates = ["published_at", "timestamp", "pub_date", "created_at"]

        for candidate_field in candidates:
            val = item.get(candidate_field)
            if val:
                # Epoch timestamp handling
                if isinstance(val, (int, float)):
                    try:
                        return datetime.fromtimestamp(val, tz=timezone.utc)
                    except (ValueError, OSError):
                        continue

                # String parsing
                try:
                    dt = parser.parse(str(val))
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except (ValueError, TypeError):
                    continue

        return datetime.now(timezone.utc)

    async def _summarize_article(self, article: Article) -> None:
        """記事の要約を生成.

        Parameters
        ----------
        article : Article
            要約を生成する記事。
        """
        prompt = f"""以下の知乎（Zhihu）ホットトピックを日本語で簡潔に要約してください。

タイトル: {article.title}
URL: {article.url}
説明: {article.text}
人気度（ホット値）: {article.popularity_score:,.0f}

要約は1-2文で、このトピックが何について議論されているかを説明してください。"""

        system_instruction = (
            "あなたは中国のQ&Aプラットフォーム「知乎（Zhihu）」のトレンドを "
            "日本語で解説するアシスタントです。簡潔かつ情報量のある要約を心がけてください。"
        )

        try:
            summary = self.gpt_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=200,
            )
            article.summary = summary
        except Exception as e:
            self.logger.error(f"要約生成に失敗: {e}")
            article.summary = f"要約生成エラー: {str(e)}"

    async def _store_articles(
        self, articles: list[Article], date_str: str
    ) -> list[tuple[str, str]]:
        """記事をJSON/Markdown形式で保存.

        Parameters
        ----------
        articles : list[Article]
            保存する記事リスト。
        date_str : str
            日付文字列（"YYYY-MM-DD"形式）。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパス [(json_path, md_path)]
        """
        if not articles:
            return []

        # JSON形式にシリアライズ
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

        # JSONファイル保存
        filename_json = f"{date_str}.json"
        json_path = await self.save_json(records, filename_json)

        # Markdown生成・保存
        markdown = self._render_markdown(records, date_str)
        filename_md = f"{date_str}.md"
        md_path = await self.save_markdown(markdown, filename_md)

        self.logger.info(f"{len(articles)}件の記事を保存しました: {date_str}")

        return [(str(json_path), str(md_path))]

    def _render_markdown(self, records: list[dict], date_str: str) -> str:
        """記事をMarkdown形式でレンダリング.

        Parameters
        ----------
        records : list[dict]
            記事のリスト。
        date_str : str
            日付文字列。

        Returns
        -------
        str
            Markdownコンテンツ。
        """
        content = f"# 知乎ホットトピック ({date_str})\n\n"

        for i, record in enumerate(records, 1):
            title = record.get("title", "")
            url = record.get("url", "")
            summary = record.get("summary", "")
            hot = record.get("popularity_score", 0)

            content += f"## {i}. [{title}]({url})\n\n"
            content += f"**人気度**: {hot:,.0f}\n\n"
            content += f"**要約**: {summary}\n\n"
            content += "---\n\n"

        return content
