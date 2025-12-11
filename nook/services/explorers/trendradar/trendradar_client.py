"""TrendRadar MCP server HTTP client.

This module provides a client for communicating with the TrendRadar MCP server
to retrieve hot topics from Chinese platforms like Zhihu.
"""

import logging

import httpx

from nook.core.clients.http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)


class TrendRadarError(Exception):
    """TrendRadar related errors.

    Raised when communication with the TrendRadar MCP server fails.
    """

    pass


class TrendRadarClient:
    """HTTP client for TrendRadar MCP server.

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

    def __init__(self, base_url: str | None = None):
        """Initialize TrendRadarClient.

        Parameters
        ----------
        base_url : str, optional
            Base URL of the TrendRadar MCP server.
        """
        self.base_url = base_url or self.DEFAULT_URL
        self._http_client: AsyncHTTPClient | None = None

    async def _get_http_client(self) -> AsyncHTTPClient:
        """Get or create HTTP client instance.

        Returns
        -------
        AsyncHTTPClient
            HTTP client instance.
        """
        if self._http_client is None:
            self._http_client = AsyncHTTPClient()
            await self._http_client.start()
        return self._http_client

    async def _make_request(
        self,
        method: str,
        params: dict | None = None,
    ) -> dict:
        """Make a JSON-RPC style request to TrendRadar MCP server.

        Parameters
        ----------
        method : str
            Method name to call.
        params : dict, optional
            Parameters for the method.

        Returns
        -------
        dict
            Response data from the server.

        Raises
        ------
        TrendRadarError
            If the request fails.
        """
        http_client = await self._get_http_client()

        request_body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }

        try:
            response = await http_client.post(
                self.base_url,
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
            return response.json()

        except httpx.ConnectError as e:
            logger.error(f"TrendRadar connection error: {e}")
            raise TrendRadarError(f"Connection failed: {e}") from e

        except httpx.TimeoutException as e:
            logger.error(f"TrendRadar timeout: {e}")
            raise TrendRadarError(f"Request timeout: {e}") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"TrendRadar HTTP error: {e}")
            raise TrendRadarError(f"HTTP error: {e}") from e

        except Exception as e:
            logger.error(f"TrendRadar request failed: {e}")
            raise TrendRadarError(f"Request failed: {e}") from e

    async def get_latest_news(
        self,
        platform: str = "zhihu",
        limit: int = 50,
    ) -> list[dict]:
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
            List of news items, each containing:
            - title: str - News title
            - url: str - URL to the news
            - hot: int - Hotness score

        Raises
        ------
        TrendRadarError
            If the request fails.

        Examples
        --------
        >>> client = TrendRadarClient()
        >>> news = await client.get_latest_news(platform="zhihu", limit=10)
        >>> for item in news:
        ...     print(f"{item['title']} - {item['hot']}")
        """
        response = await self._make_request(
            method="tools/call",
            params={
                "name": f"get_{platform}_hot",
                "arguments": {"limit": limit},
            },
        )

        # Extract result from JSON-RPC response
        if "result" in response:
            return response["result"]
        elif "error" in response:
            raise TrendRadarError(f"API error: {response['error']}")
        else:
            return []

    async def health_check(self) -> bool:
        """Check if TrendRadar server is reachable.

        Returns
        -------
        bool
            True if server is reachable, False otherwise.

        Examples
        --------
        >>> client = TrendRadarClient()
        >>> if await client.health_check():
        ...     print("Server is running")
        """
        try:
            await self._make_request(method="health")
            return True
        except TrendRadarError:
            return False

    async def close(self) -> None:
        """Close HTTP client connection.

        Should be called when done using the client.
        """
        if self._http_client:
            await self._http_client.close()
            self._http_client = None
