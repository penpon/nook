"""Tests for TrendRadar MCP client.

This module tests the TrendRadarClient class that communicates with
the TrendRadar MCP server to retrieve hot topics from Chinese platforms.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.core.errors.exceptions import APIException
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
        mock_response_data = {
            "result": [
                {
                    "title": "Sample hot topic",
                    "url": "https://zhihu.com/topic/1",
                    "hot": 1000000,
                },
            ]
        }

        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response_data

            result = await client.get_latest_news(platform="zhihu")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["title"] == "Sample hot topic"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_news_with_platform_filter(self):
        """
        Given: Specific platform specified.
        When: get_latest_news is called with platform parameter.
        Then: Request is made with correct platform parameter.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": []}

            await client.get_latest_news(platform="zhihu", limit=10)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            # Verify platform is passed in the request
            assert call_args.kwargs["params"]["name"] == "get_zhihu_hot"

    @pytest.mark.asyncio
    async def test_get_latest_news_with_limit(self):
        """
        Given: Limit parameter specified.
        When: get_latest_news is called with limit.
        Then: Request includes limit parameter.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": [{"title": "Topic 1"}]}

            result = await client.get_latest_news(platform="zhihu", limit=5)

            assert isinstance(result, list)
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            # Verify limit is passed in the request params
            assert call_args.kwargs["params"]["arguments"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_latest_news_raises_error_on_missing_result(self):
        """
        Given: Response missing 'result' field.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            # Result field is missing
            mock_request.return_value = {"other": "data"}

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "Invalid response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_latest_news_raises_error_on_api_error(self):
        """
        Given: _make_request raises TrendRadarError.
        When: get_latest_news is called.
        Then: TrendRadarError is propagated.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = TrendRadarError("API error")

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "API error" in str(exc_info.value)


class TestMakeRequest:
    """Tests for _make_request method."""

    @pytest.mark.asyncio
    async def test_make_request_raises_error_on_json_rpc_error(self):
        """
        Given: Server returns JSON-RPC error.
        When: _make_request is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"code": -32600, "message": "Invalid Request"}
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client._make_request(method="test")

            assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_raises_error_on_invalid_json(self):
        """
        Given: Server returns invalid JSON.
        When: _make_request is called.
        Then: TrendRadarError is raised with appropriate message.
        """
        client = TrendRadarClient()
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        # Simulate JSON decode error
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_http_client.post.return_value = mock_response

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client._make_request(method="test")

            assert "Invalid JSON response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_raises_error_on_json_decode_error(self):
        """
        Given: Server returns malformed JSON string.
        When: _make_request is called.
        Then: TrendRadarError is raised with appropriate message.
        """
        client = TrendRadarClient()
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        # Simulate JSON decode error directly from json module
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_http_client.post.return_value = mock_response

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client._make_request(method="test")

            assert "Invalid JSON response" in str(exc_info.value)


class TestConnectionErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_api_exception_raises_trendradar_error(self):
        """
        Given: HTTP client raises APIException.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()

        # Mock the HTTP client's post method to raise APIException
        mock_http_client = AsyncMock()
        # APIException takes message, status_code (optional), response_body (optional)
        mock_http_client.post.side_effect = APIException("Connection failed")

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "Communication failed" in str(exc_info.value)


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """
        Given: TrendRadar server is running.
        When: health_check is called.
        Then: True is returned.
        """
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"status": "ok"}

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_failure_on_exception(self, client):
        """
        Given: TrendRadar server is unreachable (raises exception).
        When: health_check is called.
        Then: False is returned.
        """
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = TrendRadarError("Connection failed")

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_failure_on_json_error(self, client):
        """
        Given: TrendRadar server returns invalid JSON (raises JSONDecodeError wrapped in TrendRadarError).
        When: health_check is called.
        Then: False is returned.
        """
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            # _make_request wraps JSON errors in TrendRadarError
            mock_request.side_effect = TrendRadarError("Invalid JSON response")

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


class TestResultTypeValidation:
    """Tests for result field type validation."""

    @pytest.mark.asyncio
    async def test_non_list_result_raises_error(self):
        """
        Given: Response with non-list result field.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()

        # Test dict result
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": {"data": "not a list"}}

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "must be a list" in str(exc_info.value)

        # Test string result
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": "not a list"}

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "must be a list" in str(exc_info.value)

        # Test null result
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": None}

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "must be a list" in str(exc_info.value)


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_sets_http_client_to_none(self):
        """
        Given: Client with active HTTP client.
        When: close is called.
        Then: _http_client is set to None.
        """
        client = TrendRadarClient()

        # Initialize HTTP client
        mock_http_client = AsyncMock()
        client._http_client = mock_http_client

        await client.close()

        assert client._http_client is None
        mock_http_client.close.assert_called_once()

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
        assert client._http_client is None

        # Second close should not raise error
        await client.close()
        assert client._http_client is None
