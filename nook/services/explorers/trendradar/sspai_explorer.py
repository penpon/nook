"""SspaiExplorer - TrendRadar経由で少数派のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
少数派（SSPai）のホットトピックを取得するSspaiExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class SspaiExplorer(BaseTrendRadarExplorer):
    """少数派のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、
    少数派（SSPai）のホットトピックを取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。
    config : BaseConfig | None, default=None
        設定オブジェクト。

    Examples
    --------
    >>> explorer = SspaiExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "sspai"
    FEED_NAME = "sspai"
    MARKDOWN_HEADER = "少数派ホットトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """SspaiExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-sspai",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下の少数派（SSPai）ホットトピックを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. コンテンツの概要 (1-2文)
[紹介されているアプリ・ツール・手法を簡潔に説明]

2. 機能・特徴 (箇条書き3-5点)
- [ポイント1: 主要機能]
- [ポイント2: 対応プラットフォーム]
- [ポイント3: 価格・ライセンス]

3. 活用シーン
[具体的なユースケースや組み合わせ]

4. 日本での代替・類似ツール
[日本で入手可能な類似ツールの紹介]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のデジタルライフメディア「少数派（SSPai）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "アプリの機能、ワークフローの具体例、生産性向上のコツが"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )
