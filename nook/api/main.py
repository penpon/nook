"""
Nook APIのメインアプリケーション。
FastAPIを使用してAPIエンドポイントを提供します。
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from nook.api.routers import content, weather, chat

# 環境変数の読み込み
load_dotenv()

# FastAPIアプリケーションの作成
app = FastAPI(
    title="Nook API",
    description="パーソナル情報ハブのAPI",
    version="0.1.0"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(content.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

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
        "description": "パーソナル情報ハブのAPI"
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