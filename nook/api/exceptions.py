from typing import Any

from fastapi import HTTPException, status


class NookHTTPException(HTTPException):
    """Nook用のHTTPException基底クラス"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: str,
        headers: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_type = error_type


class NotFoundError(NookHTTPException):
    """リソースが見つからない場合の例外"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with identifier '{identifier}' not found",
            error_type="not_found",
        )


class AuthenticationError(NookHTTPException):
    """認証エラー"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_type="authentication_error",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(NookHTTPException):
    """認可エラー"""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="authorization_error",
        )


class ValidationError(NookHTTPException):
    """バリデーションエラー"""

    def __init__(self, detail: str, field: str | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
            error_type="validation_error",
        )
        self.field = field


class RateLimitError(NookHTTPException):
    """レート制限エラー"""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again after {retry_after} seconds",
            error_type="rate_limit_error",
            headers={"Retry-After": str(retry_after)},
        )
