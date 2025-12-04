from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.async_utils import (
    AsyncTaskManager,
    TaskResult,
    batch_process,
    gather_with_errors,
    run_sync_in_thread,
    run_with_semaphore,
)


def _run(coro):
    return asyncio.run(coro)


def test_gather_with_errors_collects_success_and_failures():
    async def succeed():
        await asyncio.sleep(0.01)
        return 1

    async def fail():
        await asyncio.sleep(0.01)
        raise RuntimeError("boom")

    async def main():
        return await gather_with_errors(
            succeed(),
            fail(),
            task_names=["success", "failure"],
        )

    results = _run(main())

    assert isinstance(results[0], TaskResult)
    assert results[0].name == "success"
    assert results[0].success is True
    assert results[1].name == "failure"
    assert results[1].success is False
    assert isinstance(results[1].error, RuntimeError)


def test_gather_with_errors_validates_task_name_length():
    async def noop():
        return None

    async def main():
        coro = noop()
        with pytest.raises(
            ValueError, match="task_names must have the same length as coros"
        ):
            await gather_with_errors(coro, task_names=["first", "second"])
        coro.close()

    _run(main())


def test_gather_with_errors_allows_single_named_task():
    async def noop():
        return 42

    async def main():
        return await gather_with_errors(noop(), task_names=["only-one"])

    results = _run(main())
    assert len(results) == 1
    assert results[0].name == "only-one"
    assert results[0].success is True
    assert results[0].result == 42


def test_gather_with_errors_treats_empty_task_names_as_default():
    async def noop():
        return "ok"

    async def main():
        return await gather_with_errors(noop(), task_names=[])

    results = _run(main())
    assert len(results) == 1
    assert results[0].name == "Task-0"
    assert results[0].result == "ok"


def test_run_with_semaphore_limits_parallelism():
    max_running = 0
    current = 0

    async def tracked_task(value):
        nonlocal current, max_running
        current += 1
        max_running = max(max_running, current)
        await asyncio.sleep(0.01)
        current -= 1
        return value

    progress_updates: list[tuple[int, int]] = []

    async def progress(count, total):
        progress_updates.append((count, total))

    async def main():
        coros = [partial(tracked_task, idx) for idx in range(5)]
        return await run_with_semaphore(
            coros,
            max_concurrent=2,
            progress_callback=progress,
        )

    results = _run(main())

    assert sorted(results) == list(range(5))
    assert max_running <= 2
    assert progress_updates[-1] == (5, 5)


def test_batch_process_splits_into_batches():
    processed_batches: list[list[int]] = []

    async def processor(batch):
        processed_batches.append(list(batch))
        return sum(batch)

    async def main():
        return await batch_process(
            items=list(range(6)),
            processor=processor,
            batch_size=2,
            max_concurrent_batches=2,
        )

    results = _run(main())

    assert processed_batches == [[0, 1], [2, 3], [4, 5]]
    assert results == [1, 5, 9]


def test_run_sync_in_thread_executes_blocking_code():
    def blocking_add(a, b):
        return a + b

    async def main():
        return await run_sync_in_thread(blocking_add, 2, 3)

    result = _run(main())
    assert result == 5


def test_async_task_manager_handles_success_and_failure():
    manager = AsyncTaskManager(max_concurrent=2)

    async def ok_task():
        await asyncio.sleep(0.01)
        return "done"

    async def fail_task():
        await asyncio.sleep(0.01)
        raise ValueError("bad")

    async def main():
        await manager.submit("ok", ok_task())
        await manager.submit("fail", fail_task())

        assert await manager.wait_for("ok") == "done"

        with pytest.raises(ValueError, match="bad"):
            await manager.wait_for("fail")

        summary = await manager.wait_all()
        assert summary["results"]["ok"] == "done"
        assert isinstance(summary["errors"]["fail"], ValueError)

    _run(main())


def test_async_task_manager_rejects_duplicate_names():
    manager = AsyncTaskManager()

    async def sleeper():
        await asyncio.sleep(0.05)
        return 1

    async def main():
        await manager.submit("task", sleeper())

        duplicate_coro = sleeper()
        with pytest.raises(ValueError, match="Task task already exists"):
            await manager.submit("task", duplicate_coro)
        duplicate_coro.close()

        await manager.wait_all()

    _run(main())
