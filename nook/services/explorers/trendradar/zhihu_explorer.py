"""知乎Explorer - TrendRadar経由で知乎のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
知乎（Zhihu）のホットトピックを取得するZhihuExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class ZhihuExplorer(BaseTrendRadarExplorer):
    """知乎のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、知乎（Zhihu）のホットトピックを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = ZhihuExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "zhihu"
    FEED_NAME = "zhihu"
    MARKDOWN_HEADER = "知乎ホットトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """ZhihuExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-zhihu",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下の知乎（Zhihu）ホットトピックを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. 記事の主な内容 (1-2文)
[記事の内容を簡潔に説明]

2. 重要なポイント (箇条書き3-5点)
- [ポイント1]
- [ポイント2]
- [ポイント3]

3. 議論の傾向 (コメントや反応から読み取れる場合)
[議論の方向性や主要な意見について短い説明]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のQ&Aプラットフォーム「知乎（Zhihu）」のトレンドを "
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "単なる翻訳ではなく、文化的背景や議論の文脈が伝わるような"
            "具体的で情報量の多い要約を作成してください。"
        )
