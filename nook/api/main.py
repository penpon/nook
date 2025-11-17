"""
Nook APIのメインアプリケーション。
FastAPIを使用してAPIエンドポイントを提供します。
"""

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from nook.api.exceptions import NookHTTPException
from nook.api.middleware.error_handler import error_handler_middleware, handle_exception
from nook.api.models.errors import ErrorResponse
from nook.api.routers import content, weather
from nook.common.error_metrics import error_metrics

# 環境変数の読み込み
load_dotenv()

# FastAPIアプリケーションの作成
app = FastAPI(
    title="Nook API",
    description="パーソナル情報ハブのAPI",
    version="0.1.0",
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)

# エラーハンドリングミドルウェアの追加
app.middleware("http")(error_handler_middleware)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# エラーハンドラーの登録
@app.exception_handler(NookHTTPException)
async def nook_exception_handler(request: Request, exc: NookHTTPException):
    error_metrics.record_error(
        exc.error_type, {"status_code": exc.status_code, "detail": exc.detail}
    )

    return handle_exception(exc, request)


# ルーターの登録
app.include_router(content.router, prefix="/api")
app.include_router(weather.router, prefix="/api")


@app.get("/")
async def root():
    """
    ルートエンドポイント。

    Returns
    -------
    dict
        APIの基本情報。
    """
    return {
        "name": "Nook API",
        "version": "0.1.0",
        "description": "パーソナル情報ハブのAPI",
    }


@app.get("/health")
async def health():
    """
    ヘルスチェックエンドポイント。

    Returns
    -------
    dict
        ヘルスステータス。
    """
    return {"status": "healthy"}


@app.get("/api/health/errors", include_in_schema=False)
async def get_error_stats():
    """
    エラー統計を取得するエンドポイント。

    Returns
    -------
    dict
        過去60分間のエラー統計。
    """
    return error_metrics.get_error_stats()
