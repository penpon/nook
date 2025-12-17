"""WeiboExplorer - TrendRadar経由で微博のホットサーチを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
微博（Weibo）のホットサーチを取得するWeiboExplorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class WeiboExplorer(BaseTrendRadarExplorer):
    """微博のホットサーチをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、微博（Weibo）のホットサーチを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = WeiboExplorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "weibo"
    FEED_NAME = "weibo"
    MARKDOWN_HEADER = "微博ホットサーチ"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """WeiboExplorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-weibo",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下の微博（Weibo）ホットサーチを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. トレンドの概要 (1-2文)
[話題になっている内容を簡潔に説明]

2. 話題のポイント (箇条書き3-5点)
- [ポイント1: 発端・きっかけ]
- [ポイント2: 主要な意見・反応]
- [ポイント3: 関連するハッシュタグ・キーワード]

3. 世論の傾向
[賛否・感情的反応・議論の方向性]

4. 文化的背景
[日本人に伝わりにくい文化的コンテキストの補足]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のSNSプラットフォーム「微博（Weibo）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のユーザーに向けて、"
            "トレンドの背景、世論の反応、話題になった理由や文化的コンテキストが"
            "伝わるような具体的で情報量の多い要約を作成してください。"
        )

    def _parse_popularity_score(self, value: object) -> float:
        """人気スコアをパース（万/億対応）."""
        if value is None:
            return 0.0

        try:
            val_str = str(value).strip().replace(",", "")
            if "万" in val_str:
                return float(val_str.replace("万", "")) * 10000
            if "億" in val_str:
                return float(val_str.replace("億", "")) * 100000000
            return float(val_str)
        except (ValueError, TypeError):
            return super()._parse_popularity_score(value)
