"""TencentExplorer - TrendRadar経由で腾讯新闻のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
腾讯新闻（Tencent News）のホットトピックを取得する
TencentExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class TencentExplorer(BaseTrendRadarExplorer):
    """腾讯新闻のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    腾讯新闻のニュースホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = TencentExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "tencent-hot"
    FEED_NAME = "tencent"
    MARKDOWN_HEADER = "腾讯新闻トレンド"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """TencentExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-tencent",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        return self._get_default_summary_prompt(
            article=article,
            platform_label="腾讯新闻",
            content_label="ニューストレンド",
            sections=[
                "ニュースの概要 (1-2文)\n[主要なニュース内容を簡潔に説明]",
                "重要なポイント (箇条書き3-5点)\n- [ポイント1: 事実関係]\n- [ポイント2: 関係企業・人物]\n- [ポイント3: 影響範囲]",
                "中国市場への影響\n[中国国内での反応や影響]",
                "日本・国際社会との関連\n[日本や国際社会への示唆]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のニュースメディア「腾讯新闻（Tencent News）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "ニュースの要点、社会的背景、中国市場での影響が"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
