import functools
import logging
from collections.abc import Callable
from typing import TypeVar

from nook.core.errors.exceptions import APIException, ServiceException

T = TypeVar("T")


class ServiceErrorHandler:
    """サービス層のエラーハンドリング"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)

    def handle_api_error(self, api_name: str):
        """API呼び出しのエラーハンドリングデコレータ"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        "API call failed",
                        extra={
                            "service": self.service_name,
                            "api": api_name,
                            "function": func.__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

                    # 特定のAPIエラーを変換
                    if hasattr(e, "response"):
                        status_code = getattr(e.response, "status_code", None)
                        response_body = getattr(e.response, "text", None)

                        raise APIException(
                            f"{api_name} API error: {str(e)}",
                            status_code=status_code,
                            response_body=response_body,
                        ) from e
                    else:
                        raise APIException(f"{api_name} API error: {str(e)}") from e

            return wrapper

        return decorator

    def handle_data_processing(self, operation: str):
        """データ処理のエラーハンドリングデコレータ"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        "Data processing failed",
                        extra={
                            "service": self.service_name,
                            "operation": operation,
                            "function": func.__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

                    raise ServiceException(f"Failed to {operation}: {str(e)}") from e

            return wrapper

        return decorator
