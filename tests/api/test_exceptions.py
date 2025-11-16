"""nook/api/exceptions.py のテスト"""

import pytest
from fastapi import status

from nook.api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NookHTTPException,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


@pytest.mark.unit
class TestNookHTTPException:
    """NookHTTPException基底クラスのテスト"""

    def test_basic_creation(self):
        """基本的なNookHTTPExceptionの作成"""
        exc = NookHTTPException(
            status_code=400, detail="Test error", error_type="test_error"
        )
        assert exc.status_code == 400
        assert exc.detail == "Test error"
        assert exc.error_type == "test_error"

    def test_with_headers(self):
        """ヘッダー付きの例外作成"""
        exc = NookHTTPException(
            status_code=400,
            detail="Test",
            error_type="test",
            headers={"X-Custom": "value"},
        )
        assert exc.headers == {"X-Custom": "value"}


@pytest.mark.unit
class TestNotFoundError:
    """NotFoundErrorのテスト"""

    def test_creation(self):
        """NotFoundErrorの作成"""
        exc = NotFoundError(resource="User", identifier="123")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "User" in exc.detail
        assert "123" in exc.detail
        assert exc.error_type == "not_found"

    def test_various_resources(self):
        """様々なリソースタイプでのテスト"""
        resources = [("Content", "reddit"), ("File", "data.json"), ("API", "v1")]
        for resource, identifier in resources:
            exc = NotFoundError(resource=resource, identifier=identifier)
            assert resource in exc.detail
            assert identifier in exc.detail


@pytest.mark.unit
class TestAuthenticationError:
    """AuthenticationErrorのテスト"""

    def test_default_creation(self):
        """デフォルトメッセージでのAuthenticationError作成"""
        exc = AuthenticationError()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Authentication failed"
        assert exc.error_type == "authentication_error"
        assert "WWW-Authenticate" in exc.headers

    def test_custom_detail(self):
        """カスタムメッセージでの作成"""
        exc = AuthenticationError(detail="Invalid credentials")
        assert exc.detail == "Invalid credentials"
        assert exc.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.unit
class TestAuthorizationError:
    """AuthorizationErrorのテスト"""

    def test_default_creation(self):
        """デフォルトメッセージでのAuthorizationError作成"""
        exc = AuthorizationError()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "Insufficient permissions"
        assert exc.error_type == "authorization_error"

    def test_custom_detail(self):
        """カスタムメッセージでの作成"""
        exc = AuthorizationError(detail="Admin access required")
        assert exc.detail == "Admin access required"


@pytest.mark.unit
class TestValidationError:
    """ValidationErrorのテスト"""

    def test_creation(self):
        """ValidationErrorの作成"""
        exc = ValidationError(detail="Invalid input")
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.detail == "Invalid input"
        assert exc.error_type == "validation_error"

    def test_with_field(self):
        """フィールド指定ありの作成"""
        exc = ValidationError(detail="Invalid email", field="email")
        assert exc.field == "email"
        assert exc.detail == "Invalid email"


@pytest.mark.unit
class TestRateLimitError:
    """RateLimitErrorのテスト"""

    def test_creation(self):
        """RateLimitErrorの作成"""
        exc = RateLimitError(retry_after=60)
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "60" in exc.detail
        assert exc.error_type == "rate_limit_error"
        assert exc.headers["Retry-After"] == "60"

    def test_various_retry_values(self):
        """様々なretry_after値でのテスト"""
        for retry_value in [10, 30, 300, 3600]:
            exc = RateLimitError(retry_after=retry_value)
            assert exc.headers["Retry-After"] == str(retry_value)
            assert str(retry_value) in exc.detail
