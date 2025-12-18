"""ProductHuntExplorer - TrendRadar経由でProduct Huntのホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
Product Huntのホットトピックを取得するProductHuntExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class ProductHuntExplorer(BaseTrendRadarExplorer):
    """Product HuntのホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    Product Huntのホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = ProductHuntExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "producthunt"
    FEED_NAME = "producthunt"
    MARKDOWN_HEADER = "Product Huntトレンド"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """ProductHuntExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-producthunt",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成.

        与えられた記事（Article）の情報を元に、Product Huntのコンテキストに
        最適化された要約用プロンプトを作成します。

        Parameters
        ----------
        article : Article
            要約対象の記事オブジェクト。

        Returns
        -------
        str
            生成されたプロンプト文字列。
        """
        return self._get_default_summary_prompt(
            article=article,
            platform_label="Product Hunt",
            content_label="トレンド",
            sections=[
                "プロダクト概要 (1-2文)\n[サービス・製品の内容を簡潔に説明]",
                "主要機能 (箇条書き3-5点)\n- [ポイント1: コア機能]\n- [ポイント2: 差別化ポイント]\n- [ポイント3: 料金プラン]",
                "コミュニティの評価\n[Upvote数、コメントの傾向、メーカーの反応]",
                "日本での利用可能性\n[日本語対応、日本市場での展開可能性]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得.

        Returns
        -------
        str
            GPTに与えるシステム指示（Role設定）。
        """
        return (
            "あなたはプロダクト発見プラットフォーム「Product Hunt」のトレンドを"
            "日本語で解説する専門のアシスタントです。英語のプロダクト情報を"
            "的確に理解し、日本のユーザーに向けて、プロダクトの機能、ターゲット層、"
            "ビジネスモデル、類似サービスとの比較が伝わるような"
            "具体的で情報量の多い要約を作成してください。"
        )
