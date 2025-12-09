import asyncio
from functools import partial

import pytest

from nook.common.async_utils import (
    AsyncTaskManager,
    batch_process,
    gather_with_errors,
    run_sync_in_thread,
    run_with_semaphore,
)


@pytest.mark.asyncio
async def test_gather_with_errors():
    async def ok():
        return 1

    async def fail():
        raise ValueError("err")

    results = await gather_with_errors(ok(), fail(), task_names=["ok", "fail"])

    assert len(results) == 2
    assert results[0].success
    assert results[0].result == 1
    assert not results[1].success
    assert isinstance(results[1].error, ValueError)


@pytest.mark.asyncio
async def test_gather_with_errors_mismatch_names():
    with pytest.raises(ValueError, match="same length"):
        await gather_with_errors(
            partial(asyncio.sleep, 0)(), partial(asyncio.sleep, 0)(), task_names=["one"]
        )


@pytest.mark.asyncio
async def test_gather_with_errors_default_names():
    results = await gather_with_errors(partial(asyncio.sleep, 0)(), task_names=None)
    assert results[0].name == "Task-0"


@pytest.mark.asyncio
async def test_run_with_semaphore():
    running = 0
    max_running = 0

    async def task():
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.01)
        running -= 1
        return "ok"

    coros = [task for _ in range(5)]
    results = await run_with_semaphore(coros, max_concurrent=2)

    assert len(results) == 5
    assert max_running <= 2
    assert all(r == "ok" for r in results)


@pytest.mark.asyncio
async def test_run_with_semaphore_exception():
    async def ok():
        return 1

    async def fail():
        raise ValueError("boom")

    # default gather raises on first error
    with pytest.raises(ValueError, match="boom"):
        await run_with_semaphore([ok, fail], max_concurrent=2)


@pytest.mark.asyncio
async def test_batch_process():
    async def processor(batch):
        return [x * 2 for x in batch]

    items = [1, 2, 3, 4, 5]
    results = await batch_process(items, processor, batch_size=2)

    assert results == [[2, 4], [6, 8], [10]]


@pytest.mark.asyncio
async def test_run_sync_in_thread():
    def sync_func(a, b):
        return a + b

    res = await run_sync_in_thread(sync_func, 1, 2)
    assert res == 3


@pytest.mark.asyncio
async def test_run_sync_in_thread_error():
    def sync_fail():
        raise ValueError("sync error")

    with pytest.raises(ValueError, match="sync error"):
        await run_sync_in_thread(sync_fail)


# --- AsyncTaskManager Tests ---


@pytest.mark.asyncio
async def test_manager_submit_run_wait():
    manager = AsyncTaskManager()
    await manager.submit("t1", partial(asyncio.sleep, 0.01, result="done")())

    res = await manager.wait_for("t1")
    assert res == "done"

    # Verify cleanup
    status = manager.get_status()
    assert "t1" in status["completed"]
    assert "t1" not in status["running"]


@pytest.mark.asyncio
async def test_manager_duplicate_submit():
    manager = AsyncTaskManager()
    # Submit a long-running task
    await manager.submit("t1", asyncio.sleep(10))

    # Attempt to submit duplicate while first task is still running
    with pytest.raises(ValueError, match="already exists"):
        await manager.submit("t1", asyncio.sleep(0))

    # Cleanup: cancel the long-running task
    if "t1" in manager.tasks:
        manager.tasks["t1"].cancel()
        try:
            await manager.tasks["t1"]
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_manager_wait_unknown():
    manager = AsyncTaskManager()
    with pytest.raises(ValueError, match="not found"):
        await manager.wait_for("unknown")


@pytest.mark.asyncio
async def test_manager_wait_timeout():
    manager = AsyncTaskManager()
    await manager.submit("slow", asyncio.sleep(0.5))

    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_for("slow", timeout=0.01)


@pytest.mark.asyncio
async def test_manager_wait_error():
    manager = AsyncTaskManager()

    async def fail():
        raise ValueError("oops")

    await manager.submit("fail", fail())

    # Wait for completion first (or wait_for will wait for task)
    with pytest.raises(ValueError, match="oops"):
        await manager.wait_for("fail")

    # Check status
    status = manager.get_status()
    assert "fail" in status["failed"]


@pytest.mark.asyncio
async def test_manager_wait_all():
    manager = AsyncTaskManager()
    await manager.submit("t1", partial(asyncio.sleep, 0.01, result=1)())
    await manager.submit("t2", partial(asyncio.sleep, 0.01, result=2)())

    summary = await manager.wait_all()
    assert summary["results"] == {"t1": 1, "t2": 2}
    assert summary["errors"] == {}

    status = manager.get_status()
    assert status["total"] == 2
