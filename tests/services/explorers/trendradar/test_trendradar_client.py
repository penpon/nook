"""Tests for TrendRadar MCP client.

This module tests the TrendRadarClient class that communicates with
the TrendRadar MCP server to retrieve hot topics from Chinese platforms.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.core.errors.exceptions import APIException
from nook.services.explorers.trendradar.trendradar_client import (
    TrendRadarClient,
    TrendRadarError,
)


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
            assert "zhihu" in str(call_args) or call_args[1].get("platform") == "zhihu"

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
    async def test_health_check_success(self):
        """
        Given: TrendRadar server is running.
        When: health_check is called.
        Then: True is returned.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"status": "ok"}

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_on_exception(self):
        """
        Given: TrendRadar server is unreachable (raises exception).
        When: health_check is called.
        Then: False is returned.
        """
        client = TrendRadarClient()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = TrendRadarError("Connection failed")

            result = await client.health_check()

            assert result is False
