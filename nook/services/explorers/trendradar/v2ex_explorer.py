"""V2exExplorer - TrendRadar経由でV2EXのホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
V2EX（中国の開発者コミュニティ）のホットトピックを取得する
V2exExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class V2exExplorer(BaseTrendRadarExplorer):
    """V2EXのホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    V2EXの開発者コミュニティのホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = V2exExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "v2ex"
    FEED_NAME = "v2ex"
    MARKDOWN_HEADER = "V2EXトレンドトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """V2exExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-v2ex",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        return self._get_default_summary_prompt(
            article=article,
            platform_label="V2EX",
            content_label="トレンドトピック",
            sections=[
                "トピックの概要 (1-2文)\n[議論されている技術やトピックを簡潔に説明]",
                "議論のポイント (箇条書き3-5点)\n- [ポイント1: 主要な意見・提案]\n- [ポイント2: 技術的な詳細]\n- [ポイント3: コミュニティの反応]",
                "開発者コミュニティの動向\n[トレンドや共通の関心事]",
                "日本の開発者への示唆\n[日本での適用可能性や参考になる点]",
            ],
        )

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国の開発者コミュニティ「V2EX」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のエンジニアに向けて、"
            "技術的な議論のポイント、開発者の意見、キャリアに関する洞察が"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
