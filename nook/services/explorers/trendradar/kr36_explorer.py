"""36氪Explorer - TrendRadar経由で36氪のホットトピックを取得.

このモジュールは、TrendRadar MCPサーバーを経由して
36氪（36Kr）のホットトピックを取得するKr36Explorerクラスを提供します。
"""

from nook.core.config import BaseConfig
from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer


class Kr36Explorer(BaseTrendRadarExplorer):
    """36氪のホットトピックをTrendRadar経由で取得するExplorer.

    TrendRadar MCPサーバーと通信し、36氪（36Kr）のホットトピックを
    取得・要約・保存します。

    Parameters
    ----------
    storage_dir : str, default="var/data"
        データ保存ディレクトリのルートパス。

    Examples
    --------
    >>> explorer = Kr36Explorer()
    >>> explorer.run(days=1, limit=20)
    """

    # プラットフォーム固有の設定
    PLATFORM_NAME = "36kr"
    FEED_NAME = "36kr"
    MARKDOWN_HEADER = "36氪ホットトピック"

    def __init__(self, storage_dir: str = "var/data", config: BaseConfig | None = None):
        """Kr36Explorerを初期化.

        Parameters
        ----------
        storage_dir : str, default="var/data"
            データ保存ディレクトリのルートパス。
        config : BaseConfig | None, default=None
            設定オブジェクト。
        """
        super().__init__(
            service_name="trendradar-36kr",
            storage_dir=storage_dir,
            config=config,
        )

    def _get_summary_prompt(self, article: Article) -> str:
        """GPT要約用のプロンプトを生成."""
        safe_title = self._sanitize_prompt_input(article.title, max_length=200)
        safe_url = self._sanitize_prompt_input(article.url, max_length=500)
        safe_text = self._sanitize_prompt_input(article.text or "", max_length=500)

        return f"""以下の36氪（36Kr）ホットトピックを日本語で詳細に要約してください。

タイトル: {safe_title}
URL: {safe_url}
説明: {safe_text}

以下のフォーマットで出力してください：

1. ビジネスニュースの概要 (1-2文)
[企業・投資・事業の内容を簡潔に説明]

2. ビジネスポイント (箇条書き3-5点)
- [ポイント1: 資金調達額・評価額]
- [ポイント2: ビジネスモデル・収益構造]
- [ポイント3: 市場規模・成長性]

3. 業界構造・競争環境
[競合他社や市場ポジションの分析]

4. 日本企業への示唆
[日本市場での展開可能性や参考になる戦略]"""

    def _get_system_instruction(self) -> str:
        """GPT要約用のシステム指示を取得."""
        return (
            "あなたは中国のスタートアップメディア「36氪（36Kr）」のトレンドを"
            "日本語で解説する専門のアシスタントです。日本のビジネスパーソンに向けて、"
            "投資規模、ビジネスモデル、競争環境、成長戦略などのビジネス視点が"
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
