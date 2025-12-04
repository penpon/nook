from __future__ import annotations

from pathlib import Path
import sys
import json
from typing import Any

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.middleware.error_handler import (
    error_handler_middleware,
    handle_exception,
)
from nook.common.exceptions import (
    APIException,
    ConfigurationException,
    DataException,
    NookException,
    ServiceException,
)


def make_request(path: str = "/test") -> Request:
    """Create a FastAPI Request object for middleware testing.

    Args:
        path: Request path for the simulated request.

    Returns:
        Request: Configured FastAPI request instance.
    """

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
    }
    return Request(scope)


def _get_json(response: JSONResponse) -> dict[str, Any]:
    """Decode JSON data from a FastAPI response.

    Args:
        response: JSONResponse returned by handler.

    Returns:
        dict[str, Any]: Parsed JSON payload.
    """

    return json.loads(response.body.decode())


def assert_error_response(
    response: JSONResponse,
    expected_status: int,
    expected_type: str,
) -> None:
    """Assert the error response payload matches expectation.

    Args:
        response: JSONResponse returned from handler.
        expected_status: Expected HTTP status code.
        expected_type: Expected custom error type.
    """

    assert response.status_code == expected_status
    data = _get_json(response)
    assert data["error"]["type"] == expected_type
    assert data["error"]["status_code"] == expected_status
    assert isinstance(data["error"]["error_id"], str)
    assert isinstance(data["error"]["timestamp"], str)


def test_handle_exception_api_exception_includes_response_body() -> None:
    """Test APIException response body propagation.

    Given: APIException with response_body is raised.
    When: handle_exception processes the exception.
    Then: Response includes api_error type and response body detail.
    """

    # Given
    request = make_request()
    exc = APIException("boom", status_code=502, response_body="body")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(response, status.HTTP_502_BAD_GATEWAY, "api_error")
    data = _get_json(response)
    assert data["error"]["details"]["response_body"] == "body"


def test_handle_exception_configuration_exception() -> None:
    """Test ConfigurationException maps to configuration_error.

    Given: ConfigurationException is raised.
    When: handle_exception processes it.
    Then: Response is 500 with configuration_error type.
    """

    # Given
    request = make_request()
    exc = ConfigurationException("config bad")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "configuration_error"
    )


def test_handle_exception_data_exception() -> None:
    """Test DataException returns 422 data_error payload.

    Given: DataException is raised.
    When: handle_exception runs.
    Then: Response is 422 with data_error type.
    """

    # Given
    request = make_request()
    exc = DataException("bad data")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(response, status.HTTP_422_UNPROCESSABLE_CONTENT, "data_error")


def test_handle_exception_service_exception() -> None:
    """Test ServiceException returns 503 service_error payload.

    Given: ServiceException occurs.
    When: handle_exception handles it.
    Then: Response is 503 with service_error type.
    """

    # Given
    request = make_request()
    exc = ServiceException("service error")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(
        response, status.HTTP_503_SERVICE_UNAVAILABLE, "service_error"
    )


def test_handle_exception_nook_exception() -> None:
    """Test generic NookException maps to application_error.

    Given: NookException is raised.
    When: handle_exception handles it.
    Then: Response is 500 with application_error type.
    """

    # Given
    request = make_request()
    exc = NookException("app error")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "application_error"
    )


def test_handle_exception_request_validation_error() -> None:
    """Test RequestValidationError maps to validation_error.

    Given: FastAPI RequestValidationError is raised.
    When: handle_exception processes it.
    Then: Response returns 422 validation_error with details.
    """

    # Given
    request = make_request()
    exc = RequestValidationError(
        [{"loc": ("body", "field"), "msg": "bad", "type": "value_error"}]
    )

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(
        response, status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error"
    )
    data = _get_json(response)
    assert "errors" in data["error"]["details"]


def test_handle_exception_starlette_http_exception() -> None:
    """Test Starlette HTTPException maps to http_error.

    Given: Starlette HTTPException is raised.
    When: handle_exception handles it.
    Then: Response contains http_error with matching status.
    """

    # Given
    request = make_request()
    exc = StarletteHTTPException(status_code=404, detail="not found")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(response, status.HTTP_404_NOT_FOUND, "http_error")


def test_handle_exception_unexpected_exception() -> None:
    """Test unexpected exception returns internal_error type.

    Given: RuntimeError occurs.
    When: handle_exception handles it.
    Then: Response is 500 internal_error.
    """

    # Given
    request = make_request()
    exc = RuntimeError("boom")

    # When
    response = handle_exception(exc, request)

    # Then
    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error"
    )


@pytest.mark.asyncio
async def test_error_handler_middleware_passes_through_response() -> None:
    """Test middleware returns downstream response unchanged.

    Given: call_next returns JSONResponse.
    When: middleware processes without errors.
    Then: Response passes through untouched.
    """

    # Given
    request = make_request()

    async def call_next(req: Request) -> JSONResponse:  # pragma: no cover - simple stub
        return JSONResponse({"ok": True})

    # When
    response = await error_handler_middleware(request, call_next)

    # Then
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert _get_json(response) == {"ok": True}


@pytest.mark.asyncio
async def test_error_handler_middleware_uses_handle_exception_on_error() -> None:
    """Test middleware converts raised exceptions via handle_exception.

    Given: call_next raises DataException.
    When: middleware executes.
    Then: Response becomes 422 data_error payload.
    """

    # Given
    request = make_request()

    async def call_next(req: Request) -> JSONResponse:  # pragma: no cover - stub
        raise DataException("bad data")

    # When
    response = await error_handler_middleware(request, call_next)

    # Then
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = _get_json(response)
    assert data["error"]["type"] == "data_error"
