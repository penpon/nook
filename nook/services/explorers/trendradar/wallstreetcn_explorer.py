"""WallstreetcnExplorer - TrendRadar経由で华尔街见闻のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
华尔街见闻（中国の金融・投資ニュースメディア）のホットトピックを取得する
WallstreetcnExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class WallstreetcnExplorer(BaseTrendRadarExplorer):
    """华尔街见闻のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    华尔街见闻の金融・投資関連ホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = WallstreetcnExplorer()
    >>> explorer.collect(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "wallstreetcn-hot"
    FEED_NAME = "wallstreetcn"
    MARKDOWN_HEADER = "华尔街见闻金融トレンド"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """WallstreetcnExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-wallstreetcn",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        return self._get_default_summary_prompt(
            article=article,
            platform_label="华尔街见闻",
            content_label="金融トレンド",
            sections=[
                "金融ニュースの概要 (1-2文)\n[市場動向・投資情報を簡潔に説明]",
                "投資ポイント (箇条書き3-5点)\n"
                "- [ポイント1: 市場インパクト]\n"
                "- [ポイント2: 関連銘柄・セクター]\n"
                "- [ポイント3: 数値データ（資金調達額等）]",
                "市場の反応・見通し\n[アナリストの見解や市場の反応]",
                "日本市場への影響\n[日本の投資家・企業への示唆]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国の金融メディア「华尔街见闻（Wallstreetcn）」のトレンドを日本語で解説する専門のアシスタントです。"
            "日本の投資家やビジネスパーソンに向けて、市場動向、投資判断に影響する要因、企業業績が伝わるような具体的で情報量の多い要約を作成してください。"
        )
