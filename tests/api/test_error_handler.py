from __future__ import annotations

from pathlib import Path
import sys
import json

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
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
    }
    return Request(scope)


def _get_json(response: JSONResponse):
    return json.loads(response.body.decode())


def assert_error_response(
    response: JSONResponse,
    expected_status: int,
    expected_type: str,
):
    assert response.status_code == expected_status
    data = _get_json(response)
    assert data["error"]["type"] == expected_type
    assert data["error"]["status_code"] == expected_status
    assert isinstance(data["error"]["error_id"], str)
    assert isinstance(data["error"]["timestamp"], str)


def test_handle_exception_api_exception_includes_response_body():
    request = make_request()
    exc = APIException("boom", status_code=502, response_body="body")

    response = handle_exception(exc, request)

    assert_error_response(response, status.HTTP_502_BAD_GATEWAY, "api_error")
    data = _get_json(response)
    assert data["error"]["details"]["response_body"] == "body"


def test_handle_exception_configuration_exception():
    request = make_request()
    exc = ConfigurationException("config bad")

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "configuration_error"
    )


def test_handle_exception_data_exception():
    request = make_request()
    exc = DataException("bad data")

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_422_UNPROCESSABLE_ENTITY, "data_error"
    )


def test_handle_exception_service_exception():
    request = make_request()
    exc = ServiceException("service error")

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_503_SERVICE_UNAVAILABLE, "service_error"
    )


def test_handle_exception_nook_exception():
    request = make_request()
    exc = NookException("app error")

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "application_error"
    )


def test_handle_exception_request_validation_error():
    request = make_request()
    exc = RequestValidationError(
        [{"loc": ("body", "field"), "msg": "bad", "type": "value_error"}]
    )

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error"
    )
    data = _get_json(response)
    assert "errors" in data["error"]["details"]


def test_handle_exception_starlette_http_exception():
    request = make_request()
    exc = StarletteHTTPException(status_code=404, detail="not found")

    response = handle_exception(exc, request)

    assert_error_response(response, status.HTTP_404_NOT_FOUND, "http_error")


def test_handle_exception_unexpected_exception():
    request = make_request()
    exc = RuntimeError("boom")

    response = handle_exception(exc, request)

    assert_error_response(
        response, status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error"
    )


@pytest.mark.asyncio
async def test_error_handler_middleware_passes_through_response():
    request = make_request()

    async def call_next(req: Request):
        return JSONResponse({"ok": True})

    response = await error_handler_middleware(request, call_next)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert _get_json(response) == {"ok": True}


@pytest.mark.asyncio
async def test_error_handler_middleware_uses_handle_exception_on_error():
    request = make_request()

    async def call_next(req: Request):
        raise DataException("bad data")

    response = await error_handler_middleware(request, call_next)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = _get_json(response)
    assert data["error"]["type"] == "data_error"
