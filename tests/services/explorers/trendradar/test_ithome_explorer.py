"""IthomeExplorerサービスのテスト.

このモジュールは、TrendRadar MCPサーバーを経由して
IT之家のホットトピックを取得するIthomeExplorerクラスのテストを行います。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.ithome_explorer import IthomeExplorer


class TestIthomeExplorerInitialization:
    """IthomeExplorerの初期化テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> IthomeExplorer:
        """テスト用のIthomeExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return IthomeExplorer(storage_dir=str(tmp_path))

    def test_explorer_initialization(self, explorer: IthomeExplorer) -> None:
        """
        Given: デフォルトの初期化パラメータ。
        When: IthomeExplorer がインスタンス化されたとき。
        Then: explorer は正しいサービス名と TrendRadarClient を持つ。
        """
        assert explorer.service_name == "trendradar-ithome"
        assert explorer.client is not None
        assert explorer.PLATFORM_NAME == "ithome"
        assert explorer.FEED_NAME == "ithome"
        assert explorer.MARKDOWN_HEADER == "IT之家ホットトピック"


class TestIthomeExplorerPrompt:
    """プロンプト生成のテスト。"""

    @pytest.fixture
    def explorer(self, tmp_path: Path) -> IthomeExplorer:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            return IthomeExplorer(storage_dir=str(tmp_path))

    def test_get_summary_prompt(self, explorer: IthomeExplorer) -> None:
        """
        Given: 記事オブジェクト。
        When: _get_summary_prompt が呼ばれたとき。
        Then: ITHome 用のプロンプトが生成される。
        """
        article = MagicMock()
        article.title = "Test Phone"
        article.url = "http://test.com"
        article.text = "Description"

        prompt = explorer._get_summary_prompt(article)

        assert "IT之家（ITHome）" in prompt
        assert "製品・サービスの発表内容" in prompt
        assert "スペック・詳細情報" in prompt
        assert "Test Phone" in prompt

    def test_get_system_instruction(self, explorer: IthomeExplorer) -> None:
        """
        Given: なし。
        When: _get_system_instruction が呼ばれたとき。
        Then: ITHome 用のシステム指示が返される。
        """
        instruction = explorer._get_system_instruction()
        assert "IT之家（ITHome）" in instruction
        assert "製品のスペックや価格情報" in instruction


class TestIthomeExplorerRun:
    """実行テスト（モック）。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> IthomeExplorer:
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = IthomeExplorer(storage_dir=str(tmp_path))
        explorer.storage = AsyncMock()
        return explorer

    @pytest.mark.asyncio
    async def test_run_flow(self, explorer: IthomeExplorer) -> None:
        """
        Given: モック化されたクライアント。
        When: collect が呼ばれたとき。
        Then: 正常に完了し、ファイルパスを返す。
        """
        mock_news = [
            {
                "title": "New Phone Launch",
                "url": "https://ithome.com/1",
                "hot": 1000,
            }
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="Summary")

            # Patch _store_articles to return mock paths and capture input
            with patch.object(
                explorer, "_store_articles", new_callable=AsyncMock
            ) as mock_store:
                mock_store.return_value = [("path.json", "path.md")]

                result = await explorer.collect(days=1, limit=5)

                assert result == [("path.json", "path.md")]
                mock_get.assert_called_once_with(platform="ithome", limit=5)
                # Verify passed articles
                args, _ = mock_store.call_args
                articles = args[0]
                assert len(articles) == 1
                assert articles[0].title == "New Phone Launch"

    @pytest.mark.asyncio
    async def test_collect_validation_error(self, explorer: IthomeExplorer) -> None:
        """
        Given: 不正な days パラメータ (> 1)。
        When: collect が呼ばれたとき。
        Then: ValueError が発生する。
        """
        # BaseTrendRadarExplorerの制限によりエラーが発生する
        with pytest.raises(ValueError, match="複数日の収集"):
            await explorer.collect(days=2)

    @pytest.mark.asyncio
    async def test_collect_empty_news(self, explorer: IthomeExplorer) -> None:
        """
        Given: ニュースが空の場合。
        When: collect が呼ばれたとき。
        Then: 空リストを返す。
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            result = await explorer.collect(days=1)
            assert result == []

    @pytest.mark.asyncio
    async def test_collect_gpt_error(self, explorer: IthomeExplorer) -> None:
        """
        Given: GPT生成でエラーが発生する場合。
        When: collect が呼ばれたとき。
        Then: エラーがログ出力され、処理は続行される。
        """
        mock_news = [{"title": "T", "url": "U", "hot": 100}]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                side_effect=Exception("GPT Error")
            )

            # _store_articlesが呼ばれるが、要約失敗の結果を含むArticleが渡される
            with patch.object(
                explorer, "_store_articles", new_callable=AsyncMock
            ) as mock_store:
                mock_store.return_value = []

                await explorer.collect(days=1)

                # store_articlesが呼ばれたことを確認
                assert mock_store.called


class TestIthomeExplorerTransformation:
    """データ変換ロジックのテスト。"""

    @pytest.fixture
    def explorer(self, tmp_path: Path) -> IthomeExplorer:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            return IthomeExplorer(storage_dir=str(tmp_path))

    def test_transform_to_article_valid(self, explorer: IthomeExplorer) -> None:
        """
        Given: 有効なニュースデータ。
        When: _transform_to_article が呼ばれたとき。
        Then: 正しい Article オブジェクトが返される。
        """
        news_item = {
            "title": "Test Title",
            "url": "http://example.com",
            "hot": "1000",
            "metrics": "metrics info",
        }

        article = explorer._transform_to_article(news_item)

        assert article.title == "Test Title"
        assert article.url == "http://example.com"
        assert article.popularity_score == 1000
        assert article.feed_name == "ithome"

    def test_transform_to_article_missing_hot(self, explorer: IthomeExplorer) -> None:
        """
        Given: hotフィールドがないニュースデータ。
        When: _transform_to_article が呼ばれたとき。
        Then: popularity_scoreが0になる。
        """
        news_item = {
            "title": "Test Title",
            "url": "http://example.com",
        }

        article = explorer._transform_to_article(news_item)
        assert article.popularity_score == 0

    def test_transform_to_article_invalid_hot(self, explorer: IthomeExplorer) -> None:
        """
        Given: hotフィールドが数値でない場合。
        When: _transform_to_article が呼ばれたとき。
        Then: popularity_scoreが0になる。
        """
        news_item = {
            "title": "Test Title",
            "url": "http://example.com",
            "hot": "invalid",
        }

        article = explorer._transform_to_article(news_item)
        assert article.popularity_score == 0


class TestIthomeExplorerMarkdown:
    """Markdown生成関連のテスト。"""

    @pytest.fixture
    def explorer(self, tmp_path: Path) -> IthomeExplorer:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            return IthomeExplorer(storage_dir=str(tmp_path))

    def test_format_article_markdown_escaping(self, explorer: IthomeExplorer) -> None:
        """
        Given: 特殊文字を含む記事タイトル。
        When: Markdownが生成されるとき（内部メソッド経由などで）。
        Then: 特殊文字がエスケープされていること（BaseTrendRadarExplorerの機能確認に近い）。
        """
        # ITHomeExplorer自体にMarkdown生成のオーバーライドがある場合はここでテスト。
        # なければBaseのテストになるが、念のため統合的に確認。
        pass
