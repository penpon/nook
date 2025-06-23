# TASK-002: エラーハンドリングシステム構築

## 割り当て: backend

## 目的
統一されたエラーハンドリングシステムを構築し、アプリケーション全体でのエラー処理を標準化する。

## 背景
現在のコードベースでは：
- エラーハンドリングが各サービスでバラバラ
- 例外の種類が不明確
- エラーログの形式が統一されていない
- APIレスポンスのエラー形式が標準化されていない

## 実装内容

### 1. エラーハンドリングミドルウェア
**ファイル**: `nook/api/middleware/error_handler.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union, Dict, Any
import traceback
from datetime import datetime

from nook.common.exceptions import (
    NookException,
    APIException,
    ServiceException,
    ConfigurationException,
    DataException
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
    error_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    
    # エラーログの記録
    logger.error(
        f"Unhandled exception",
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # エラータイプに応じた処理
    if isinstance(exc, APIException):
        return create_error_response(
            status_code=exc.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="api_error",
            message=str(exc),
            error_id=error_id,
            details={"response_body": exc.response_body} if exc.response_body else None
        )
    
    elif isinstance(exc, ConfigurationException):
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="configuration_error",
            message="Configuration error occurred",
            error_id=error_id
        )
    
    elif isinstance(exc, DataException):
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="data_error",
            message=str(exc),
            error_id=error_id
        )
    
    elif isinstance(exc, ServiceException):
        return create_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="service_error",
            message=str(exc),
            error_id=error_id
        )
    
    elif isinstance(exc, NookException):
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="application_error",
            message=str(exc),
            error_id=error_id
        )
    
    elif isinstance(exc, RequestValidationError):
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="validation_error",
            message="Request validation failed",
            error_id=error_id,
            details={"errors": exc.errors()}
        )
    
    elif isinstance(exc, StarletteHTTPException):
        return create_error_response(
            status_code=exc.status_code,
            error_type="http_error",
            message=exc.detail,
            error_id=error_id
        )
    
    else:
        # 予期しないエラー
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="internal_error",
            message="An unexpected error occurred",
            error_id=error_id
        )


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    error_id: str,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """標準化されたエラーレスポンスを作成"""
    content = {
        "error": {
            "type": error_type,
            "message": message,
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
    }
    
    if details:
        content["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )
```

### 2. HTTPエラーレスポンスモデル
**ファイル**: `nook/api/models/errors.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ErrorDetail(BaseModel):
    """エラーの詳細情報"""
    field: Optional[str] = Field(None, description="エラーが発生したフィールド")
    message: str = Field(..., description="エラーメッセージ")
    code: Optional[str] = Field(None, description="エラーコード")


class ErrorResponse(BaseModel):
    """APIエラーレスポンス"""
    type: str = Field(..., description="エラータイプ")
    message: str = Field(..., description="エラーメッセージ")
    error_id: str = Field(..., description="エラー追跡用ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="エラー発生時刻")
    status_code: int = Field(..., description="HTTPステータスコード")
    details: Optional[Union[Dict[str, Any], List[ErrorDetail]]] = Field(None, description="追加の詳細情報")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "validation_error",
                "message": "Request validation failed",
                "error_id": "20240120123456789012",
                "timestamp": "2024-01-20T12:34:56.789012",
                "status_code": 422,
                "details": [
                    {
                        "field": "age",
                        "message": "ensure this value is greater than or equal to 18",
                        "code": "value_error.number.not_ge"
                    }
                ]
            }
        }
```

### 3. カスタムHTTPException
**ファイル**: `nook/api/exceptions.py`

```python
from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class NookHTTPException(HTTPException):
    """Nook用のHTTPException基底クラス"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_type = error_type


class NotFoundError(NookHTTPException):
    """リソースが見つからない場合の例外"""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with identifier '{identifier}' not found",
            error_type="not_found"
        )


class AuthenticationError(NookHTTPException):
    """認証エラー"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_type="authentication_error",
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(NookHTTPException):
    """認可エラー"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="authorization_error"
        )


class ValidationError(NookHTTPException):
    """バリデーションエラー"""
    
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_type="validation_error"
        )
        self.field = field


class RateLimitError(NookHTTPException):
    """レート制限エラー"""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again after {retry_after} seconds",
            error_type="rate_limit_error",
            headers={"Retry-After": str(retry_after)}
        )
```

### 4. サービス層のエラーハンドリング
**ファイル**: `nook/common/service_errors.py`

```python
from typing import Optional, Callable, TypeVar, Any
import functools
import logging
from datetime import datetime

from nook.common.exceptions import ServiceException, APIException


T = TypeVar('T')


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
                        f"API call failed",
                        extra={
                            "service": self.service_name,
                            "api": api_name,
                            "function": func.__name__,
                            "error": str(e)
                        },
                        exc_info=True
                    )
                    
                    # 特定のAPIエラーを変換
                    if hasattr(e, 'response'):
                        status_code = getattr(e.response, 'status_code', None)
                        response_body = getattr(e.response, 'text', None)
                        
                        raise APIException(
                            f"{api_name} API error: {str(e)}",
                            status_code=status_code,
                            response_body=response_body
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
                        f"Data processing failed",
                        extra={
                            "service": self.service_name,
                            "operation": operation,
                            "function": func.__name__,
                            "error": str(e)
                        },
                        exc_info=True
                    )
                    
                    raise ServiceException(
                        f"Failed to {operation}: {str(e)}"
                    ) from e
            
            return wrapper
        return decorator
```

### 5. エラー集約とモニタリング
**ファイル**: `nook/common/error_metrics.py`

```python
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import threading
import json


class ErrorMetrics:
    """エラーメトリクスの収集と集約"""
    
    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.errors: Dict[str, List[Tuple[datetime, Dict]]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def record_error(self, error_type: str, details: Dict):
        """エラーを記録"""
        with self.lock:
            now = datetime.utcnow()
            self.errors[error_type].append((now, details))
            
            # 古いエラーを削除
            cutoff = now - timedelta(minutes=self.window_minutes)
            self.errors[error_type] = [
                (ts, d) for ts, d in self.errors[error_type]
                if ts > cutoff
            ]
    
    def get_error_stats(self) -> Dict[str, Dict]:
        """エラー統計を取得"""
        with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=self.window_minutes)
            
            stats = {}
            for error_type, error_list in self.errors.items():
                recent_errors = [(ts, d) for ts, d in error_list if ts > cutoff]
                
                if recent_errors:
                    stats[error_type] = {
                        "count": len(recent_errors),
                        "first_occurrence": recent_errors[0][0].isoformat(),
                        "last_occurrence": recent_errors[-1][0].isoformat(),
                        "rate_per_minute": len(recent_errors) / self.window_minutes
                    }
            
            return stats
    
    def get_error_report(self) -> str:
        """エラーレポートを生成"""
        stats = self.get_error_stats()
        
        if not stats:
            return "No errors in the last {} minutes".format(self.window_minutes)
        
        report_lines = [
            f"Error Report (last {self.window_minutes} minutes)",
            "=" * 50
        ]
        
        for error_type, stat in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
            report_lines.extend([
                f"\nError Type: {error_type}",
                f"Count: {stat['count']}",
                f"Rate: {stat['rate_per_minute']:.2f} errors/minute",
                f"First: {stat['first_occurrence']}",
                f"Last: {stat['last_occurrence']}"
            ])
        
        return "\n".join(report_lines)


# グローバルインスタンス
error_metrics = ErrorMetrics()
```

### 6. FastAPIアプリケーションへの統合
**ファイル**: `nook/api/main.py` (更新部分)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nook.api.middleware.error_handler import error_handler_middleware
from nook.api.exceptions import NookHTTPException
from nook.common.error_metrics import error_metrics


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nook API",
        description="AI-powered content aggregation API",
        version="1.0.0",
        responses={
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    
    # ミドルウェアの追加
    app.middleware("http")(error_handler_middleware)
    
    # エラーハンドラーの登録
    @app.exception_handler(NookHTTPException)
    async def nook_exception_handler(request: Request, exc: NookHTTPException):
        error_metrics.record_error(exc.error_type, {
            "status_code": exc.status_code,
            "detail": exc.detail
        })
        
        return handle_exception(exc, request)
    
    # エラー統計エンドポイント
    @app.get("/api/health/errors", include_in_schema=False)
    async def get_error_stats():
        return error_metrics.get_error_stats()
    
    return app
```

## テスト要件

### ユニットテスト
**ファイル**: `tests/api/test_error_handling.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from nook.api.main import create_app
from nook.api.exceptions import NotFoundError, ValidationError
from nook.common.exceptions import APIException, ServiceException


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestErrorHandling:
    def test_not_found_error(self, client):
        """NotFoundErrorのテスト"""
        with patch('nook.api.routers.content.get_content') as mock:
            mock.side_effect = NotFoundError("Content", "123")
            
            response = client.get("/api/content/123")
            
            assert response.status_code == 404
            assert response.json()["error"]["type"] == "not_found"
            assert "Content with identifier '123' not found" in response.json()["error"]["message"]
    
    def test_validation_error(self, client):
        """ValidationErrorのテスト"""
        response = client.post("/api/content", json={"invalid": "data"})
        
        assert response.status_code == 422
        assert response.json()["error"]["type"] == "validation_error"
        assert "details" in response.json()["error"]
    
    def test_api_exception(self, client):
        """APIExceptionのテスト"""
        with patch('nook.api.routers.content.external_api_call') as mock:
            mock.side_effect = APIException("External API failed", status_code=503)
            
            response = client.get("/api/content/external")
            
            assert response.status_code == 503
            assert response.json()["error"]["type"] == "api_error"
    
    def test_unexpected_error(self, client):
        """予期しないエラーのテスト"""
        with patch('nook.api.routers.content.some_function') as mock:
            mock.side_effect = RuntimeError("Unexpected error")
            
            response = client.get("/api/content/test")
            
            assert response.status_code == 500
            assert response.json()["error"]["type"] == "internal_error"
            assert "error_id" in response.json()["error"]
```

### 統合テスト
**ファイル**: `tests/integration/test_error_flow.py`

```python
import pytest
import asyncio
from nook.common.service_errors import ServiceErrorHandler
from nook.common.exceptions import APIException, ServiceException


class TestServiceErrorFlow:
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """APIエラーハンドリングのフロー"""
        handler = ServiceErrorHandler("test_service")
        
        @handler.handle_api_error("TestAPI")
        async def failing_api_call():
            raise Exception("API call failed")
        
        with pytest.raises(APIException) as exc_info:
            await failing_api_call()
        
        assert "TestAPI API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_data_processing_error(self):
        """データ処理エラーのフロー"""
        handler = ServiceErrorHandler("test_service")
        
        @handler.handle_data_processing("parse data")
        async def failing_data_processing():
            raise ValueError("Invalid data format")
        
        with pytest.raises(ServiceException) as exc_info:
            await failing_data_processing()
        
        assert "Failed to parse data" in str(exc_info.value)
```

## 完了条件

1. すべてのエラーハンドリングコードが実装されていること
2. FastAPIアプリケーションに統合されていること
3. エラーレスポンスが標準化されていること
4. エラーメトリクスが収集されること
5. ユニットテストと統合テストが成功すること

## 注意事項

1. 既存のAPIエンドポイントとの互換性を保つ
2. エラーログに機密情報を含めない
3. 本番環境では詳細なエラー情報を隠蔽する
4. パフォーマンスへの影響を最小限にする

## 依存関係

- TASK-001の完了（基底クラスと共通モジュール）

## 期限

1日間