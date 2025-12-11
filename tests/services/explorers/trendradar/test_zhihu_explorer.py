"""Tests for ZhihuExplorer service.

This module tests the ZhihuExplorer class that retrieves hot topics
from Zhihu via the TrendRadar MCP server.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer


class TestZhihuExplorerInitialization:
    """Tests for ZhihuExplorer initialization."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer()

    def test_explorer_initialization(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Default initialization parameters.
        When: ZhihuExplorer is instantiated.
        Then: The explorer has correct service name and TrendRadarClient.
        """
        assert explorer.service_name == "trendradar-zhihu"
        assert explorer.client is not None

    def test_explorer_with_custom_storage_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: Custom storage directory.
        When: ZhihuExplorer is instantiated.
        Then: The storage path is configured correctly.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir="custom_data")
        assert "custom_data" in str(explorer.storage.base_dir)


class TestZhihuExplorerTransform:
    """Tests for TrendRadar to Article transformation."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer()

    def test_transform_trendradar_to_article(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar news item dict.
        When: _transform_to_article is called.
        Then: An Article object is returned with correct attributes.
        """
        trendradar_item = {
            "title": "测试热门话题",
            "url": "https://www.zhihu.com/question/123456",
            "hot": 1500000,
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.title == "测试热门话题"
        assert article.url == "https://www.zhihu.com/question/123456"
        assert article.popularity_score == 1500000
        assert article.feed_name == "zhihu"
        assert article.category == "hot"

    def test_transform_handles_missing_hot(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item without hot field.
        When: _transform_to_article is called.
        Then: popularity_score defaults to 0.
        """
        trendradar_item = {
            "title": "话题没有热度",
            "url": "https://www.zhihu.com/question/789",
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.popularity_score == 0

    def test_transform_parses_published_at(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with timestamp.
        When: _transform_to_article is called.
        Then: published_at is parsed correctly.
        """
        # Test with ISO string
        item_iso = {
            "title": "Article",
            "url": "http://test",
            "published_at": "2023-01-01T12:00:00",
        }
        article_iso = explorer._transform_to_article(item_iso)
        assert article_iso.published_at.year == 2023
        assert article_iso.published_at.month == 1

        # Test with timestamp (epoch) - assuming dateutil can handle or if we formatted it
        # Actually Parser handles string representations mostly.
        # If TrendRadar returns int timestamp, parser.parse(str(ts)) might work if it's year-first or standard.
        # But safest is ISO string test which is common.


class TestZhihuExplorerCollect:
    """Tests for ZhihuExplorer.collect method."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer()

    @pytest.mark.asyncio
    async def test_collect_returns_file_paths(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Mock TrendRadarClient returning news items.
        When: collect is called.
        Then: Returns list of (json_path, md_path) tuples.
        """
        mock_news = [
            {"title": "热门话题1", "url": "https://zhihu.com/q/1", "hot": 1000000},
            {"title": "热门话题2", "url": "https://zhihu.com/q/2", "hot": 500000},
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock GPT client to avoid actual API calls
            explorer.gpt_client.generate_content = MagicMock(
                return_value="要約テキスト"
            )

            result = await explorer.collect(days=1, limit=10)

            mock_get.assert_called_once_with(platform="zhihu", limit=10)
            # Result should be list of tuples
            assert isinstance(result, list)
            if result:  # If any files were saved
                assert all(isinstance(item, tuple) for item in result)

    @pytest.mark.asyncio
    async def test_collect_handles_empty_response(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: TrendRadarClient returns empty list.
        When: collect is called.
        Then: Returns empty list without error.
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            result = await explorer.collect(days=1, limit=10)

            assert result == []

    @pytest.mark.asyncio
    async def test_collect_raises_error_for_multi_day(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: days param != 1.
        When: collect is called.
        Then: Raises NotImplementedError.
        """
        with pytest.raises(NotImplementedError, match="Multi-day collection"):
            await explorer.collect(days=2)


class TestZhihuExplorerRun:
    """Tests for ZhihuExplorer.run method."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer()

    def test_run_calls_collect(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A ZhihuExplorer instance.
        When: run is called.
        Then: collect is invoked via asyncio.run.
        """
        with patch.object(explorer, "collect", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []

            explorer.run(days=2, limit=20)

            mock_collect.assert_called_once()
            # Verify days and limit were passed
            mock_collect.assert_called_once_with(days=2, limit=20)
