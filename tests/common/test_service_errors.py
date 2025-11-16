"""nook/common/service_errors.py のテスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.exceptions import APIException, ServiceException
from nook.common.service_errors import ServiceErrorHandler

# ================================================================================
# 1. ServiceErrorHandler.__init__ のテスト
# ================================================================================


@pytest.mark.unit
def test_service_error_handler_init():
    """
    Given: service_name="test_service"
    When: ServiceErrorHandlerを初期化
    Then: 正常に初期化される
    """
    handler = ServiceErrorHandler("test_service")
    assert handler.service_name == "test_service"
    assert handler.logger.name == "test_service"


# ================================================================================
# 2. handle_api_error デコレータのテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_success():
    """
    Given: 正常な非同期関数
    When: handle_api_errorでデコレート
    Then: 関数結果を返す
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_with_response_attribute():
    """
    Given: response属性を持つ例外を投げる関数
    When: handle_api_errorでデコレート
    Then: APIExceptionが発生し、status_codeとresponse_bodyが含まれる
    """
    handler = ServiceErrorHandler("test_service")

    class HTTPError(Exception):
        def __init__(self, response):
            self.response = response

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    @handler.handle_api_error("test_api")
    async def test_func():
        raise HTTPError(mock_response)

    with pytest.raises(APIException) as exc_info:
        await test_func()

    assert "test_api API error" in str(exc_info.value)
    assert exc_info.value.status_code == 404
    assert exc_info.value.response_body == "Not Found"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_with_status_code_500():
    """
    Given: status_code=500のHTTPエラー
    When: handle_api_errorでデコレート
    Then: APIExceptionが発生
    """
    handler = ServiceErrorHandler("test_service")

    class HTTPError(Exception):
        def __init__(self, response):
            self.response = response

    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server Error"

    @handler.handle_api_error("test_api")
    async def test_func():
        raise HTTPError(mock_response)

    with pytest.raises(APIException) as exc_info:
        await test_func()

    assert exc_info.value.status_code == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_without_response_attribute():
    """
    Given: response属性を持たない例外を投げる関数
    When: handle_api_errorでデコレート
    Then: APIExceptionが発生し、status_code=None
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    async def test_func():
        raise ValueError("generic error")

    with pytest.raises(APIException) as exc_info:
        await test_func()

    assert "test_api API error" in str(exc_info.value)
    assert exc_info.value.status_code is None
    assert exc_info.value.response_body is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_various_exceptions():
    """
    Given: 様々な例外を投げる関数
    When: handle_api_errorでデコレート
    Then: 全てAPIExceptionでラップされる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    async def test_func_value_error():
        raise ValueError("value error")

    @handler.handle_api_error("test_api")
    async def test_func_runtime_error():
        raise RuntimeError("runtime error")

    @handler.handle_api_error("test_api")
    async def test_func_key_error():
        raise KeyError("key error")

    with pytest.raises(APIException):
        await test_func_value_error()

    with pytest.raises(APIException):
        await test_func_runtime_error()

    with pytest.raises(APIException):
        await test_func_key_error()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_message_contains_api_name():
    """
    Given: api_name="github_api"
    When: エラー発生
    Then: エラーメッセージにapi_nameが含まれる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("github_api")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(APIException) as exc_info:
        await test_func()

    assert "github_api API error" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_exception_chain():
    """
    Given: 例外が発生
    When: handle_api_errorでデコレート
    Then: from句で元の例外がチェーンされる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    async def test_func():
        raise ValueError("original error")

    with pytest.raises(APIException) as exc_info:
        await test_func()

    assert exc_info.value.__cause__.__class__ == ValueError
    assert str(exc_info.value.__cause__) == "original error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_api_error_logging():
    """
    Given: エラーが発生
    When: handle_api_errorでデコレート
    Then: errorログが出力される
    """
    handler = ServiceErrorHandler("test_service")
    handler.logger = MagicMock()

    @handler.handle_api_error("test_api")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(APIException):
        await test_func()

    # exceptionログが呼ばれたことを確認
    assert handler.logger.exception.called
    log_message = handler.logger.exception.call_args[0][0]
    assert "API call failed" in log_message

    # extraパラメータの確認
    call_kwargs = handler.logger.exception.call_args[1]
    assert "extra" in call_kwargs
    assert call_kwargs["extra"]["service"] == "test_service"
    assert call_kwargs["extra"]["api"] == "test_api"


# ================================================================================
# 3. handle_data_processing デコレータのテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_success():
    """
    Given: 正常な非同期関数
    When: handle_data_processingでデコレート
    Then: 関数結果を返す
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_data_processing("parse data")
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_value_error():
    """
    Given: ValueErrorを投げる関数
    When: handle_data_processingでデコレート
    Then: ServiceExceptionが発生
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_data_processing("parse data")
    async def test_func():
        raise ValueError("invalid data")

    with pytest.raises(ServiceException) as exc_info:
        await test_func()

    assert "Failed to parse data" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_various_exceptions():
    """
    Given: 様々な例外を投げる関数
    When: handle_data_processingでデコレート
    Then: 全てServiceExceptionでラップされる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_data_processing("process")
    async def test_func_key_error():
        raise KeyError("key error")

    @handler.handle_data_processing("process")
    async def test_func_type_error():
        raise TypeError("type error")

    with pytest.raises(ServiceException):
        await test_func_key_error()

    with pytest.raises(ServiceException):
        await test_func_type_error()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_message_contains_operation():
    """
    Given: operation="transform data"
    When: エラー発生
    Then: エラーメッセージにoperationが含まれる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_data_processing("transform data")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(ServiceException) as exc_info:
        await test_func()

    assert "Failed to transform data" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_exception_chain():
    """
    Given: 例外が発生
    When: handle_data_processingでデコレート
    Then: from句で元の例外がチェーンされる
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_data_processing("process")
    async def test_func():
        raise ValueError("original error")

    with pytest.raises(ServiceException) as exc_info:
        await test_func()

    assert exc_info.value.__cause__.__class__ == ValueError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_data_processing_logging():
    """
    Given: エラーが発生
    When: handle_data_processingでデコレート
    Then: errorログが出力される
    """
    handler = ServiceErrorHandler("test_service")
    handler.logger = MagicMock()

    @handler.handle_data_processing("parse data")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(ServiceException):
        await test_func()

    # exceptionログが呼ばれたことを確認
    assert handler.logger.exception.called
    log_message = handler.logger.exception.call_args[0][0]
    assert "Data processing failed" in log_message

    # extraパラメータの確認
    call_kwargs = handler.logger.exception.call_args[1]
    assert "extra" in call_kwargs
    assert call_kwargs["extra"]["service"] == "test_service"
    assert call_kwargs["extra"]["operation"] == "parse data"


# ================================================================================
# 4. デコレータの組み合わせテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_decorators():
    """
    Given: 両方のデコレータを適用
    When: 関数を実行
    Then: 両方のデコレータが正常動作
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    @handler.handle_data_processing("parse data")
    async def test_func():
        return "success"

    result = await test_func()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_functools_wraps_preserved():
    """
    Given: デコレート済み関数
    When: 関数名を確認
    Then: 元の関数名が保持されている
    """
    handler = ServiceErrorHandler("test_service")

    @handler.handle_api_error("test_api")
    async def test_function():
        """Test docstring"""
        return "success"

    assert test_function.__name__ == "test_function"
    assert test_function.__doc__ == "Test docstring"


# ================================================================================
# 5. ログ出力の詳細確認
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_error_logging_exc_info():
    """
    Given: APIエラーが発生
    When: handle_api_errorでデコレート
    Then: logger.exception()が呼ばれる（自動的にexc_info=Trueを含む）
    """
    handler = ServiceErrorHandler("test_service")
    handler.logger = MagicMock()

    @handler.handle_api_error("test_api")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(APIException):
        await test_func()

    # logger.exception()は自動的にexc_info=Trueを含むため、呼び出しを確認
    assert handler.logger.exception.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_data_processing_logging_exc_info():
    """
    Given: データ処理エラーが発生
    When: handle_data_processingでデコレート
    Then: logger.exception()が呼ばれる（自動的にexc_info=Trueを含む）
    """
    handler = ServiceErrorHandler("test_service")
    handler.logger = MagicMock()

    @handler.handle_data_processing("parse data")
    async def test_func():
        raise ValueError("test error")

    with pytest.raises(ServiceException):
        await test_func()

    # logger.exception()は自動的にexc_info=Trueを含むため、呼び出しを確認
    assert handler.logger.exception.called
