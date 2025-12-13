"""Tests for TrendRadar MCP client.

This module tests the TrendRadarClient class that communicates with
the TrendRadar MCP server via FastMCP to retrieve hot topics from Chinese platforms.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.trendradar_client import (
    TrendRadarClient,
    TrendRadarError,
)


@pytest.fixture
def client():
    """Fixture for TrendRadarClient."""
    return TrendRadarClient()


class TestTrendRadarClientInitialization:
    """Tests for TrendRadarClient initialization."""

    def test_client_initialization_with_default_url(self):
        """
        Given: No URL provided.
        When: TrendRadarClient is initialized.
        Then: Default URL is used.
        """
        client = TrendRadarClient()
        assert client.base_url == "http://localhost:3333/mcp"

    def test_client_initialization_with_custom_url(self):
        """
        Given: Custom URL provided.
        When: TrendRadarClient is initialized.
        Then: Custom URL is used.
        """
        custom_url = "http://custom-server:8080/mcp"
        client = TrendRadarClient(base_url=custom_url)
        assert client.base_url == custom_url


class TestGetLatestNews:
    """Tests for get_latest_news method."""

    @pytest.mark.asyncio
    async def test_get_latest_news_returns_list(self):
        """
        Given: TrendRadar server returns valid response.
        When: get_latest_news is called.
        Then: A list of news items is returned.
        """
        mock_result = MagicMock()
        mock_result.data = {
            "success": True,
            "news": [
                {
                    "title": "Sample hot topic",
                    "platform": "zhihu",
                    "rank": 1,
                },
            ],
        }
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["title"] == "Sample hot topic"

    @pytest.mark.asyncio
    async def test_get_latest_news_parses_content_blocks(self):
        """
        Given: Response has no .data but has .content with TextContent.
        When: get_latest_news is called.
        Then: JSON from content is parsed and returned.
        """
        mock_text_content = MagicMock()
        mock_text_content.text = (
            '{"success": true, "news": [{"title": "From content"}]}'
        )
        mock_result = MagicMock()
        mock_result.data = None
        mock_result.content = [mock_text_content]

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert len(result) == 1
            assert result[0]["title"] == "From content"

    @pytest.mark.asyncio
    async def test_get_latest_news_multiple_calls(self):
        """
        Given: TrendRadarClient instance.
        When: get_latest_news is called multiple times.
        Then: Each call succeeds without client reuse issues.
        """
        mock_result = MagicMock()
        mock_result.data = {"success": True, "news": [{"title": "Topic"}]}
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result1 = await client.get_latest_news(platform="zhihu")
            result2 = await client.get_latest_news(platform="zhihu")

            assert len(result1) == 1
            assert len(result2) == 1
            assert mock_client.call_tool.call_count == 2
            # Verify new Client is created for each request
            assert MockClient.call_count == 2

    @pytest.mark.asyncio
    async def test_get_latest_news_with_platform_filter(self):
        """
        Given: Specific platform specified.
        When: get_latest_news is called with platform parameter.
        Then: Request is made with correct platform parameter.
        """
        mock_result = MagicMock()
        mock_result.data = {"success": True, "news": []}
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            await client.get_latest_news(platform="zhihu", limit=10)

            mock_client.call_tool.assert_called_once_with(
                "get_latest_news", {"platforms": ["zhihu"], "limit": 10}
            )

    @pytest.mark.asyncio
    async def test_get_latest_news_with_limit(self):
        """
        Given: Limit parameter specified.
        When: get_latest_news is called with limit.
        Then: Request includes limit parameter.
        """
        mock_result = MagicMock()
        mock_result.data = {"success": True, "news": [{"title": "Topic 1"}]}
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu", limit=5)

            assert isinstance(result, list)
            mock_client.call_tool.assert_called_once_with(
                "get_latest_news", {"platforms": ["zhihu"], "limit": 5}
            )

    @pytest.mark.asyncio
    async def test_get_latest_news_handles_error_response(self):
        """
        Given: Response indicates an error.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        mock_result = MagicMock()
        mock_result.data = {
            "success": False,
            "error": {"code": "DATA_NOT_FOUND", "message": "No data found"},
        }
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "TrendRadar error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_latest_news_allows_empty_news(self):
        """
        Given: Response contains empty news list.
        When: get_latest_news is called.
        Then: Empty list is returned without error.
        """
        mock_result = MagicMock()
        mock_result.data = {"success": True, "news": []}
        mock_result.content = []

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_news_raises_error_on_empty_result(self):
        """
        Given: Response is empty/None.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            client = TrendRadarClient()

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "Empty response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_latest_news_raises_error_on_exception(self):
        """
        Given: FastMCP client raises exception.
        When: get_latest_news is called.
        Then: TrendRadarError is propagated.
        """
        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(side_effect=Exception("Connection error"))
            MockClient.return_value = mock_client

            client = TrendRadarClient()

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "Failed to get news" in str(exc_info.value)


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """
        Given: TrendRadar server is running.
        When: health_check is called.
        Then: True is returned.
        """
        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.ping = AsyncMock()
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_on_exception(self):
        """
        Given: TrendRadar server is unreachable (raises exception).
        When: health_check is called.
        Then: False is returned.
        """
        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.health_check()

            assert result is False


class TestParameterValidation:
    """Tests for parameter validation."""

    @pytest.mark.asyncio
    async def test_invalid_platform_raises_value_error(self):
        """
        Given: Invalid platform parameter.
        When: get_latest_news is called with unsupported platform.
        Then: ValueError is raised.
        """
        client = TrendRadarClient()

        # Test empty platform
        with pytest.raises(ValueError) as exc_info:
            await client.get_latest_news(platform="", limit=10)
        assert "Invalid platform" in str(exc_info.value)

        # Test unsupported platform
        with pytest.raises(ValueError) as exc_info:
            await client.get_latest_news(platform="unsupported", limit=10)
        assert "Invalid platform" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_limit_raises_value_error(self):
        """
        Given: Invalid limit parameter.
        When: get_latest_news is called with out-of-range limit.
        Then: ValueError is raised.
        """
        client = TrendRadarClient()

        # Test negative limit
        with pytest.raises(ValueError) as exc_info:
            await client.get_latest_news(platform="zhihu", limit=-1)
        assert "Invalid limit" in str(exc_info.value)

        # Test zero limit
        with pytest.raises(ValueError) as exc_info:
            await client.get_latest_news(platform="zhihu", limit=0)
        assert "Invalid limit" in str(exc_info.value)

        # Test limit > 100
        with pytest.raises(ValueError) as exc_info:
            await client.get_latest_news(platform="zhihu", limit=101)
        assert "Invalid limit" in str(exc_info.value)


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_can_be_called(self):
        """
        Given: Client instance.
        When: close is called.
        Then: No error is raised (close is a no-op since each request creates new client).
        """
        client = TrendRadarClient()

        # close() should not raise error
        await client.close()

    @pytest.mark.asyncio
    async def test_close_can_be_called_multiple_times(self):
        """
        Given: Client instance.
        When: close is called multiple times.
        Then: No error is raised.
        """
        client = TrendRadarClient()

        # First close
        await client.close()

        # Second close should not raise error
        await client.close()


class TestExtractNewsItems:
    """Tests for _extract_news_items helper method."""

    def test_extract_news_items_with_primitive_payload(self):
        """
        Given: Primitive type payload (string).
        When: _extract_news_items is called.
        Then: Payload is wrapped in dict with 'text' key.
        """
        client = TrendRadarClient()

        result = client._extract_news_items("plain text payload")

        assert result == [{"text": "plain text payload"}]

    def test_extract_news_items_with_items_key(self):
        """
        Given: Payload with 'items' key instead of 'news'.
        When: _extract_news_items is called.
        Then: Items are extracted correctly.
        """
        client = TrendRadarClient()

        result = client._extract_news_items(
            {"success": True, "items": [{"title": "Item 1"}, {"title": "Item 2"}]}
        )

        assert len(result) == 2
        assert result[0]["title"] == "Item 1"

    def test_extract_news_items_with_unknown_dict_structure(self):
        """
        Given: Dict with unknown structure (no 'news' or 'items').
        When: _extract_news_items is called.
        Then: Original dict is returned wrapped in a list with warning logged.
        """
        client = TrendRadarClient()

        result = client._extract_news_items({"custom_key": "custom_value"})

        assert result == [{"custom_key": "custom_value"}]

    def test_extract_news_items_with_empty_dict(self):
        """
        Given: Empty dict payload.
        When: _extract_news_items is called.
        Then: Empty list is returned.
        """
        client = TrendRadarClient()

        result = client._extract_news_items({})

        assert result == []


class TestGetLatestNewsFallbackPaths:
    """Tests for get_latest_news fallback handling paths."""

    @pytest.mark.asyncio
    async def test_get_latest_news_handles_non_json_content(self):
        """
        Given: Response has content.text that is not valid JSON.
        When: get_latest_news is called.
        Then: Content is returned as-is wrapped in list with 'text' key.
        """
        mock_text_content = MagicMock()
        mock_text_content.text = "This is not JSON"
        mock_result = MagicMock()
        mock_result.data = None
        mock_result.content = [mock_text_content]

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert len(result) == 1
            assert result[0]["text"] == "This is not JSON"

    @pytest.mark.asyncio
    async def test_get_latest_news_handles_raw_list_result(self):
        """
        Given: Result is a raw list (no .data attribute, result itself is list).
        When: get_latest_news is called.
        Then: List is processed directly by _extract_news_items.
        """
        # Create a result that is actually a list (defensive fallback path)
        raw_list_result = [{"title": "Direct list item"}]

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=raw_list_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert len(result) == 1
            assert result[0]["title"] == "Direct list item"

    @pytest.mark.asyncio
    async def test_get_latest_news_raises_on_invalid_result_type(self):
        """
        Given: Result has no .data, is not list/dict, and has empty .content.
        When: get_latest_news is called.
        Then: TrendRadarError is raised for unexpected result type.
        """
        mock_result = MagicMock()
        mock_result.data = None
        mock_result.content = []  # Empty content list

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "unexpected result type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_latest_news_multiple_content_blocks_fallback(self):
        """
        Given: Response has multiple content blocks, first is not valid JSON, second is.
        When: get_latest_news is called.
        Then: First block is skipped (invalid JSON), second block is parsed and returned.
        Note: Validates two-step strategy - returns first valid JSON, ignoring prior failures.
        """
        mock_text_content1 = MagicMock()
        mock_text_content1.text = "This is not JSON"

        mock_text_content2 = MagicMock()
        mock_text_content2.text = '{"success": true, "news": [{"title": "Valid JSON"}]}'

        mock_result = MagicMock()
        mock_result.data = None
        mock_result.content = [mock_text_content1, mock_text_content2]

        with patch(
            "nook.services.explorers.trendradar.trendradar_client.Client"
        ) as MockClient:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.call_tool = AsyncMock(return_value=mock_result)
            MockClient.return_value = mock_client

            client = TrendRadarClient()
            result = await client.get_latest_news(platform="zhihu")

            assert len(result) == 1
            assert result[0]["title"] == "Valid JSON"
