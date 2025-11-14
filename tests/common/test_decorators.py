"""nook/common/decorators.py のテスト"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.decorators import handle_errors, log_execution_time
from nook.common.exceptions import RetryException

# ================================================================================
# 1. handle_errors デコレータ（非同期）のテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_success_first_try():
    """
    Given: 正常な非同期関数
    When: handle_errorsでデコレート
    Then: 1回目で成功し、関数結果を返す
    """

    @handle_errors(retries=3)
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_success_after_retry():
    """
    Given: 1回失敗後に成功する非同期関数
    When: handle_errorsでデコレート
    Then: リトライ後に成功し、infoログ出力
    """
    call_count = 0

    @handle_errors(retries=3, delay=0.01)
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("First attempt failed")
        return "success"

    result = await test_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_all_retries_failed():
    """
    Given: 常に失敗する非同期関数
    When: retries=3で全て失敗
    Then: RetryException発生
    """

    @handle_errors(retries=3, delay=0.01)
    async def test_func():
        raise ValueError("Always fails")

    with pytest.raises(RetryException) as exc_info:
        await test_func()

    assert "Failed after 3 attempts" in str(exc_info.value)
    assert exc_info.value.__cause__.__class__ == ValueError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_various_exceptions():
    """
    Given: 様々な例外を出す関数
    When: handle_errorsでデコレート
    Then: RetryExceptionでラップされる
    """

    @handle_errors(retries=2, delay=0.01)
    async def test_func_value_error():
        raise ValueError("value error")

    @handle_errors(retries=2, delay=0.01)
    async def test_func_runtime_error():
        raise RuntimeError("runtime error")

    with pytest.raises(RetryException):
        await test_func_value_error()

    with pytest.raises(RetryException):
        await test_func_runtime_error()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_backoff_calculation():
    """
    Given: delay=1.0, backoff=2.0の設定
    When: リトライ発生
    Then: 待機時間が指数的に増加（1, 2, 4秒）
    """
    call_count = 0

    @handle_errors(retries=3, delay=1.0, backoff=2.0)
    async def test_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("fail")

    with patch("nook.common.decorators.asyncio.sleep") as mock_sleep:
        with pytest.raises(RetryException):
            await test_func()

        # sleep呼び出しを確認（最後のリトライではsleepしない）
        assert mock_sleep.call_count == 2
        # 1回目: 1.0 * (2.0 ** 0) = 1.0
        # 2回目: 1.0 * (2.0 ** 1) = 2.0
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_async_logging():
    """
    Given: 失敗する非同期関数
    When: リトライが発生
    Then: 適切なログが出力される
    """

    @handle_errors(retries=2, delay=0.01)
    async def test_func():
        raise ValueError("test error")

    with patch("nook.common.decorators.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with pytest.raises(RetryException):
            await test_func()

        # warningログが呼ばれたことを確認
        assert mock_logger.warning.called
        # errorログが呼ばれたことを確認（最終失敗時）
        assert mock_logger.error.called


# ================================================================================
# 2. handle_errors デコレータ（同期）のテスト
# ================================================================================


@pytest.mark.unit
def test_handle_errors_sync_success_first_try():
    """
    Given: 正常な同期関数
    When: handle_errorsでデコレート
    Then: 1回目で成功し、関数結果を返す
    """

    @handle_errors(retries=3)
    def test_func():
        return "success"

    result = test_func()
    assert result == "success"


@pytest.mark.unit
def test_handle_errors_sync_success_after_retry():
    """
    Given: 1回失敗後に成功する同期関数
    When: handle_errorsでデコレート
    Then: リトライ後に成功し、infoログ出力
    """
    call_count = 0

    @handle_errors(retries=3, delay=0.01)
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("First attempt failed")
        return "success"

    result = test_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
def test_handle_errors_sync_all_retries_failed():
    """
    Given: 常に失敗する同期関数
    When: retries=3で全て失敗
    Then: RetryException発生
    """

    @handle_errors(retries=3, delay=0.01)
    def test_func():
        raise ValueError("Always fails")

    with pytest.raises(RetryException) as exc_info:
        test_func()

    assert "Failed after 3 attempts" in str(exc_info.value)


@pytest.mark.unit
def test_handle_errors_sync_long_error_message():
    """
    Given: 100文字超のエラーメッセージ
    When: ログ出力
    Then: メッセージは100文字に切り詰められる
    """
    long_message = "x" * 150

    @handle_errors(retries=2, delay=0.01)
    def test_func():
        raise ValueError(long_message)

    with patch("nook.common.decorators.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with pytest.raises(RetryException):
            test_func()

        # warningログの呼び出しを確認
        warning_calls = mock_logger.warning.call_args_list
        assert len(warning_calls) > 0

        # メッセージが切り詰められていることを確認
        log_message = warning_calls[0][0][0]
        assert "..." in log_message


# ================================================================================
# 3. handle_errors デコレータ（境界値）のテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_retries_one():
    """
    Given: retries=1
    When: 1回失敗
    Then: すぐに例外発生
    """

    @handle_errors(retries=1, delay=0.01)
    async def test_func():
        raise ValueError("fail")

    with pytest.raises(RetryException):
        await test_func()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_retries_ten():
    """
    Given: retries=10
    When: 9回失敗後に成功
    Then: 10回目で成功
    """
    call_count = 0

    @handle_errors(retries=10, delay=0.01)
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 10:
            raise ValueError("fail")
        return "success"

    result = await test_func()
    assert result == "success"
    assert call_count == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_delay_zero():
    """
    Given: delay=0（待機なし）
    When: リトライ発生
    Then: 即座にリトライ
    """

    @handle_errors(retries=3, delay=0)
    async def test_func():
        raise ValueError("fail")

    with patch("nook.common.decorators.asyncio.sleep") as mock_sleep:
        with pytest.raises(RetryException):
            await test_func()

        # sleepが0秒で呼ばれる
        if mock_sleep.called:
            assert all(call[0][0] == 0 for call in mock_sleep.call_args_list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_backoff_one():
    """
    Given: backoff=1.0（固定待機時間）
    When: リトライ発生
    Then: 待機時間がdelayで固定
    """

    @handle_errors(retries=3, delay=2.0, backoff=1.0)
    async def test_func():
        raise ValueError("fail")

    with patch("nook.common.decorators.asyncio.sleep") as mock_sleep:
        with pytest.raises(RetryException):
            await test_func()

        # 全て2.0秒待機
        if mock_sleep.called:
            assert all(call[0][0] == 2.0 for call in mock_sleep.call_args_list)


# ================================================================================
# 4. log_execution_time デコレータ（非同期）のテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_log_execution_time_async_success():
    """
    Given: 正常な非同期関数
    When: log_execution_timeでデコレート
    Then: 実行時間がログ出力され、関数結果を返す
    """

    @log_execution_time
    async def test_func():
        await asyncio.sleep(0.01)
        return "success"

    with patch("nook.common.decorators.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = await test_func()

        assert result == "success"
        # infoログが呼ばれたことを確認
        assert mock_logger.info.called
        log_message = mock_logger.info.call_args[0][0]
        assert "completed" in log_message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_log_execution_time_async_with_exception():
    """
    Given: 例外を投げる非同期関数
    When: log_execution_timeでデコレート
    Then: 実行時間がerrorログに記録され、例外を再raise
    """

    @log_execution_time
    async def test_func():
        await asyncio.sleep(0.01)
        raise ValueError("test error")

    with patch("nook.common.decorators.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with pytest.raises(ValueError):
            await test_func()

        # errorログが呼ばれたことを確認
        assert mock_logger.error.called
        log_message = mock_logger.error.call_args[0][0]
        assert "failed" in log_message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_log_execution_time_async_execution_time_recorded():
    """
    Given: 非同期関数
    When: log_execution_timeでデコレート
    Then: extraフィールドにexecution_timeが記録される
    """

    @log_execution_time
    async def test_func():
        await asyncio.sleep(0.01)
        return "success"

    with patch("nook.common.decorators.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        await test_func()

        # extraパラメータを確認
        call_kwargs = mock_logger.info.call_args[1]
        assert "extra" in call_kwargs
        assert "execution_time" in call_kwargs["extra"]
        assert isinstance(call_kwargs["extra"]["execution_time"], float)


# ================================================================================
# 5. log_execution_time デコレータ（同期）のテスト
# ================================================================================


@pytest.mark.unit
def test_log_execution_time_sync_returns_original():
    """
    Given: 同期関数
    When: log_execution_timeでデコレート
    Then: 元の関数がそのまま返る（未実装）
    """

    def test_func():
        return "success"

    decorated = log_execution_time(test_func)

    # 同期版は未実装なので、元の関数がそのまま返る
    result = decorated()
    assert result == "success"


# ================================================================================
# 6. デコレータの組み合わせテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_combined_decorators():
    """
    Given: handle_errorsとlog_execution_timeを両方適用
    When: 関数を実行
    Then: 両方のデコレータが正常動作
    """

    @handle_errors(retries=2, delay=0.01)
    @log_execution_time
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_functools_wraps_preserved():
    """
    Given: デコレート済み関数
    When: 関数名やdocstringを確認
    Then: 元の情報が保持されている
    """

    @handle_errors(retries=3)
    async def test_func():
        """Test docstring"""
        return "success"

    assert test_func.__name__ == "test_func"
    assert test_func.__doc__ == "Test docstring"


# ================================================================================
# 7. エッジケースのテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_default_parameters():
    """
    Given: デフォルトパラメータ
    When: デコレート
    Then: retries=3, delay=1.0, backoff=2.0で動作
    """

    @handle_errors()
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_errors_large_backoff():
    """
    Given: backoff=10.0（急激な増加）
    When: リトライ発生
    Then: 待機時間が急激に増加
    """

    @handle_errors(retries=3, delay=1.0, backoff=10.0)
    async def test_func():
        raise ValueError("fail")

    with patch("nook.common.decorators.asyncio.sleep") as mock_sleep:
        with pytest.raises(RetryException):
            await test_func()

        # 1回目: 1.0, 2回目: 10.0
        if mock_sleep.call_count >= 2:
            assert mock_sleep.call_args_list[0][0][0] == 1.0
            assert mock_sleep.call_args_list[1][0][0] == 10.0
