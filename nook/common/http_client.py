import httpx
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from nook.common.exceptions import APIException, RetryException
from nook.common.decorators import handle_errors
from nook.common.config import BaseConfig


logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """非同期HTTPクライアント with connection pooling"""
    
    def __init__(self, config: BaseConfig = None):
        self.config = config or BaseConfig()
        self.timeout = httpx.Timeout(
            timeout=self.config.REQUEST_TIMEOUT,
            connect=5.0,
            read=self.config.REQUEST_TIMEOUT,
            write=5.0,
            pool=5.0
        )
        self.limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._session_start: Optional[datetime] = None
    
    async def __aenter__(self):
        """コンテキストマネージャーのエントリー"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのエグジット"""
        await self.close()
    
    async def start(self):
        """クライアントセッションを開始"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True,
                http2=True  # HTTP/2サポート
            )
            self._session_start = datetime.utcnow()
            logger.info("HTTP client session started")
    
    async def close(self):
        """クライアントセッションを終了"""
        if self._client:
            await self._client.aclose()
            self._client = None
            
            if self._session_start:
                duration = (datetime.utcnow() - self._session_start).total_seconds()
                logger.info(f"HTTP client session closed after {duration:.2f} seconds")
    
    @handle_errors(retries=3, delay=1.0, backoff=2.0)
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """GET リクエスト"""
        if not self._client:
            await self.start()
        
        logger.debug(f"GET {url}", extra={"params": params})
        
        try:
            response = await self._client.get(
                url,
                headers=headers,
                params=params,
                **kwargs
            )
            response.raise_for_status()
            
            logger.debug(
                f"GET {url} completed",
                extra={
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            )
            
            return response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise APIException(
                f"HTTP {e.response.status_code} error",
                status_code=e.response.status_code,
                response_body=e.response.text
            ) from e
        
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise APIException(f"Request failed: {str(e)}") from e
    
    @handle_errors(retries=3, delay=1.0, backoff=2.0)
    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """POST リクエスト"""
        if not self._client:
            await self.start()
        
        logger.debug(f"POST {url}")
        
        try:
            response = await self._client.post(
                url,
                json=json,
                data=data,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            
            logger.debug(
                f"POST {url} completed",
                extra={"status_code": response.status_code}
            )
            
            return response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise APIException(
                f"HTTP {e.response.status_code} error",
                status_code=e.response.status_code,
                response_body=e.response.text
            ) from e
        
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise APIException(f"Request failed: {str(e)}") from e
    
    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """JSONレスポンスを取得"""
        response = await self.get(url, **kwargs)
        return response.json()
    
    async def get_text(self, url: str, **kwargs) -> str:
        """テキストレスポンスを取得"""
        response = await self.get(url, **kwargs)
        return response.text
    
    async def download(
        self,
        url: str,
        output_path: str,
        chunk_size: int = 8192,
        progress_callback=None
    ):
        """ファイルをダウンロード"""
        if not self._client:
            await self.start()
        
        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        await progress_callback(downloaded, total_size)
            
            logger.info(f"Downloaded {url} to {output_path}")


# グローバルクライアントインスタンス（シングルトン）
_global_client: Optional[AsyncHTTPClient] = None


async def get_http_client() -> AsyncHTTPClient:
    """グローバルHTTPクライアントを取得"""
    global _global_client
    
    if _global_client is None:
        _global_client = AsyncHTTPClient()
        await _global_client.start()
    
    return _global_client


async def close_http_client():
    """グローバルHTTPクライアントを閉じる"""
    global _global_client
    
    if _global_client:
        await _global_client.close()
        _global_client = None