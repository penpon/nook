import logging
import traceback
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from nook.core.errors.exceptions import (
    APIException,
    ConfigurationException,
    DataException,
    NookException,
    ServiceException,
)

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """グローバルエラーハンドリングミドルウェア"""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        return handle_exception(exc, request)


def handle_exception(exc: Exception, request: Request) -> JSONResponse:
    """例外を処理してJSONレスポンスを返す"""
    error_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")

    # エラーログの記録
    logger.error(
        "Unhandled exception",
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # エラータイプに応じた処理
    if isinstance(exc, APIException):
        return create_error_response(
            status_code=exc.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="api_error",
            message=str(exc),
            error_id=error_id,
            details={"response_body": exc.response_body} if exc.response_body else None,
        )

    elif isinstance(exc, ConfigurationException):
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="configuration_error",
            message="Configuration error occurred",
            error_id=error_id,
        )

    elif isinstance(exc, DataException):
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_type="data_error",
            message=str(exc),
            error_id=error_id,
        )

    elif isinstance(exc, ServiceException):
        return create_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="service_error",
            message=str(exc),
            error_id=error_id,
        )

    elif isinstance(exc, NookException):
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="application_error",
            message=str(exc),
            error_id=error_id,
        )

    elif isinstance(exc, RequestValidationError):
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_type="validation_error",
            message="Request validation failed",
            error_id=error_id,
            details={"errors": exc.errors()},
        )

    elif isinstance(exc, StarletteHTTPException):
        return create_error_response(
            status_code=exc.status_code,
            error_type="http_error",
            message=exc.detail,
            error_id=error_id,
        )

    else:
        # 予期しないエラー
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="internal_error",
            message="An unexpected error occurred",
            error_id=error_id,
        )


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    error_id: str,
    details: dict[str, Any] = None,
) -> JSONResponse:
    """標準化されたエラーレスポンスを作成"""
    content = {
        "error": {
            "type": error_type,
            "message": message,
            "error_id": error_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "status_code": status_code,
        }
    }

    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)
