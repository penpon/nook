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
