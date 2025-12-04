from __future__ import annotations

from pathlib import Path
import sys

from fastapi import status

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NookHTTPException,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


def test_nook_http_exception_base_fields():
    exc = NookHTTPException(
        status_code=418,
        detail="teapot",
        error_type="custom_error",
        headers={"X-Test": "1"},
    )

    assert exc.status_code == 418
    assert exc.detail == "teapot"
    assert exc.error_type == "custom_error"
    assert exc.headers.get("X-Test") == "1"


def test_not_found_error_populates_fields():
    exc = NotFoundError(resource="item", identifier="42")
    assert exc.status_code == status.HTTP_404_NOT_FOUND
    assert "item" in exc.detail
    assert "42" in exc.detail
    assert exc.error_type == "not_found"


def test_authentication_error_sets_bearer_header():
    exc = AuthenticationError()
    assert exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.error_type == "authentication_error"
    assert exc.headers.get("WWW-Authenticate") == "Bearer"


def test_authorization_error_has_forbidden_status():
    exc = AuthorizationError()
    assert exc.status_code == status.HTTP_403_FORBIDDEN
    assert exc.error_type == "authorization_error"


def test_validation_error_can_store_field_name():
    exc = ValidationError(detail="invalid", field="name")
    assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc.error_type == "validation_error"
    assert exc.field == "name"


def test_rate_limit_error_sets_retry_after_header():
    exc = RateLimitError(retry_after=10)
    assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert exc.error_type == "rate_limit_error"
    assert exc.headers.get("Retry-After") == "10"
