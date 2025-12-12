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

        # Test with timestamp (epoch)
        item_epoch = {
            "title": "Article Epoch",
            "url": "http://test-epoch",
            "timestamp": 1672531200,  # 2023-01-01 00:00:00 UTC
        }
        article_epoch = explorer._transform_to_article(item_epoch)
        assert article_epoch.published_at.year == 2023

    def test_transform_parses_epoch_zero(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with epoch timestamp 0.
        When: _transform_to_article is called.
        Then: published_at is 1970-01-01T00:00:00Z.
        """
        item = {
            "title": "Epoch Zero Article",
            "url": "http://test-epoch-zero",
            "timestamp": 0,
        }
        article = explorer._transform_to_article(item)
        assert article.published_at.year == 1970
        assert article.published_at.month == 1
        assert article.published_at.day == 1

    def test_transform_handles_malformed_hot(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with malformed hot field.
        When: _transform_to_article is called.
        Then: popularity_score defaults to 0.0 without raising exception.
        """
        item = {
            "title": "Malformed Hot",
            "url": "http://test-malformed",
            "hot": "N/A",
        }
        article = explorer._transform_to_article(item)
        assert article.popularity_score == 0.0


class TestZhihuExplorerCollect:
    """Tests for ZhihuExplorer.collect method."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer()
        # Mock storage to prevent disk I/O
        explorer.storage = AsyncMock()

        # Mock save methods to return dummy paths containing filename
        async def save_side_effect(data, filename):
            return f"mock/{filename}"

        explorer.storage.save.side_effect = save_side_effect
        return explorer

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
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                return_value=(
                    "このトピックは中国の技術コミュニティで活発に議論されており、"
                    "多くのエンジニアが関心を寄せています。"
                )
            )

            result = await explorer.collect(days=1, limit=10)

            mock_get.assert_called_once_with(platform="zhihu", limit=10)
            # Result should be non-empty list of 2-tuples
            assert result, "collect() should return non-empty list with mocked news"
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result), (
                "Each item should be a 2-tuple (json_path, md_path)"
            )

    @pytest.mark.asyncio
    async def test_collect_propagates_errors(self, explorer: ZhihuExplorer) -> None:
        """
        Given: TrendRadarClient raises an exception.
        When: collect is called.
        Then: The exception is propagated.
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await explorer.collect(days=1, limit=10)

    @pytest.mark.asyncio
    async def test_collect_raises_error_for_multi_day_with_days_param(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: days param != 1 and target_dates is None.
        When: collect is called.
        Then: Raises NotImplementedError.
        """
        with pytest.raises(NotImplementedError, match="Multi-day collection"):
            await explorer.collect(days=2)

    @pytest.mark.asyncio
    async def test_collect_validates_limit(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Invalid limit values.
        When: collect is called.
        Then: Raises ValueError.
        """
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=0)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=101)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=-5)

    @pytest.mark.asyncio
    async def test_collect_rejects_bool_limit(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Boolean value for limit parameter.
        When: collect is called.
        Then: Raises ValueError (bool is subclass of int in Python).
        """
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=True)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=False)

    @pytest.mark.asyncio
    async def test_collect_with_single_target_date(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Single date in target_dates parameter.
        When: collect is called.
        Then: Accepts the date and uses it for filename.
        """
        from datetime import date

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            target_date = date(2024, 1, 15)
            result = await explorer.collect(target_dates=[target_date])

            # ファイル名に指定した日付が使用されることを確認
            assert len(result) == 1
            json_path, md_path = result[0]
            assert "2024-01-15" in json_path
            assert "2024-01-15" in md_path

    @pytest.mark.asyncio
    async def test_collect_rejects_empty_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Empty target_dates list.
        When: collect is called.
        Then: Raises ValueError.
        """
        with pytest.raises(
            ValueError, match="target_dates must contain at least one date"
        ):
            await explorer.collect(target_dates=[])

    @pytest.mark.asyncio
    async def test_collect_with_multiple_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Multiple dates in target_dates parameter.
        When: collect is called.
        Then: Raises NotImplementedError.
        """
        from datetime import date

        target_dates = [date(2024, 1, 15), date(2024, 1, 16)]
        with pytest.raises(NotImplementedError, match="Multi-day collection"):
            await explorer.collect(target_dates=target_dates)

    @pytest.mark.asyncio
    async def test_collect_with_none_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: target_dates is None.
        When: collect is called.
        Then: Uses today's date for filename.
        """
        from datetime import datetime, timezone

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            result = await explorer.collect(target_dates=None)

            # 今日の日付が使用されることを確認
            assert len(result) == 1
            json_path, md_path = result[0]
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            assert today_str in json_path
            assert today_str in md_path

    @pytest.mark.asyncio
    async def test_collect_returns_empty_for_no_news(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: TrendRadarClient returns empty list.
        When: collect is called.
        Then: Returns empty list.
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            result = await explorer.collect(days=1, limit=10)

            assert result == []

    @pytest.mark.asyncio
    async def test_collect_handles_gpt_error(self, explorer: ZhihuExplorer) -> None:
        """
        Given: GPT client raises exception during summarization.
        When: collect is called.
        Then: Article summary contains error message and collect completes.
        """
        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock gpt_client.generate_async to raise exception
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                side_effect=Exception("GPT Error")
            )

            # Patch _store_articles to capture articles before saving
            original_store = explorer._store_articles
            captured_articles = []

            async def capture_and_store(articles, date_str):
                captured_articles.extend(articles)
                return await original_store(articles, date_str)

            with patch.object(
                explorer, "_store_articles", side_effect=capture_and_store
            ):
                result = await explorer.collect(days=1, limit=10)

            # Should complete and return file paths
            assert isinstance(result, list)
            # Verify error message is set in article summary (fixed message, no exception details)
            assert len(captured_articles) == 1
            assert (
                captured_articles[0].summary
                == ZhihuExplorer.ERROR_MSG_GENERATION_FAILED
            )
            # Ensure no exception details are leaked
            assert "GPT Error" not in captured_articles[0].summary


class TestZhihuExplorerRun:
    """Tests for ZhihuExplorer.run method."""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer()
        # Mock storage to prevent disk I/O (though run() mocks collect, it's safer)
        explorer.storage = AsyncMock()
        return explorer

    def test_run_calls_collect(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A ZhihuExplorer instance.
        When: run is called.
        Then: collect is invoked via asyncio.run.
        """
        with patch.object(explorer, "collect", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []

            explorer.run(days=1, limit=20)

            mock_collect.assert_called_once()
            # Verify days and limit were passed
            mock_collect.assert_called_once_with(days=1, limit=20)
