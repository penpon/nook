import httpx
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import cloudscraper

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
        self._http1_client: Optional[httpx.AsyncClient] = None
        self._session_start: Optional[datetime] = None
    
    @staticmethod
    def get_browser_headers() -> Dict[str, str]:
        """最新のブラウザヘッダーを返す"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
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
    
    async def _start_http1_client(self):
        """HTTP/1.1専用クライアントセッションを開始"""
        if self._http1_client is None:
            self._http1_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True,
                http2=False  # HTTP/1.1専用
            )
            logger.info("HTTP/1.1 client session started")
    
    async def close(self):
        """クライアントセッションを終了"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self._http1_client:
            await self._http1_client.aclose()
            self._http1_client = None
            
        if self._session_start:
            duration = (datetime.utcnow() - self._session_start).total_seconds()
            logger.info(f"HTTP client session closed after {duration:.2f} seconds")
    
    @handle_errors(retries=3, delay=1.0, backoff=2.0)
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        force_http1: bool = False,
        use_browser_headers: bool = True,
        **kwargs
    ) -> httpx.Response:
        """GET リクエスト（HTTP/1.1フォールバック対応）"""
        # ブラウザヘッダーを使用
        if use_browser_headers and headers is None:
            headers = self.get_browser_headers()
        elif use_browser_headers and headers:
            # ユーザー指定のヘッダーとマージ
            browser_headers = self.get_browser_headers()
            browser_headers.update(headers)
            headers = browser_headers
            
        if force_http1:
            # HTTP/1.1を強制使用
            if not self._http1_client:
                await self._start_http1_client()
            client = self._http1_client
            logger.debug(f"GET {url} (forced HTTP/1.1)", extra={"params": params})
        else:
            # 通常のHTTP/2クライアントを使用
            if not self._client:
                await self.start()
            client = self._client
            logger.debug(f"GET {url}", extra={"params": params})
        
        try:
            response = await client.get(
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
                    "response_time": response.elapsed.total_seconds(),
                    "http_version": "HTTP/1.1" if force_http1 else "HTTP/2"
                }
            )
            
            return response
            
        except httpx.StreamError as e:
            # StreamResetエラーの場合、HTTP/1.1でリトライ
            if not force_http1 and ("stream" in str(e).lower() or "reset" in str(e).lower()):
                logger.info(f"StreamReset error for {url}, falling back to HTTP/1.1: {e}")
                return await self.get(url, headers=headers, params=params, force_http1=True, **kwargs)
            else:
                logger.error(f"Stream error for {url}: {e}")
                raise APIException(f"Stream error: {str(e)}") from e
            
        except httpx.HTTPStatusError as e:
            # 403エラーの場合、cloudscraper��リトライ
            if e.response.status_code == 403:
                logger.info(f"403 error for {url}, trying cloudscraper")
                return await self._cloudscraper_fallback(url, params, **kwargs)
            else:
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
    
    async def _cloudscraper_fallback(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """cloudscraperを使用したフォールバック処理"""
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            # 同期処理を非同期で実行
            response = await asyncio.to_thread(
                scraper.get,
                url,
                params=params,
                timeout=self.timeout.read
            )
            
            # httpx互換のレスポンスに変換
            return self._convert_to_httpx_response(response)
            
        except Exception as e:
            logger.error(f"Cloudscraper failed for {url}: {e}")
            # 元の403エラーを再発生
            raise APIException(
                f"HTTP 403 error (cloudscraper also failed)",
                status_code=403
            ) from e
    
    def _convert_to_httpx_response(self, response):
        """requests.Responseをhttpx互換のレスポンスアダプターに変換"""
        class CloudscraperResponseAdapter:
            def __init__(self, cloudscraper_response):
                self._response = cloudscraper_response
                self.status_code = cloudscraper_response.status_code
                self.text = cloudscraper_response.text
                self.content = cloudscraper_response.content
                self.headers = cloudscraper_response.headers
            
            def json(self):
                return self._response.json()
            
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"HTTP {self.status_code} error",
                        request=None,
                        response=self
                    )
        
        return CloudscraperResponseAdapter(response)
    
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