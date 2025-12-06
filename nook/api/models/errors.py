from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class ErrorDetail(BaseModel):
    """エラーの詳細情報"""

    field: str | None = Field(None, description="エラーが発生したフィールド")
    message: str = Field(..., description="エラーメッセージ")
    code: str | None = Field(None, description="エラーコード")


class ErrorResponse(BaseModel):
    """APIエラーレスポンス"""

    model_config = ConfigDict(
        json_schema_extra={
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
                        "code": "value_error.number.not_ge",
                    }
                ],
            }
        }
    )

    type: str = Field(..., description="エラータイプ")
    message: str = Field(..., description="エラーメッセージ")
    error_id: str = Field(..., description="エラー追跡用ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="エラー発生時刻"
    )
    status_code: int = Field(..., description="HTTPステータスコード")
    details: dict[str, Any] | list[ErrorDetail] | None = Field(
        None, description="追加の詳細情報"
    )
