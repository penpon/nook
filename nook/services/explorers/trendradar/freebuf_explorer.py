"""FreebufExplorer - TrendRadar経由でFreebufのホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
Freebuf（中国最大のサイバーセキュリティメディア）のホットトピックを取得する
FreebufExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class FreebufExplorer(BaseTrendRadarExplorer):
    """FreebufのホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    Freebufのセキュリティ関連ホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = FreebufExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "freebuf"
    FEED_NAME = "freebuf"
    MARKDOWN_HEADER = "Freebufセキュリティトレンド"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """FreebufExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-freebuf",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        return self._get_default_summary_prompt(
            article=article,
            platform_label="Freebuf",
            content_label="セキュリティトレンド",
            sections=[
                "セキュリティトピックの概要 (1-2文)\n[脅威・脆弱性・セキュリティ動向を簡潔に説明]",
                "技術的詳細 (箇条書き3-5点)\n- [ポイント1: 攻撃手法/脆弱性タイプ]\n- [ポイント2: 影響を受けるシステム]\n- [ポイント3: 検知・防御方法]",
                "業界への影響\n[セキュリティ業界や企業への影響]",
                "日本での対策・関連事例\n[日本での類似事例や推奨される対策]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のサイバーセキュリティメディア「Freebuf」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のセキュリティエンジニアに向けて、"
            "脅威の技術的詳細、攻撃手法、防御策、影響範囲が"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
