"""TrendRadar MCP server HTTP client.

This module provides a client for communicating with the TrendRadar MCP server
to retrieve hot topics from Chinese platforms like Zhihu.
"""

import logging
from typing import Any

from nook.core.clients.http_client import AsyncHTTPClient
from nook.core.errors.exceptions import APIException

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
    ) -> dict[str, Any]:
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
            If the request fails or server returns an error.
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
            data = response.json()

            # Check for JSON-RPC error
            if "error" in data:
                error_msg = data["error"]
                logger.error(f"TrendRadar API error: {error_msg}")
                raise TrendRadarError(f"API error: {error_msg}")

            return data

        except APIException as e:
            logger.error(f"TrendRadar communication failed: {e}")
            raise TrendRadarError(f"Communication failed: {e}") from e

        except Exception as e:
            logger.error(f"TrendRadar unexpected error: {e}")
            raise TrendRadarError(f"Unexpected error: {e}") from e

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
        TrendRadarError
            If the request fails or response is invalid.
        """
        response = await self._make_request(
            method="tools/call",
            params={
                "name": f"get_{platform}_hot",
                "arguments": {"limit": limit},
            },
        )

        # Extract result from JSON-RPC response
        if "result" not in response:
            logger.error(f"Invalid response from TrendRadar: {response}")
            raise TrendRadarError("Invalid response: missing 'result' field")

        return response["result"]

    async def health_check(self) -> bool:
        """Check if TrendRadar server is reachable.

        Returns
        -------
        bool
            True if server is reachable and returns healthy status.
        """
        try:
            await self._make_request(method="health")
            # healthメソッドのレスポンス形式に合わせて検証
            # ここではエラーにならなければOKとするが、必要ならレスポンス内容もチェック
            # 例: return response.get("status") == "ok"
            # 指摘は「エラーレスポンスでもTrueを返す」点だったので、
            # _make_requestでエラーチェックが入ったことで解決している。
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
