"""ToutiaoExplorer - TrendRadar経由で今日头条のホットニュースを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
今日头条（Toutiao）のホットニュースを取得するToutiaoExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class ToutiaoExplorer(BaseTrendRadarExplorer):
    """今日头条のホットニュースをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    今日头条（Toutiao）のホットニュースを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = ToutiaoExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "toutiao"
    FEED_NAME = "toutiao"
    MARKDOWN_HEADER = "今日头条ホットニュース"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """ToutiaoExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-toutiao",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        return self._get_default_summary_prompt(
            article=article,
            platform_label="今日头条（Toutiao）",
            content_label="ホットニュース",
            sections=[
                "ニュースの概要 (1-2文)\n[主要なニュース内容を簡潔に説明]",
                "重要なポイント (箇条書き3-5点)\n- [ポイント1: 事実関係]\n- [ポイント2: 関係者・組織]\n- [ポイント3: 影響範囲]",
                "社会的影響\n[このニュースがもたらす影響や意味]",
                "国際的視点\n[日本や国際社会との関連性]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のニュースアグリゲーター「今日头条（Toutiao）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "ニュースの要点、社会的影響、異なる視点からの分析が"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
