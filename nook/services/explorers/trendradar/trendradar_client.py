"""TrendRadar MCP server client using FastMCP.

This module provides a client for communicating with the TrendRadar MCP server
to retrieve hot topics from Chinese platforms like Zhihu.
"""

import json
import logging
from typing import Any

from fastmcp import Client

logger = logging.getLogger(__name__)


class TrendRadarError(Exception):
    """TrendRadar related errors.

    Raised when communication with the TrendRadar MCP server fails.
    """

    pass


class TrendRadarClient:
    """FastMCP client for TrendRadar MCP server.

    This client communicates with the TrendRadar MCP server to retrieve
    hot topics from various Chinese platforms.

    Parameters
    ----------
    base_url : str, optional
        Base URL of the TrendRadar MCP server.
        Defaults to "http://localhost:3333/mcp".

    Examples
    --------
    >>> client = TrendRadarClient()
    >>> news = await client.get_latest_news(platform="zhihu")
    >>> print(news)
    [{"title": "Hot Topic 1", "url": "...", "hot": 1000000}, ...]
    """

    DEFAULT_URL = "http://localhost:3333/mcp"
    SUPPORTED_PLATFORMS = ["zhihu", "weibo"]

    def __init__(self, base_url: str | None = None):
        """Initialize TrendRadarClient.

        Parameters
        ----------
        base_url : str, optional
            Base URL of the TrendRadar MCP server.
        """
        self.base_url = base_url or self.DEFAULT_URL
        self._client: Client | None = None

    def _get_client(self) -> Client:
        """Get or create FastMCP client instance.

        Returns
        -------
        Client
            FastMCP client instance.
        """
        if self._client is None:
            self._client = Client(self.base_url)
        return self._client

    def _extract_news_items(self, payload: Any) -> list[dict[str, Any]]:
        """Normalize TrendRadar tool payload into list of news dicts."""
        if payload is None:
            return []

        # TrendRadar commonly returns {"success": true, "news": [...]}
        if isinstance(payload, dict):
            if payload.get("success") is False:
                error_info = payload.get("error", {})
                error_msg = error_info.get("message", "Unknown error from TrendRadar")
                logger.error(f"TrendRadar error: {error_msg}")
                raise TrendRadarError(f"TrendRadar error: {error_msg}")

            news = payload.get("news")
            if isinstance(news, list):
                return news

            items = payload.get("items")
            if isinstance(items, list):
                return items

            # Unknown dict shape: return a single record if non-empty
            return [payload] if payload else []

        if isinstance(payload, list):
            return payload

        # Primitive/unknown payload types
        return [{"text": str(payload)}]

    async def get_latest_news(
        self,
        platform: str = "zhihu",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get latest news from specified platform.

        Parameters
        ----------
        platform : str, default="zhihu"
            Platform to get news from (e.g., "zhihu", "weibo").
        limit : int, default=50
            Maximum number of news items to return.

        Returns
        -------
        list[dict]
            List of news items.

        Raises
        ------
        ValueError
            If platform is not supported or limit is out of valid range.
        TrendRadarError
            If the request fails or response is invalid.
        """
        # Validate platform parameter
        if not platform or platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Invalid platform '{platform}'. "
                f"Supported platforms: {', '.join(self.SUPPORTED_PLATFORMS)}"
            )

        # Validate limit parameter
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError(
                f"Invalid limit {limit}. Must be an integer between 1 and 100."
            )

        client = self._get_client()
        # TrendRadar uses get_latest_news with platforms parameter
        tool_name = "get_latest_news"

        try:
            async with client:
                result = await client.call_tool(
                    tool_name, {"platforms": [platform], "limit": limit}
                )

            # FastMCP returns CallToolResult which may include structured data (.data)
            # and/or content blocks (.content).
            if result is None:
                logger.error(f"Empty response from TrendRadar for {tool_name}")
                raise TrendRadarError("Empty response from server")

            # Prefer structured data if provided by FastMCP
            result_data = getattr(result, "data", None)
            if result_data is not None:
                return self._extract_news_items(result_data)

            # Fallback: accept raw list/dict results (defensive)
            if isinstance(result, (list, dict)):
                return self._extract_news_items(result)

            # Parse content blocks (e.g., TextContent) if present
            if hasattr(result, "content") and result.content:
                # Extract text content and parse as JSON
                for content in result.content:
                    if hasattr(content, "text"):
                        try:
                            data = json.loads(content.text)

                            return self._extract_news_items(data)
                        except json.JSONDecodeError:
                            # If not JSON, return as-is wrapped in list
                            return [{"text": content.text}]

            logger.error(f"Invalid result type from TrendRadar: {type(result)}")
            raise TrendRadarError(
                f"Invalid response: unexpected result type {type(result).__name__}"
            )

        except TrendRadarError:
            raise
        except Exception as e:
            logger.error(f"TrendRadar error: {e}")
            raise TrendRadarError(f"Failed to get news: {e}") from e

    async def health_check(self) -> bool:
        """Check if TrendRadar server is reachable.

        Returns
        -------
        bool
            True if server is reachable and returns healthy status.
        """
        client = self._get_client()
        try:
            async with client:
                await client.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close client connection.

        Should be called when done using the client.
        """
        # FastMCP client is closed via context manager, nothing to do here
        self._client = None
