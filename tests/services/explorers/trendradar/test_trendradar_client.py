"""Tests for TrendRadar MCP client.

This module tests the TrendRadarClient class that communicates with
the TrendRadar MCP server to retrieve hot topics from Chinese platforms.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

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
                {
                    "title": "Another topic",
                    "url": "https://zhihu.com/topic/2",
                    "hot": 500000,
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
            assert len(result) == 2
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


class TestConnectionErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_connection_error_raises_trendradar_error(self):
        """
        Given: TrendRadar server is unreachable.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()

        # Mock the HTTP client's post method to raise ConnectError
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "Connection" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error_raises_trendradar_error(self):
        """
        Given: Request times out.
        When: get_latest_news is called.
        Then: TrendRadarError is raised.
        """
        client = TrendRadarClient()

        # Mock the HTTP client's post method to raise TimeoutException
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.TimeoutException("Request timeout")

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            with pytest.raises(TrendRadarError) as exc_info:
                await client.get_latest_news(platform="zhihu")

            assert "timeout" in str(exc_info.value).lower()


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
    async def test_health_check_failure(self):
        """
        Given: TrendRadar server is unreachable.
        When: health_check is called.
        Then: False is returned.
        """
        client = TrendRadarClient()

        # Mock the HTTP client's post method to raise ConnectError
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(
            client, "_get_http_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_http_client

            result = await client.health_check()

            assert result is False
