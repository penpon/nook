"""nook/api/middleware/error_handler.py のテスト"""

from unittest.mock import Mock

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from nook.api.middleware.error_handler import (
    create_error_response,
    handle_exception,
)
from nook.common.exceptions import (
    APIException,
    ConfigurationException,
    DataException,
    NookException,
    ServiceException,
)


@pytest.mark.unit
class TestCreateErrorResponse:
    """create_error_response関数のテスト"""

    def test_basic_error_response(self):
        """基本的なエラーレスポンスの作成"""
        response = create_error_response(
            status_code=400,
            error_type="test_error",
            message="Test message",
            error_id="12345",
        )

        assert response.status_code == 400
        content = response.body.decode()
        assert "test_error" in content
        assert "Test message" in content
        assert "12345" in content

    def test_error_response_with_details(self):
        """詳細情報付きエラーレスポンス"""
        details = {"field": "email", "reason": "invalid format"}
        response = create_error_response(
            status_code=422,
            error_type="validation",
            message="Validation failed",
            error_id="67890",
            details=details,
        )

        assert response.status_code == 422
        content = response.body.decode()
        assert "email" in content
        assert "invalid format" in content

    def test_error_response_structure(self):
        """エラーレスポンスの構造確認"""
        response = create_error_response(
            status_code=500,
            error_type="internal_error",
            message="Server error",
            error_id="error123",
        )

        import json

        content = json.loads(response.body)
        assert "error" in content
        assert content["error"]["type"] == "internal_error"
        assert content["error"]["message"] == "Server error"
        assert content["error"]["error_id"] == "error123"
        assert "timestamp" in content["error"]
        assert content["error"]["status_code"] == 500


@pytest.mark.unit
class TestHandleException:
    """handle_exception関数のテスト"""

    def _create_mock_request(self):
        """モックRequestオブジェクトの作成"""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com/api/test")
        request.headers = {}
        return request

    def test_handle_api_exception(self):
        """APIExceptionの処理"""
        request = self._create_mock_request()
        exc = APIException("API call failed", status_code=503)

        response = handle_exception(exc, request)

        assert response.status_code == 503

    def test_handle_configuration_exception(self):
        """ConfigurationExceptionの処理"""
        request = self._create_mock_request()
        exc = ConfigurationException("Invalid config")

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_handle_data_exception(self):
        """DataExceptionの処理"""
        request = self._create_mock_request()
        exc = DataException("Invalid data format")

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_handle_service_exception(self):
        """ServiceExceptionの処理"""
        request = self._create_mock_request()
        exc = ServiceException("Service unavailable")

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_handle_nook_exception(self):
        """NookExceptionの処理"""
        request = self._create_mock_request()
        exc = NookException("General error")

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_handle_request_validation_error(self):
        """RequestValidationErrorの処理"""
        request = self._create_mock_request()

        # RequestValidationErrorのモック作成
        exc = Mock(spec=RequestValidationError)
        exc.errors = Mock(return_value=[{"field": "email", "msg": "invalid"}])

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_handle_starlette_http_exception(self):
        """StarletteHTTPExceptionの処理"""
        request = self._create_mock_request()
        exc = StarletteHTTPException(status_code=404, detail="Not found")

        response = handle_exception(exc, request)

        assert response.status_code == 404

    def test_handle_unexpected_exception(self):
        """予期しない例外の処理"""
        request = self._create_mock_request()
        exc = ValueError("Unexpected error")

        response = handle_exception(exc, request)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_error_id_generation(self):
        """エラーIDが生成されることを確認"""
        request = self._create_mock_request()
        exc = Exception("Test error")

        response = handle_exception(exc, request)

        import json

        content = json.loads(response.body)
        assert "error_id" in content["error"]
        assert len(content["error"]["error_id"]) > 0
