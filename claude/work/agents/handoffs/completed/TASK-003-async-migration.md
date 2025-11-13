# TASK-003: 非同期処理への移行

## 割り当て: backend

## 目的
現在の同期的な処理を非同期処理に移行し、並行処理を活用してパフォーマンスを向上させる。

## 背景
現在のコードベースの問題点：
- `requests`ライブラリを使用した同期的なHTTP通信
- 複数のAPIを順次呼び出している
- I/O待機時間が無駄になっている
- `run_services.py`が各サービスを順番に実行

## 実装内容

### 1. 非同期HTTPクライアント
**ファイル**: `nook/common/http_client.py`

```python
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
```

### 2. レート制限付きHTTPクライアント
**ファイル**: `nook/common/rate_limiter.py`

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from collections import defaultdict
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)


class RateLimiter:
    """APIレート制限管理"""
    
    def __init__(
        self,
        rate: int,
        per: timedelta = timedelta(seconds=1),
        burst: Optional[int] = None
    ):
        self.rate = rate
        self.per = per
        self.burst = burst or rate
        self.allowance = float(self.burst)
        self.last_check = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1):
        """レート制限をチェックして必要に応じて待機"""
        async with self._lock:
            now = datetime.utcnow()
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
                    extra={"tokens_needed": tokens, "allowance": self.allowance}
                )
                
                await asyncio.sleep(wait_time)
                
                # 待機後に再度計算
                now = datetime.utcnow()
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
        default_rate_limit: Optional[RateLimiter] = None
    ):
        super().__init__(config)
        self.default_rate_limit = default_rate_limit or RateLimiter(
            rate=60,
            per=timedelta(minutes=1)
        )
        self.domain_rate_limits: Dict[str, RateLimiter] = {}
    
    def add_domain_rate_limit(
        self,
        domain: str,
        rate: int,
        per: timedelta = timedelta(seconds=1),
        burst: Optional[int] = None
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
```

### 3. 並行処理ユーティリティ
**ファイル**: `nook/common/async_utils.py`

```python
import asyncio
from typing import List, Callable, Any, TypeVar, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime
from functools import partial


logger = logging.getLogger(__name__)
T = TypeVar('T')


class TaskResult:
    """タスク実行結果"""
    
    def __init__(self, name: str, success: bool, result: Any = None, error: Exception = None):
        self.name = name
        self.success = success
        self.result = result
        self.error = error
        self.timestamp = datetime.utcnow()


async def gather_with_errors(
    *coros,
    return_exceptions: bool = True,
    task_names: Optional[List[str]] = None
) -> List[TaskResult]:
    """複数のコルーチンを並行実行し、エラーも含めて結果を返す"""
    if task_names and len(task_names) != len(coros):
        raise ValueError("task_names must have the same length as coros")
    
    if not task_names:
        task_names = [f"Task-{i}" for i in range(len(coros))]
    
    results = await asyncio.gather(*coros, return_exceptions=return_exceptions)
    
    task_results = []
    for i, (name, result) in enumerate(zip(task_names, results)):
        if isinstance(result, Exception):
            logger.error(f"Task {name} failed: {result}")
            task_results.append(TaskResult(name, False, error=result))
        else:
            task_results.append(TaskResult(name, True, result=result))
    
    return task_results


async def run_with_semaphore(
    coros: List[Callable[[], Any]],
    max_concurrent: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Any]:
    """セマフォを使って並行実行数を制限"""
    semaphore = asyncio.Semaphore(max_concurrent)
    total = len(coros)
    completed = 0
    
    async def run_with_limit(coro_func):
        async with semaphore:
            result = await coro_func()
            
            nonlocal completed
            completed += 1
            
            if progress_callback:
                await progress_callback(completed, total)
            
            return result
    
    tasks = [run_with_limit(coro) for coro in coros]
    return await asyncio.gather(*tasks)


async def batch_process(
    items: List[T],
    processor: Callable[[List[T]], Any],
    batch_size: int = 100,
    max_concurrent_batches: int = 5
) -> List[Any]:
    """アイテムをバッチ処理"""
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    async def process_batch(batch):
        return await processor(batch)
    
    return await run_with_semaphore(
        [partial(process_batch, batch) for batch in batches],
        max_concurrent=max_concurrent_batches
    )


def run_sync_in_thread(
    sync_func: Callable[..., T],
    *args,
    **kwargs
) -> asyncio.Future[T]:
    """同期関数を別スレッドで実行"""
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    
    return loop.run_in_executor(
        executor,
        partial(sync_func, *args, **kwargs)
    )


class AsyncTaskManager:
    """非同期タスクマネージャー"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}
        self._lock = asyncio.Lock()
    
    async def submit(self, name: str, coro) -> str:
        """タスクを送信"""
        async with self._lock:
            if name in self.tasks:
                raise ValueError(f"Task {name} already exists")
            
            task = asyncio.create_task(self._run_task(name, coro))
            self.tasks[name] = task
            
            return name
    
    async def _run_task(self, name: str, coro):
        """タスクを実行"""
        try:
            result = await coro
            async with self._lock:
                self.results[name] = result
                logger.info(f"Task {name} completed successfully")
        except Exception as e:
            async with self._lock:
                self.errors[name] = e
                logger.error(f"Task {name} failed: {e}")
        finally:
            async with self._lock:
                if name in self.tasks:
                    del self.tasks[name]
    
    async def wait_for(self, name: str, timeout: Optional[float] = None) -> Any:
        """特定のタスクの完了を待つ"""
        task = self.tasks.get(name)
        if not task:
            if name in self.results:
                return self.results[name]
            elif name in self.errors:
                raise self.errors[name]
            else:
                raise ValueError(f"Task {name} not found")
        
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Task {name} timed out")
            raise
        
        if name in self.errors:
            raise self.errors[name]
        
        return self.results.get(name)
    
    async def wait_all(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """すべてのタスクの完了を待つ"""
        if self.tasks:
            tasks = list(self.tasks.values())
            await asyncio.wait(tasks, timeout=timeout)
        
        return {
            "results": self.results.copy(),
            "errors": self.errors.copy()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """タスクの状態を取得"""
        return {
            "running": list(self.tasks.keys()),
            "completed": list(self.results.keys()),
            "failed": list(self.errors.keys()),
            "total": len(self.tasks) + len(self.results) + len(self.errors)
        }
```

### 4. サービスの非同期化（例: GitHubサービス）
**ファイル**: `nook/services/github_trending.py` (リファクタリング後)

```python
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import toml

from nook.common.base_service import BaseService
from nook.common.http_client import get_http_client
from nook.common.async_utils import gather_with_errors, run_with_semaphore
from nook.common.decorators import handle_errors, log_execution_time
from nook.common.service_errors import ServiceErrorHandler


class GitHubTrendingService(BaseService):
    """GitHub Trending リポジトリの収集サービス"""
    
    def __init__(self):
        super().__init__("github_trending")
        self.error_handler = ServiceErrorHandler(self.service_name)
        self.languages = self._load_languages()
    
    def _load_languages(self) -> List[str]:
        """言語設定を読み込み"""
        try:
            with open("nook/services/github_trending/languages.toml", "r") as f:
                config = toml.load(f)
                return config.get("languages", [])
        except Exception as e:
            self.logger.error(f"Failed to load languages: {e}")
            return ["python", "javascript", "go"]  # デフォルト値
    
    @log_execution_time
    async def collect(self) -> None:
        """メインの収集処理"""
        self.logger.info("Starting GitHub trending collection")
        
        async with await get_http_client() as client:
            # 各言語のトレンドを並行取得
            language_tasks = [
                self._collect_language_trending(client, language)
                for language in self.languages
            ]
            
            results = await gather_with_errors(
                *language_tasks,
                task_names=self.languages
            )
            
            # 結果をマージ
            all_repos = []
            for result in results:
                if result.success and result.result:
                    all_repos.extend(result.result)
            
            if all_repos:
                # リポジトリ情報を並行取得
                enriched_repos = await self._enrich_repositories(client, all_repos)
                
                # Markdownレポートを生成
                report = await self._generate_report(enriched_repos)
                
                # 保存
                filename = f"github_trending_{datetime.now().strftime('%Y-%m-%d')}.md"
                await self.save_markdown(report, filename)
                
                self.logger.info(f"Collected {len(enriched_repos)} repositories")
            else:
                self.logger.warning("No repositories collected")
    
    @handle_errors(retries=3)
    @ServiceErrorHandler.handle_api_error("GitHub")
    async def _collect_language_trending(
        self,
        client,
        language: str
    ) -> List[Dict[str, Any]]:
        """特定言語のトレンドリポジトリを取得"""
        url = f"https://api.github.com/search/repositories"
        params = {
            "q": f"language:{language} stars:>100",
            "sort": "stars",
            "order": "desc",
            "per_page": 10
        }
        
        response = await client.get(url, params=params)
        data = response.json()
        
        return data.get("items", [])
    
    async def _enrich_repositories(
        self,
        client,
        repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """リポジトリの詳細情報を取得"""
        async def get_repo_details(repo):
            try:
                # READMEを取得
                readme_url = f"{repo['url']}/readme"
                readme_response = await client.get(
                    readme_url,
                    headers={"Accept": "application/vnd.github.v3.raw"}
                )
                
                # GPTで要約
                if readme_response.status_code == 200:
                    summary = await self._summarize_readme(readme_response.text)
                    repo["summary"] = summary
                else:
                    repo["summary"] = repo.get("description", "No description")
                
                return repo
            except Exception as e:
                self.logger.warning(f"Failed to enrich repo {repo['name']}: {e}")
                repo["summary"] = repo.get("description", "No description")
                return repo
        
        # セマフォで並行数を制限（GitHub API レート制限対策）
        enriched = await run_with_semaphore(
            [lambda r=repo: get_repo_details(r) for repo in repos],
            max_concurrent=5
        )
        
        return enriched
    
    async def _summarize_readme(self, readme_text: str) -> str:
        """READMEを要約（非同期）"""
        # 長すぎる場合は切り詰め
        if len(readme_text) > 5000:
            readme_text = readme_text[:5000] + "..."
        
        prompt = f"""
        以下のREADMEを日本語で簡潔に要約してください（100文字以内）:
        
        {readme_text}
        """
        
        # GPTクライアントの非同期対応（仮実装）
        # 実際の実装では、GPTクライアントも非同期化する必要がある
        summary = await asyncio.get_event_loop().run_in_executor(
            None,
            self.gpt_client.generate,
            prompt
        )
        
        return summary
    
    async def _generate_report(self, repos: List[Dict[str, Any]]) -> str:
        """レポートを生成"""
        lines = [
            f"# GitHub Trending - {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "本日のトレンドリポジトリ",
            ""
        ]
        
        # 言語別にグループ化
        by_language = {}
        for repo in repos:
            lang = repo.get("language", "Unknown")
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(repo)
        
        for language, lang_repos in sorted(by_language.items()):
            lines.append(f"## {language}")
            lines.append("")
            
            for repo in sorted(lang_repos, key=lambda x: x.get("stargazers_count", 0), reverse=True):
                lines.extend([
                    f"### [{repo['name']}]({repo['html_url']})",
                    f"⭐ {repo.get('stargazers_count', 0):,} stars | "
                    f"🍴 {repo.get('forks_count', 0):,} forks",
                    "",
                    repo.get("summary", "No description"),
                    ""
                ])
        
        return "\n".join(lines)
```

### 5. サービス実行スクリプトの非同期化
**ファイル**: `nook/services/run_services.py` (リファクタリング後)

```python
import asyncio
import logging
from typing import List, Optional
from datetime import datetime
import signal
import sys

from nook.services.github_trending import GitHubTrendingService
from nook.services.hacker_news import HackerNewsService
from nook.services.reddit_explorer import RedditExplorerService
from nook.services.tech_feed import TechFeedService
from nook.services.business_feed import BusinessFeedService

from nook.common.async_utils import AsyncTaskManager, gather_with_errors
from nook.common.logging import setup_logger
from nook.common.http_client import close_http_client


logger = setup_logger("service_runner")


class ServiceRunner:
    """サービス実行マネージャー"""
    
    def __init__(self):
        self.services = [
            GitHubTrendingService(),
            HackerNewsService(),
            RedditExplorerService(),
            TechFeedService(),
            BusinessFeedService(),
        ]
        self.task_manager = AsyncTaskManager(max_concurrent=5)
        self.running = False
    
    async def run_all(self) -> None:
        """すべてのサービスを並行実行"""
        self.running = True
        start_time = datetime.now()
        
        logger.info(f"Starting {len(self.services)} services")
        
        try:
            # 各サービスのcollectメソッドを並行実行
            service_tasks = [
                service.collect() for service in self.services
            ]
            
            results = await gather_with_errors(
                *service_tasks,
                task_names=[s.service_name for s in self.services]
            )
            
            # 結果をレポート
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Service run completed in {duration:.2f} seconds",
                extra={
                    "successful": successful,
                    "failed": failed,
                    "total": len(self.services)
                }
            )
            
            # エラーの詳細をログ
            for result in results:
                if not result.success:
                    logger.error(
                        f"Service {result.name} failed",
                        extra={"error": str(result.error)}
                    )
            
        except Exception as e:
            logger.error(f"Service runner failed: {e}", exc_info=True)
            raise
        finally:
            self.running = False
            # HTTPクライアントをクリーンアップ
            await close_http_client()
    
    async def run_service(self, service_name: str) -> None:
        """特定のサービスを実行"""
        service = next(
            (s for s in self.services if s.service_name == service_name),
            None
        )
        
        if not service:
            raise ValueError(f"Service {service_name} not found")
        
        logger.info(f"Running service: {service_name}")
        
        try:
            await service.collect()
            logger.info(f"Service {service_name} completed successfully")
        except Exception as e:
            logger.error(f"Service {service_name} failed: {e}", exc_info=True)
            raise
    
    async def run_continuous(self, interval_seconds: int = 3600) -> None:
        """定期的にサービスを実行"""
        logger.info(f"Starting continuous run with interval: {interval_seconds}s")
        
        while self.running:
            try:
                await self.run_all()
            except Exception as e:
                logger.error(f"Run failed: {e}", exc_info=True)
            
            # 次の実行まで待機
            logger.info(f"Waiting {interval_seconds} seconds until next run")
            await asyncio.sleep(interval_seconds)
    
    def stop(self):
        """実行を停止"""
        logger.info("Stopping service runner")
        self.running = False


async def main():
    """メイン実行関数"""
    runner = ServiceRunner()
    
    # シグナルハンドラーの設定
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        runner.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # コマンドライン引数の処理（簡易版）
    if len(sys.argv) > 1:
        if sys.argv[1] == "--continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
            await runner.run_continuous(interval)
        else:
            # 特定のサービスを実行
            await runner.run_service(sys.argv[1])
    else:
        # すべてのサービスを一度実行
        await runner.run_all()


if __name__ == "__main__":
    asyncio.run(main())
```

## テスト要件

### ユニットテスト
**ファイル**: `tests/common/test_async_http.py`

```python
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from nook.common.http_client import AsyncHTTPClient, get_http_client
from nook.common.exceptions import APIException


@pytest.mark.asyncio
class TestAsyncHTTPClient:
    async def test_get_success(self):
        """GETリクエストの成功テスト"""
        async with AsyncHTTPClient() as client:
            with patch.object(client._client, 'get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"success": True}
                mock_response.raise_for_status = AsyncMock()
                mock_get.return_value = mock_response
                
                result = await client.get_json("https://example.com")
                
                assert result == {"success": True}
                mock_get.assert_called_once()
    
    async def test_get_retry_on_error(self):
        """エラー時のリトライテスト"""
        async with AsyncHTTPClient() as client:
            with patch.object(client._client, 'get') as mock_get:
                # 2回失敗して3回目で成功
                mock_get.side_effect = [
                    httpx.RequestError("Connection failed"),
                    httpx.RequestError("Connection failed"),
                    AsyncMock(
                        status_code=200,
                        json=AsyncMock(return_value={"success": True}),
                        raise_for_status=AsyncMock()
                    )
                ]
                
                result = await client.get_json("https://example.com")
                
                assert result == {"success": True}
                assert mock_get.call_count == 3
    
    async def test_rate_limiter(self):
        """レート制限のテスト"""
        from nook.common.rate_limiter import RateLimitedHTTPClient, RateLimiter
        from datetime import timedelta
        
        # 1秒に1リクエストの制限
        rate_limiter = RateLimiter(rate=1, per=timedelta(seconds=1))
        
        async with RateLimitedHTTPClient(default_rate_limit=rate_limiter) as client:
            with patch.object(client._client, 'get') as mock_get:
                mock_response = AsyncMock(
                    status_code=200,
                    raise_for_status=AsyncMock()
                )
                mock_get.return_value = mock_response
                
                import time
                start = time.time()
                
                # 2つのリクエストを送信
                await client.get("https://example.com")
                await client.get("https://example.com")
                
                elapsed = time.time() - start
                
                # 2番目のリクエストは約1秒待機するはず
                assert elapsed >= 0.9  # 多少の誤差を許容
```

### 統合テスト
**ファイル**: `tests/integration/test_async_services.py`

```python
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from nook.services.run_services import ServiceRunner


@pytest.mark.asyncio
class TestServiceRunner:
    async def test_run_all_services(self):
        """全サービス並行実行のテスト"""
        runner = ServiceRunner()
        
        # 各サービスのcollectメソッドをモック
        for service in runner.services:
            service.collect = AsyncMock()
        
        await runner.run_all()
        
        # すべてのサービスが呼ばれたことを確認
        for service in runner.services:
            service.collect.assert_called_once()
    
    async def test_concurrent_execution(self):
        """並行実行の確認"""
        runner = ServiceRunner()
        
        call_times = []
        
        async def mock_collect(service_name):
            call_times.append((service_name, asyncio.get_event_loop().time()))
            await asyncio.sleep(0.1)  # 100ms の処理をシミュレート
        
        # 各サービスのcollectメソッドをモック
        for service in runner.services:
            service.collect = lambda s=service.service_name: mock_collect(s)
        
        start_time = asyncio.get_event_loop().time()
        await runner.run_all()
        end_time = asyncio.get_event_loop().time()
        
        # 並行実行なので、全体の実行時間は個々の合計より短いはず
        total_time = end_time - start_time
        assert total_time < 0.5  # 5サービス×0.1秒 = 0.5秒より短い
        
        # すべてのサービスがほぼ同時に開始されたことを確認
        start_times = [t[1] for t in call_times]
        assert max(start_times) - min(start_times) < 0.05
```

## 完了条件

1. 非同期HTTPクライアントが実装されていること
2. レート制限機能が動作すること
3. 既存のサービスが非同期処理に移行されていること
4. サービスが並行実行されること
5. テストが成功すること
6. パフォーマンスが向上すること（実行時間30%以上短縮）

## 注意事項

1. 既存の同期処理との互換性を保つ
2. エラーハンドリングを適切に行う
3. リソースのクリーンアップを忘れない
4. デッドロックを避ける
5. メモリリークに注意

## 依存関係

- TASK-001の完了（基底クラス）
- TASK-002の完了（エラーハンドリング）
- httpx >= 0.24.0
- asyncio (Python標準ライブラリ)

## 期限

3日間