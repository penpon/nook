"""掘金Explorer - TrendRadar経由で掘金のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
掘金（Juejin）のホットトピックを取得するJuejinExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class JuejinExplorer(BaseTrendRadarExplorer):
    """掘金のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、掘金（Juejin）のホットトピックを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = JuejinExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "juejin"
    FEED_NAME = "juejin"
    MARKDOWN_HEADER = "掘金ホットトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """JuejinExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-juejin",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下の掘金（Juejin）ホットトピックを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. 技術トピックの概要 (1-2文)
[技術的な内容を簡潔に説明]

2. 技術的なポイント (箇条書き3-5点)
- [ポイント1: 使用技術・フレームワーク]
- [ポイント2: 実装のアプローチ]
- [ポイント3: パフォーマンス・最適化]

3. 開発者コミュニティの反応
[コメントでの議論やフィードバックの傾向]

4. 日本の開発者への示唆
[日本での適用可能性や類似事例]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国の開発者コミュニティ「掘金（Juejin）」のトレンドを "
            "日本語で解説する専門のアシスタントです。日本のエンジニアに向けて、"
            "技術的な背景やコード例の意図、開発者間での議論のポイントが"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
