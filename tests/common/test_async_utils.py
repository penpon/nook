"""
nook/common/async_utils.py のテスト

テスト観点:
- TaskResult（タスク実行結果クラス）
- gather_with_errors（並行実行・エラーハンドリング）
- run_with_semaphore（セマフォ制御付き並行実行）
- batch_process（バッチ処理）
- run_sync_in_thread（同期関数の非同期実行）
- AsyncTaskManager（非同期タスクマネージャー）
"""

import asyncio
import time

import pytest

from nook.common.async_utils import (
    AsyncTaskManager,
    TaskResult,
    batch_process,
    gather_with_errors,
    run_sync_in_thread,
    run_with_semaphore,
)

# =============================================================================
# 1. TaskResultのテスト
# =============================================================================


@pytest.mark.unit
def test_task_result_success():
    """
    Given: 成功したタスクの情報
    When: TaskResultを初期化
    Then: success=True、結果が設定され、timestampが生成される
    """
    # When
    result = TaskResult(name="task1", success=True, result="data")

    # Then
    assert result.name == "task1"
    assert result.success is True
    assert result.result == "data"
    assert result.error is None
    assert result.timestamp is not None


@pytest.mark.unit
def test_task_result_failure():
    """
    Given: 失敗したタスクの情報
    When: TaskResultを初期化
    Then: success=False、エラーが設定され、timestampが生成される
    """
    # Given
    error = ValueError("test error")

    # When
    result = TaskResult(name="task1", success=False, error=error)

    # Then
    assert result.name == "task1"
    assert result.success is False
    assert result.result is None
    assert result.error == error
    assert result.timestamp is not None


# =============================================================================
# 2. gather_with_errorsのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_all_success():
    """
    Given: 全タスクが成功するコルーチンリスト
    When: gather_with_errorsを実行
    Then: 全結果がsuccess=Trueで返される
    """

    # Given
    async def task(n):
        await asyncio.sleep(0.01)
        return n * 2

    # When
    results = await gather_with_errors(task(1), task(2), task(3))

    # Then
    assert len(results) == 3
    assert all(r.success for r in results)
    assert results[0].result == 2
    assert results[1].result == 4
    assert results[2].result == 6


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_partial_failure():
    """
    Given: 一部が失敗するタスクリスト
    When: gather_with_errorsを実行
    Then: 成功と失敗が混在した結果が返される
    """

    # Given
    async def success_task(n):
        return n * 2

    async def failure_task():
        raise ValueError("test error")

    # When
    results = await gather_with_errors(success_task(1), failure_task(), success_task(3))

    # Then
    assert len(results) == 3
    assert results[0].success is True
    assert results[0].result == 2
    assert results[1].success is False
    assert isinstance(results[1].error, ValueError)
    assert results[2].success is True
    assert results[2].result == 6


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_custom_names():
    """
    Given: カスタムtask_namesを指定
    When: gather_with_errorsを実行
    Then: TaskResultにカスタム名が設定される
    """

    # Given
    async def task(n):
        return n * 2

    task_names = ["Alpha", "Beta", "Gamma"]

    # When
    results = await gather_with_errors(task(1), task(2), task(3), task_names=task_names)

    # Then
    assert len(results) == 3
    assert results[0].name == "Alpha"
    assert results[1].name == "Beta"
    assert results[2].name == "Gamma"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_all_failure():
    """
    Given: 全タスクが失敗するコルーチンリスト
    When: gather_with_errorsを実行
    Then: 全結果がsuccess=Falseで返される
    """

    # Given
    async def failure_task(msg):
        raise RuntimeError(msg)

    # When
    results = await gather_with_errors(
        failure_task("error1"), failure_task("error2"), failure_task("error3")
    )

    # Then
    assert len(results) == 3
    assert all(not r.success for r in results)
    assert all(isinstance(r.error, RuntimeError) for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_invalid_task_names_length():
    """
    Given: コルーチン数とtask_names長さが不一致
    When: gather_with_errorsを実行
    Then: ValueErrorが発生
    """

    # Given
    async def task(n):
        return n * 2

    # When/Then
    with pytest.raises(ValueError, match="task_names must have the same length"):
        await gather_with_errors(task(1), task(2), task(3), task_names=["A", "B"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_no_return_exceptions():
    """
    Given: return_exceptions=Falseで失敗するタスク
    When: gather_with_errorsを実行
    Then: 例外が再発生する
    """

    # Given
    async def failure_task():
        raise ValueError("test error")

    # When/Then
    with pytest.raises(ValueError, match="test error"):
        await gather_with_errors(failure_task(), return_exceptions=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_empty():
    """
    Given: 空のコルーチンリスト
    When: gather_with_errorsを実行
    Then: 空のリストが返される
    """
    # When
    results = await gather_with_errors()

    # Then
    assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gather_with_errors_single_task():
    """
    Given: 単一のコルーチン
    When: gather_with_errorsを実行
    Then: 1つのTaskResultが返される
    """

    # Given
    async def task():
        return 42

    # When
    results = await gather_with_errors(task())

    # Then
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].result == 42


# =============================================================================
# 3. run_with_semaphoreのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_concurrency_limit():
    """
    Given: max_concurrent=2で5つのタスク
    When: run_with_semaphoreを実行
    Then: 最大2並行で実行され、全結果が返される
    """
    # Given
    concurrent_count = 0
    max_concurrent_seen = 0

    async def task(n):
        nonlocal concurrent_count, max_concurrent_seen
        concurrent_count += 1
        max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
        await asyncio.sleep(0.05)
        concurrent_count -= 1
        return n * 2

    coros = [lambda x=i: task(x) for i in range(5)]

    # When
    results = await run_with_semaphore(coros, max_concurrent=2)

    # Then
    assert len(results) == 5
    assert max_concurrent_seen <= 2
    assert sorted(results) == [0, 2, 4, 6, 8]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_progress_callback():
    """
    Given: progress_callbackを設定
    When: run_with_semaphoreを実行
    Then: 各タスク完了時にコールバックが呼ばれる
    """

    # Given
    async def task(n):
        await asyncio.sleep(0.01)
        return n

    progress_calls = []

    async def progress_callback(completed, total):
        progress_calls.append((completed, total))

    coros = [lambda x=i: task(x) for i in range(3)]

    # When
    await run_with_semaphore(coros, max_concurrent=2, progress_callback=progress_callback)

    # Then
    assert len(progress_calls) == 3
    assert progress_calls[0][1] == 3  # total
    assert progress_calls[-1][0] == 3  # completed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_all_success():
    """
    Given: 3つの成功タスク
    When: run_with_semaphoreを実行
    Then: 全結果が正常に返却される
    """

    # Given
    async def task(n):
        await asyncio.sleep(0.01)
        return n * 3

    coros = [lambda x=i: task(x) for i in range(3)]

    # When
    results = await run_with_semaphore(coros, max_concurrent=10)

    # Then
    assert results == [0, 3, 6]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_task_failure():
    """
    Given: 失敗するタスクを含むリスト
    When: run_with_semaphoreを実行
    Then: 例外が伝播する
    """

    # Given
    async def success_task(n):
        return n

    async def failure_task():
        raise ValueError("task failed")

    coros = [lambda: success_task(1), lambda: failure_task()]

    # When/Then
    with pytest.raises(ValueError, match="task failed"):
        await run_with_semaphore(coros, max_concurrent=2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_callback_failure():
    """
    Given: progress_callbackが例外を発生
    When: run_with_semaphoreを実行
    Then: タスク実行が例外で失敗する
    """

    # Given
    async def task(n):
        return n

    async def failing_callback(completed, total):
        raise RuntimeError("callback error")

    coros = [lambda x=i: task(x) for i in range(2)]

    # When/Then
    with pytest.raises(RuntimeError, match="callback error"):
        await run_with_semaphore(coros, max_concurrent=2, progress_callback=failing_callback)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_max_concurrent_one():
    """
    Given: max_concurrent=1で3つのタスク
    When: run_with_semaphoreを実行
    Then: 完全に直列実行される
    """
    # Given
    execution_order = []

    async def task(n):
        execution_order.append(f"start-{n}")
        await asyncio.sleep(0.01)
        execution_order.append(f"end-{n}")
        return n

    coros = [lambda x=i: task(x) for i in range(3)]

    # When
    results = await run_with_semaphore(coros, max_concurrent=1)

    # Then
    assert results == [0, 1, 2]
    # 完全直列なのでstart/endが交互に現れる
    assert execution_order[0] == "start-0"
    assert execution_order[1] == "end-0"
    assert execution_order[2] == "start-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_semaphore_empty():
    """
    Given: 空のコルーチンリスト
    When: run_with_semaphoreを実行
    Then: 空のリストが返される
    """
    # When
    results = await run_with_semaphore([], max_concurrent=10)

    # Then
    assert results == []


# =============================================================================
# 4. batch_processのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_multiple_batches():
    """
    Given: 250アイテム、batch_size=100
    When: batch_processを実行
    Then: 3バッチに分割して処理される
    """
    # Given
    items = list(range(250))
    batch_sizes = []

    async def processor(batch):
        batch_sizes.append(len(batch))
        await asyncio.sleep(0.01)
        return sum(batch)

    # When
    results = await batch_process(items, processor, batch_size=100, max_concurrent_batches=5)

    # Then
    assert len(results) == 3
    assert batch_sizes == [100, 100, 50]
    assert sum(results) == sum(items)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_single_batch():
    """
    Given: 50アイテム、batch_size=100
    When: batch_processを実行
    Then: 1バッチで処理される
    """
    # Given
    items = list(range(50))

    async def processor(batch):
        return len(batch)

    # When
    results = await batch_process(items, processor, batch_size=100)

    # Then
    assert len(results) == 1
    assert results[0] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_processor_failure():
    """
    Given: processorが例外を発生
    When: batch_processを実行
    Then: 例外が伝播する
    """
    # Given
    items = list(range(10))

    async def failing_processor(batch):
        raise RuntimeError("processor error")

    # When/Then
    with pytest.raises(RuntimeError, match="processor error"):
        await batch_process(items, failing_processor, batch_size=5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_concurrent_limit():
    """
    Given: max_concurrent_batches=2で5バッチ
    When: batch_processを実行
    Then: 最大2バッチが並行実行される
    """
    # Given
    items = list(range(500))
    concurrent_count = 0
    max_concurrent_seen = 0
    lock = asyncio.Lock()

    async def processor(batch):
        nonlocal concurrent_count, max_concurrent_seen
        async with lock:
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
        await asyncio.sleep(0.05)
        async with lock:
            concurrent_count -= 1
        return len(batch)

    # When
    results = await batch_process(items, processor, batch_size=100, max_concurrent_batches=2)

    # Then
    assert len(results) == 5
    assert max_concurrent_seen <= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_empty():
    """
    Given: 空のアイテムリスト
    When: batch_processを実行
    Then: 空のリストが返される
    """
    # Given
    items = []

    async def processor(batch):
        return len(batch)

    # When
    results = await batch_process(items, processor, batch_size=100)

    # Then
    assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_process_exact_batch_size():
    """
    Given: 100アイテム、batch_size=100
    When: batch_processを実行
    Then: ちょうど1バッチで処理される
    """
    # Given
    items = list(range(100))

    async def processor(batch):
        return len(batch)

    # When
    results = await batch_process(items, processor, batch_size=100)

    # Then
    assert len(results) == 1
    assert results[0] == 100


# =============================================================================
# 5. run_sync_in_threadのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sync_in_thread_success():
    """
    Given: 通常の同期関数
    When: run_sync_in_threadを実行
    Then: Futureが返却され、結果が取得できる
    """

    # Given
    def sync_func():
        return 42

    # When
    future = run_sync_in_thread(sync_func)
    result = await future

    # Then
    assert result == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sync_in_thread_with_args():
    """
    Given: 引数とkwargsを持つ同期関数
    When: run_sync_in_threadで引数を渡す
    Then: 引数が正しく渡され、結果が返される
    """

    # Given
    def sync_func(a, b, c=0):
        return a + b + c

    # When
    future = run_sync_in_thread(sync_func, 10, 20, c=5)
    result = await future

    # Then
    assert result == 35


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sync_in_thread_exception():
    """
    Given: 例外を発生する同期関数
    When: run_sync_in_threadを実行
    Then: Futureから例外が取得できる
    """

    # Given
    def failing_func():
        raise ValueError("sync error")

    # When
    future = run_sync_in_thread(failing_func)

    # Then
    with pytest.raises(ValueError, match="sync error"):
        await future


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sync_in_thread_blocking_operation():
    """
    Given: time.sleepを含む同期関数
    When: run_sync_in_threadを実行
    Then: 非ブロッキングで実行される
    """

    # Given
    def blocking_func():
        time.sleep(0.1)
        return "done"

    # When
    start = time.time()
    future = run_sync_in_thread(blocking_func)

    # 他のタスクを並行実行できることを確認
    await asyncio.sleep(0.01)
    elapsed_before_wait = time.time() - start

    result = await future

    # Then
    assert result == "done"
    # future作成直後はブロックしていない
    assert elapsed_before_wait < 0.1


# =============================================================================
# 6. AsyncTaskManagerのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_init():
    """
    Given: max_concurrent=5
    When: AsyncTaskManagerを初期化
    Then: 空の状態で初期化される
    """
    # When
    manager = AsyncTaskManager(max_concurrent=5)

    # Then
    assert manager.max_concurrent == 5
    assert len(manager.tasks) == 0
    assert len(manager.results) == 0
    assert len(manager.errors) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_submit_success():
    """
    Given: 成功するタスク
    When: submitを実行
    Then: タスクIDが返却され、実行が開始される
    """
    # Given
    manager = AsyncTaskManager()

    async def task():
        await asyncio.sleep(0.01)
        return "success"

    # When
    task_id = await manager.submit("task1", task())

    # Then
    assert task_id == "task1"
    assert "task1" in manager.tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_submit_multiple():
    """
    Given: 3つのタスク
    When: 複数submitを実行
    Then: 全タスクが実行される
    """
    # Given
    manager = AsyncTaskManager()

    async def task(n):
        await asyncio.sleep(0.01)
        return n * 2

    # When
    await manager.submit("task1", task(1))
    await manager.submit("task2", task(2))
    await manager.submit("task3", task(3))

    # Then
    assert len(manager.tasks) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_success():
    """
    Given: 完了するタスク
    When: wait_forを実行
    Then: 結果が返却される
    """
    # Given
    manager = AsyncTaskManager()

    async def task():
        await asyncio.sleep(0.01)
        return 42

    # When
    await manager.submit("task1", task())
    result = await manager.wait_for("task1")

    # Then
    assert result == 42
    assert "task1" in manager.results


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_all_success():
    """
    Given: 複数のタスク
    When: wait_allを実行
    Then: results/errors辞書が返却される
    """
    # Given
    manager = AsyncTaskManager()

    async def task(n):
        await asyncio.sleep(0.01)
        return n * 2

    # When
    await manager.submit("task1", task(1))
    await manager.submit("task2", task(2))
    result = await manager.wait_all()

    # Then
    assert len(result["results"]) == 2
    assert result["results"]["task1"] == 2
    assert result["results"]["task2"] == 4
    assert len(result["errors"]) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_get_status():
    """
    Given: 実行中・完了・失敗が混在
    When: get_statusを実行
    Then: 正しいステータスが返却される
    """
    # Given
    manager = AsyncTaskManager()

    async def success_task():
        await asyncio.sleep(0.01)
        return "ok"

    async def failure_task():
        await asyncio.sleep(0.01)
        raise ValueError("error")

    async def long_task():
        await asyncio.sleep(1)
        return "done"

    # When
    await manager.submit("success", success_task())
    await manager.submit("failure", failure_task())
    await manager.submit("running", long_task())

    # 一部完了を待つ
    await asyncio.sleep(0.05)

    status = manager.get_status()

    # Then
    assert "running" in status["running"]
    assert "success" in status["completed"]
    assert "failure" in status["failed"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_submit_duplicate_name():
    """
    Given: 既に存在するタスク名
    When: 同じ名前でsubmitを実行
    Then: ValueErrorが発生
    """
    # Given
    manager = AsyncTaskManager()

    async def task():
        await asyncio.sleep(0.1)
        return "ok"

    await manager.submit("task1", task())

    # When/Then
    with pytest.raises(ValueError, match="Task task1 already exists"):
        await manager.submit("task1", task())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_not_found():
    """
    Given: 存在しないタスク名
    When: wait_forを実行
    Then: ValueErrorが発生
    """
    # Given
    manager = AsyncTaskManager()

    # When/Then
    with pytest.raises(ValueError, match="Task not_found not found"):
        await manager.wait_for("not_found")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_failed_task():
    """
    Given: 失敗したタスク
    When: wait_forを実行
    Then: 保存された例外が再発生
    """
    # Given
    manager = AsyncTaskManager()

    async def failing_task():
        raise RuntimeError("task error")

    # When
    await manager.submit("task1", failing_task())

    # Then
    with pytest.raises(RuntimeError, match="task error"):
        await manager.wait_for("task1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_timeout():
    """
    Given: timeout内に完了しないタスク
    When: wait_forをtimeout指定で実行
    Then: TimeoutErrorが発生
    """
    # Given
    manager = AsyncTaskManager()

    async def long_task():
        await asyncio.sleep(1)
        return "done"

    # When
    await manager.submit("task1", long_task())

    # Then
    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_for("task1", timeout=0.05)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_task_exception():
    """
    Given: タスクが例外を発生
    When: タスクを実行
    Then: errorsに記録される
    """
    # Given
    manager = AsyncTaskManager()

    async def failing_task():
        await asyncio.sleep(0.01)
        raise ValueError("test error")

    # When
    await manager.submit("task1", failing_task())
    await asyncio.sleep(0.05)

    # Then
    assert "task1" in manager.errors
    assert isinstance(manager.errors["task1"], ValueError)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_all_partial():
    """
    Given: timeout内に一部のみ完了するタスク
    When: wait_allをtimeout指定で実行
    Then: 完了分のみresultsに含まれる
    """
    # Given
    manager = AsyncTaskManager()

    async def quick_task():
        await asyncio.sleep(0.01)
        return "quick"

    async def slow_task():
        await asyncio.sleep(1)
        return "slow"

    # When
    await manager.submit("quick", quick_task())
    await manager.submit("slow", slow_task())
    result = await manager.wait_all(timeout=0.1)

    # Then
    assert "quick" in result["results"]
    # slowタスクはtimeout内に完了しない


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_empty():
    """
    Given: タスクをsubmitしない
    When: wait_allを実行
    Then: 空のresults/errorsが返される
    """
    # Given
    manager = AsyncTaskManager()

    # When
    result = await manager.wait_all()

    # Then
    assert result["results"] == {}
    assert result["errors"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_completed():
    """
    Given: 既に完了したタスク
    When: wait_forを実行
    Then: 即座に結果が返される
    """
    # Given
    manager = AsyncTaskManager()

    async def task():
        return 100

    # When
    await manager.submit("task1", task())
    await asyncio.sleep(0.05)  # 完了を待つ

    # タスク完了後にwait_for
    result = await manager.wait_for("task1")

    # Then
    assert result == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_task_manager_wait_for_failed_completed():
    """
    Given: 既に失敗したタスク
    When: wait_forを実行
    Then: 即座に例外が発生
    """
    # Given
    manager = AsyncTaskManager()

    async def failing_task():
        raise RuntimeError("error")

    # When
    await manager.submit("task1", failing_task())
    await asyncio.sleep(0.05)  # 完了を待つ

    # Then
    with pytest.raises(RuntimeError, match="error"):
        await manager.wait_for("task1")
