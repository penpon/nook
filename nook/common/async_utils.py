import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Any, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TaskResult:
    """タスク実行結果"""

    def __init__(self, name: str, success: bool, result: Any = None, error: Exception = None):
        self.name = name
        self.success = success
        self.result = result
        self.error = error
        self.timestamp = datetime.utcnow()


async def gather_with_errors(
    *coros, return_exceptions: bool = True, task_names: list[str] | None = None
) -> list[TaskResult]:
    """複数のコルーチンを並行実行し、エラーも含めて結果を返す"""
    if task_names and len(task_names) != len(coros):
        raise ValueError("task_names must have the same length as coros")

    if not task_names:
        task_names = [f"Task-{i}" for i in range(len(coros))]

    results = await asyncio.gather(*coros, return_exceptions=return_exceptions)

    task_results = []
    for name, result in zip(task_names, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Task {name} failed: {result}")
            task_results.append(TaskResult(name, False, error=result))
        else:
            task_results.append(TaskResult(name, True, result=result))

    return task_results


async def run_with_semaphore(
    coros: list[Callable[[], Any]],
    max_concurrent: int = 10,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[Any]:
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
    items: list[T],
    processor: Callable[[list[T]], Any],
    batch_size: int = 100,
    max_concurrent_batches: int = 5,
) -> list[Any]:
    """アイテムをバッチ処理"""
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    async def process_batch(batch):
        return await processor(batch)

    return await run_with_semaphore(
        [partial(process_batch, batch) for batch in batches],
        max_concurrent=max_concurrent_batches,
    )


def run_sync_in_thread(sync_func: Callable[..., T], *args, **kwargs) -> asyncio.Future[T]:
    """同期関数を別スレッドで実行"""
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    return loop.run_in_executor(executor, partial(sync_func, *args, **kwargs))


class AsyncTaskManager:
    """非同期タスクマネージャー"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.tasks: dict[str, asyncio.Task] = {}
        self.results: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}
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

    async def wait_for(self, name: str, timeout: float | None = None) -> Any:
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

    async def wait_all(self, timeout: float | None = None) -> dict[str, Any]:
        """すべてのタスクの完了を待つ"""
        if self.tasks:
            tasks = list(self.tasks.values())
            await asyncio.wait(tasks, timeout=timeout)

        return {"results": self.results.copy(), "errors": self.errors.copy()}

    def get_status(self) -> dict[str, Any]:
        """タスクの状態を取得"""
        return {
            "running": list(self.tasks.keys()),
            "completed": list(self.results.keys()),
            "failed": list(self.errors.keys()),
            "total": len(self.tasks) + len(self.results) + len(self.errors),
        }
