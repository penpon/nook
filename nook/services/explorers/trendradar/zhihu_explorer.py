"""Zhihu Explorer - TrendRadar経由で知乎のホットトピックを取得.

This module provides the ZhihuExplorer class that retrieves hot topics
from Zhihu via the TrendRadar MCP server.
"""

import asyncio
import html
from datetime import date, datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.base.base_service import BaseService
from nook.services.explorers.trendradar.trendradar_client import TrendRadarClient


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

    # APIレート制限と処理時間のバランスを考慮し、1回あたりの取得数を制限 (Default: 15)
    # QiitaExplorerなどと比較しても、詳細な要約生成にはコストがかかるため保守的な値を設定
    TOTAL_LIMIT = 15

    # GPT設定
    GPT_TEMPERATURE = 0.3
    GPT_MAX_TOKENS = 200

    # 並列実行制限（APIレート制限対策）
    MAX_CONCURRENT_REQUESTS = 5

    # エラーメッセージ定数
    ERROR_MSG_EMPTY_SUMMARY = "要約を生成できませんでした（空のレスポンス）"
    ERROR_MSG_GENERATION_FAILED = "要約生成に失敗しました"

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
            config = BaseConfig(DATA_DIR=storage_dir)
        else:
            # Pydantic v2 の model_copy を使用して安全にコピー
            config = config.model_copy(update={"DATA_DIR": storage_dir})

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
        # target_dates のバリデーション
        if target_dates is not None:
            if len(target_dates) == 0:
                raise ValueError("target_dates must contain at least one date")
            if len(target_dates) > 1:
                raise NotImplementedError(
                    "Multi-day collection (len(target_dates) > 1) is not yet implemented. "
                    "Please provide a single date or use days=1."
                )
            # 単一日付の場合は受け入れる
            target_date = target_dates[0]
        else:
            # target_dates が None の場合は今日の日付を使用
            target_date = datetime.now(timezone.utc).date()

        # days パラメータは target_dates が None の場合のみ使用
        if target_dates is None and days != 1:
            raise NotImplementedError(
                "Multi-day collection (days > 1) is not yet implemented"
            )

        # target_dates 指定時に days != 1 はエラー（混乱を防ぐ）
        if target_dates is not None and days != 1:
            raise ValueError(
                "days parameter must be 1 (or omitted) when target_dates is provided. "
                "The days parameter is ignored when target_dates is specified."
            )

        # limit のバリデーション
        if limit is not None:
            # boolはintのサブクラスなので明示的に除外
            if (
                not isinstance(limit, int)
                or isinstance(limit, bool)
                or limit < 1
                or limit > 100
            ):
                raise ValueError(
                    f"limit must be an integer between 1 and 100, got {limit}"
                )
            effective_limit = limit
        else:
            effective_limit = self.TOTAL_LIMIT

        # TrendRadarからデータ取得
        news_items = await self.client.get_latest_news(
            platform="zhihu", limit=effective_limit
        )

        if not news_items:
            self.logger.info("取得したホットトピックがありません")
            return []

        # Article オブジェクトに変換
        articles = [self._transform_to_article(item) for item in news_items]

        # GPT要約を生成（並列実行でパフォーマンス向上）
        # Semaphoreで同時実行数を制限してAPIレート制限を回避
        sem = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        async def bounded_summarize(a: Article) -> None:
            async with sem:
                await self._summarize_article(a)

        # return_exceptions=Trueで1つの要約が失敗しても他の要約を継続
        results = await asyncio.gather(
            *[bounded_summarize(article) for article in articles],
            return_exceptions=True,
        )

        # 例外チェック: _summarize_article内でキャッチしきれなかった想定外のエラーを確認
        for i, res in enumerate(results):
            if isinstance(res, BaseException):
                if isinstance(res, asyncio.CancelledError):
                    self.logger.warning(
                        f"Summary generation cancelled for article: {articles[i].title}"
                    )
                    raise res

                self.logger.error(
                    f"Unexpected error in summary generation for article '{articles[i].title}': {res}",
                    exc_info=res,
                )
                if not articles[i].summary:
                    articles[i].summary = self.ERROR_MSG_GENERATION_FAILED
                # 予期せぬエラーは再送出して収集処理を失敗させる
                raise res

        # 日付別にグループ化して保存
        date_str = target_date.strftime("%Y-%m-%d")
        saved_files = await self._store_articles(articles, date_str)

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
            soup=BeautifulSoup("", "html.parser"),
            category="hot",
            popularity_score=self._parse_popularity_score(item.get("hot", 0)),
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
            if val is None:
                continue
            # Epoch timestamp handling
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                try:
                    return datetime.fromtimestamp(val, tz=timezone.utc)
                except (ValueError, OverflowError):
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

    def _parse_popularity_score(self, value: object) -> float:
        """人気スコアを安全にパース.

        Parameters
        ----------
        value : object
            パースする値。

        Returns
        -------
        float
            パースされた人気スコア。失敗時は0.0。
        """
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    async def _summarize_article(self, article: Article) -> None:
        """記事の要約を生成（in-place mutator）.

        このメソッドは記事オブジェクトの `summary` フィールドを直接変更します。
        asyncio.gather等で並列実行する場合、各Articleオブジェクトが独立している
        ことを前提としています。同一オブジェクトを複数タスクで共有しないでください。

        Parameters
        ----------
        article : Article
            要約を生成する記事。
        """
        prompt = f"""以下の知乎（Zhihu）ホットトピックを日本語で簡潔に要約してください。

タイトル: {article.title}
URL: {article.url}
説明: {article.text[:500]}
人気度（ホット値）: {article.popularity_score:,.0f}

要約は1-2文で、このトピックが何について議論されているかを説明してください。"""

        system_instruction = (
            "あなたは中国のQ&Aプラットフォーム「知乎（Zhihu）」のトレンドを "
            "日本語で解説するアシスタントです。簡潔かつ情報量のある要約を心がけてください。"
        )

        try:
            # GPTClientの非同期メソッドを使用してイベントループをブロックしない
            summary = await self.gpt_client.generate_async(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=self.GPT_TEMPERATURE,
                max_tokens=self.GPT_MAX_TOKENS,
            )
            # 空の要約をフォールバック（空白のみの場合も弾く）
            if summary and summary.strip():
                article.summary = summary
            else:
                self.logger.warning(
                    f"GPT returned empty summary for article: {article.title}"
                )
                article.summary = self.ERROR_MSG_EMPTY_SUMMARY
        except asyncio.CancelledError:
            # キャンセルは即座に再送出して呼び出し元のキャンセル処理を有効にする
            raise
        except Exception:
            # 詳細はログにのみ記録（スタックトレース含む）
            self.logger.exception(f"要約生成に失敗 (article: {article.title})")
            # 成果物には固定メッセージのみ
            article.summary = self.ERROR_MSG_GENERATION_FAILED

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
            # Markdownの特殊文字をエスケープ
            raw_title = record.get("title", "")
            # HTML特殊文字のエスケープに加え、Markdownリンクを壊す [] をエスケープ
            title = html.escape(raw_title).replace("[", "\\[").replace("]", "\\]")

            raw_url = record.get("url", "")
            # URL内の ) がMarkdownリンクを早期に閉じてしまうのを防ぐ
            url = raw_url.replace(")", "\\)")

            # summary も Markdown を壊す可能性のある文字をエスケープ
            raw_summary = record.get("summary", "")
            summary = html.escape(raw_summary).replace("[", "\\[").replace("]", "\\]")
            hot = record.get("popularity_score", 0)

            content += f"## {i}. [{title}]({url})\n\n"
            content += f"**人気度**: {hot:,.0f}\n\n"
            content += f"**要約**: {summary}\n\n"
            content += "---\n\n"

        return content
