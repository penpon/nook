"""IT之家Explorer - TrendRadar経由でIT之家のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
IT之家（ITHome）のホットトピックを取得するIthomeExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class IthomeExplorer(BaseTrendRadarExplorer):
    """IT之家のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、IT之家（ITHome）のホットトピックを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = IthomeExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "ithome"
    FEED_NAME = "ithome"
    MARKDOWN_HEADER = "IT之家ホットトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """IthomeExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-ithome",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下のIT之家（ITHome）ホットトピックを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. ニュースの概要 (1-2文)
[製品・サービスの発表内容を簡潔に説明]

2. スペック・詳細情報 (箇条書き3-5点)
- [ポイント1: 製品スペック]
- [ポイント2: 価格・発売日]
- [ポイント3: 競合との比較]

3. 市場の反応
[中国市場での評価やユーザーの反応]

4. 日本市場への影響
[日本での発売可能性や影響の予測]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のテックニュースサイト「IT之家（ITHome）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "製品のスペックや価格情報、中国市場での反応や比較評価が"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
