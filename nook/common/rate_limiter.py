import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from nook.common.config import BaseConfig
from nook.common.http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)


class RateLimiter:
    """APIレート制限管理"""

    def __init__(
        self,
        rate: int,
        per: timedelta = timedelta(seconds=1),
        burst: int | None = None,
    ):
        self.rate = rate
        self.per = per
        self.burst = burst or rate
        self.allowance = float(self.burst)
        self.last_check = datetime.now(UTC)
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        """レート制限をチェックして必要に応じて待機"""
        async with self._lock:
            now = datetime.now(UTC)
            elapsed = (now - self.last_check).total_seconds()
            self.last_check = now

            # トークンを回復
            self.allowance += elapsed * (self.rate / self.per.total_seconds())
            if self.allowance > self.burst:
                self.allowance = float(self.burst)

            if self.allowance < tokens:
                # 必要なトークンが回復するまでの時間を計算
                deficit = tokens - self.allowance
                wait_time = deficit * (self.per.total_seconds() / self.rate)

                logger.debug(
                    f"Rate limit reached, waiting {wait_time:.2f} seconds",
                    extra={"tokens_needed": tokens, "allowance": self.allowance},
                )

                await asyncio.sleep(wait_time)

                # 待機後に再度計算
                now = datetime.now(UTC)
                elapsed = (now - self.last_check).total_seconds()
                self.last_check = now
                self.allowance += elapsed * (self.rate / self.per.total_seconds())
                if self.allowance > self.burst:
                    self.allowance = float(self.burst)

            self.allowance -= tokens


class RateLimitedHTTPClient(AsyncHTTPClient):
    """レート制限機能付きHTTPクライアント"""

    def __init__(
        self,
        config: BaseConfig = None,
        default_rate_limit: RateLimiter | None = None,
    ):
        super().__init__(config)
        self.default_rate_limit = default_rate_limit or RateLimiter(
            rate=60, per=timedelta(minutes=1)
        )
        self.domain_rate_limits: dict[str, RateLimiter] = {}

    def add_domain_rate_limit(
        self,
        domain: str,
        rate: int,
        per: timedelta = timedelta(seconds=1),
        burst: int | None = None,
    ):
        """特定ドメインのレート制限を設定"""
        self.domain_rate_limits[domain] = RateLimiter(rate, per, burst)

    def _get_domain(self, url: str) -> str:
        """URLからドメインを抽出"""
        from urllib.parse import urlparse

        return urlparse(url).netloc

    async def _acquire_rate_limit(self, url: str, tokens: int = 1):
        """URLに対応するレート制限を取得して待機"""
        domain = self._get_domain(url)

        if domain in self.domain_rate_limits:
            rate_limiter = self.domain_rate_limits[domain]
        else:
            rate_limiter = self.default_rate_limit

        await rate_limiter.acquire(tokens)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """レート制限付きGETリクエスト"""
        await self._acquire_rate_limit(url)
        return await super().get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """レート制限付きPOSTリクエスト"""
        await self._acquire_rate_limit(url)
        return await super().post(url, **kwargs)
