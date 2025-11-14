"""
チャットAPIルーター。
チャット機能のエンドポイントを提供します。
"""

import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from nook.api.models.schemas import ChatRequest, ChatResponse
from nook.common.gpt_client import GPTClient

# 環境変数の読み込み
load_dotenv()

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    チャットメッセージを処理し、レスポンスを返します。

    Parameters
    ----------
    request : ChatRequest
        チャットリクエスト

    Returns
    -------
    ChatResponse
        チャットレスポンス

    Raises
    ------
    HTTPException
        APIキーが設定されていない場合や、APIリクエストに失敗した場合
    """
    # APIキーの確認
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # デモモード: APIキーがない場合はダミーレスポンスを返す
        return ChatResponse(
            response="申し訳ありませんが、OPENAI_API_KEYが設定されていないため、実際の応答ができません。環境変数を設定してください。"
        )

    try:
        # GPTクライアントの初期化
        client = GPTClient(api_key=api_key)

        # チャット履歴の整形
        formatted_history = []
        for msg in request.chat_history:
            formatted_history.append(
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            )

        # システムプロンプトの作成
        system_prompt = "あなたは親切なアシスタントです。ユーザーが提供したコンテンツについて質問に答えてください。"
        if request.markdown:
            system_prompt += (
                f"\n\n以下のコンテンツに基づいて回答してください:\n\n{request.markdown}"
            )

        # GPT APIを呼び出し
        response = client.chat(
            messages=formatted_history,
            system=system_prompt,
            temperature=0.7,
            max_tokens=1000,
        )

        return ChatResponse(response=response)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"チャットリクエストの処理中にエラーが発生しました: {str(e)}",
        ) from e
