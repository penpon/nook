from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.core.errors.exceptions import RetryException  # noqa: E402
from nook.core.utils.decorators import handle_errors, log_execution_time  # noqa: E402


def test_handle_errors_sync_success():
    """同期関数の成功時テスト"""

    @handle_errors(retries=2, delay=0.1, backoff=1.5)
    def sync_func():
        return "success"

    result = sync_func()
    assert result == "success"


def test_handle_errors_sync_retry_success():
    """同期関数のリトライ後成功テスト"""

    call_count = 0

    @handle_errors(retries=3, delay=0.01, backoff=1.0)
    def sync_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("temporary error")
        return "success"

    result = sync_func()
    assert result == "success"
    assert call_count == 2


def test_handle_errors_sync_failure():
    """同期関数の失敗時テスト"""

    @handle_errors(retries=2, delay=0.01, backoff=1.0)
    def sync_func():
        raise ValueError("persistent error")

    with pytest.raises(RetryException) as exc_info:
        sync_func()

    assert "Failed after 2 attempts" in str(exc_info.value)
    assert "persistent error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_errors_async_success():
    """非同期関数の成功時テスト"""

    @handle_errors(retries=2, delay=0.1, backoff=1.5)
    async def async_func():
        return "success"

    result = await async_func()
    assert result == "success"


@pytest.mark.asyncio
async def test_handle_errors_async_retry_success():
    """非同期関数のリトライ後成功テスト"""

    call_count = 0

    @handle_errors(retries=3, delay=0.01, backoff=1.0)
    async def async_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("temporary error")
        return "success"

    result = await async_func()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_handle_errors_async_failure():
    """非同期関数の失敗時テスト"""

    @handle_errors(retries=2, delay=0.01, backoff=1.0)
    async def async_func():
        raise ValueError("persistent error")

    with pytest.raises(RetryException) as exc_info:
        await async_func()

    assert "Failed after 2 attempts" in str(exc_info.value)
    assert "persistent error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_logs_warning_and_error(caplog):
    """警告とエラーログのテスト"""

    call_count = 0

    @handle_errors(retries=2, delay=0.01, backoff=1.0)
    async def async_func():
        nonlocal call_count
        call_count += 1
        raise RuntimeError(f"error {call_count}")

    caplog.set_level(logging.WARNING)

    with pytest.raises(RetryException):
        await async_func()

    # 警告ログが2回記録される（2回失敗）
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warnings) == 2

    # エラーログが1回記録される
    errors = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(errors) == 1
    assert "Function async_func failed after 2 attempts" in errors[0].message


@pytest.mark.asyncio
async def test_handle_error_with_long_message_truncates():
    """長いエラーメッセージの切り捨てテスト"""

    long_message = "x" * 200

    @handle_errors(retries=1, delay=0.01, backoff=1.0)
    async def async_func():
        raise ValueError(long_message)

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with pytest.raises(RetryException):
            await async_func()

        # 警告ログでメッセージが切り捨てられていることを確認
        warning_calls = mock_logger.warning.call_args_list
        assert len(warning_calls) == 1

        warning_args, _ = warning_calls[0]
        warning_message = warning_args[0]
        assert warning_message.endswith("...")  # 切り捨てマークが存在
        # メッセージ長が制限されていることを確認（元のメッセージ + 100文字以下）
        assert (
            len(warning_message)
            <= len("Function async_func failed (attempt 1/1): ValueError: ") + 103
        )


@pytest.mark.asyncio
async def test_log_execution_time_async_success(caplog):
    """非同期関数の実行時間ログ成功テスト"""

    @log_execution_time
    async def async_func():
        await asyncio.sleep(0.1)
        return "success"

    caplog.set_level(logging.INFO)

    result = await async_func()
    assert result == "success"

    # 成功ログが記録される
    info_records = [
        record
        for record in caplog.records
        if record.levelname == "INFO" and "completed" in record.message
    ]
    assert len(info_records) == 1

    # execution_timeフィールドを確認
    assert "execution_time" in info_records[0].__dict__


@pytest.mark.asyncio
async def test_log_execution_time_async_failure(caplog):
    """非同期関数の実行時間ログ失敗テスト"""

    @log_execution_time
    async def async_func():
        await asyncio.sleep(0.05)
        raise ValueError("test error")

    caplog.set_level(logging.ERROR)

    with pytest.raises(ValueError):
        await async_func()

    # エラーログが記録される
    error_records = [
        record
        for record in caplog.records
        if record.levelname == "ERROR" and "failed" in record.message
    ]
    assert len(error_records) == 1

    # execution_timeフィールドを確認
    assert "execution_time" in error_records[0].__dict__


def test_log_execution_time_sync_returns_original():
    """同期関数ではlog_execution_timeが元の関数を返すテスト"""

    @log_execution_time
    def sync_func():
        return "original"

    # 同期関数の場合はデコレータが適用されない（実装省略のため）
    result = sync_func()
    assert result == "original"


def test_handle_errors_backoff_calculation():
    """バックオフ計算のテスト"""

    call_times = []

    @handle_errors(retries=3, delay=0.1, backoff=2.0)
    async def async_func():
        call_times.append(time.time())
        if len(call_times) < 3:
            raise ValueError("retry")
        return "success"

    start_time = time.time()
    result = asyncio.run(async_func())
    end_time = time.time()

    assert result == "success"
    assert len(call_times) == 3

    # バックオフ時間が経過していることを確認
    total_time = end_time - start_time
    expected_delay = 0.1 + 0.2  # 1回目と2回目の待機時間
    assert total_time >= expected_delay


@pytest.mark.asyncio
async def test_handle_errors_with_different_exception_types():
    """異なる例外タイプのテスト"""

    @handle_errors(retries=2, delay=0.01, backoff=1.0)
    async def func_with_runtime_error():
        raise RuntimeError("runtime error")

    @handle_errors(retries=2, delay=0.01, backoff=1.0)
    async def func_with_value_error():
        raise ValueError("value error")

    with pytest.raises(RetryException) as exc_info:
        await func_with_runtime_error()
    assert "runtime error" in str(exc_info.value)

    with pytest.raises(RetryException) as exc_info:
        await func_with_value_error()
    assert "value error" in str(exc_info.value)
