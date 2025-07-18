"""
APIスキーマ。
APIリクエストとレスポンスのデータモデルを定義します。
"""

from pydantic import BaseModel, Field


class ContentRequest(BaseModel):
    """
    コンテンツリクエスト。
    
    Parameters
    ----------
    date : str, optional
        取得する日付（YYYY-MM-DD形式）。
    """

    date: str | None = Field(None, description="取得する日付（YYYY-MM-DD形式）")


class ContentItem(BaseModel):
    """
    コンテンツ項目。
    
    Parameters
    ----------
    title : str
        タイトル。
    content : str
        コンテンツ本文。
    url : str, optional
        関連URL。
    source : str
        ソース（reddit, hackernews, github, techfeed, paper）。
    """

    title: str = Field(..., description="タイトル")
    content: str = Field(..., description="コンテンツ本文")
    url: str | None = Field(None, description="関連URL")
    source: str = Field(
        ..., description="ソース（reddit, hackernews, github, techfeed, paper）"
    )


class ContentResponse(BaseModel):
    """
    コンテンツレスポンス。
    
    Parameters
    ----------
    items : List[ContentItem]
        コンテンツ項目のリスト。
    """

    items: list[ContentItem] = Field(..., description="コンテンツ項目のリスト")


class WeatherResponse(BaseModel):
    """
    天気レスポンス。
    
    Parameters
    ----------
    temperature : float
        気温（摂氏）。
    icon : str
        天気アイコン。
    """

    temperature: float = Field(..., description="気温（摂氏）")
    icon: str = Field(..., description="天気アイコン")


class ChatMessage(BaseModel):
    """
    チャットメッセージ。
    
    Parameters
    ----------
    role : str
        メッセージの役割（'user' または 'assistant'）。
    content : str
        メッセージの内容。
    """

    role: str
    content: str


class ChatRequest(BaseModel):
    """
    チャットリクエスト。
    
    Parameters
    ----------
    topic_id : str
        トピックID。
    message : str
        ユーザーメッセージ。
    chat_history : List[Dict[str, str]]
        チャット履歴。
    markdown : str, optional
        関連するマークダウンコンテキスト。
    """

    topic_id: str = Field(..., description="トピックID")
    message: str = Field(..., description="ユーザーメッセージ")
    chat_history: list[dict[str, str]] = Field(
        default_factory=list, description="チャット履歴"
    )
    markdown: str | None = Field("", description="関連するマークダウンコンテキスト")


class ChatResponse(BaseModel):
    """
    チャットレスポンス。
    
    Parameters
    ----------
    response : str
        アシスタントからのレスポンス。
    """

    response: str = Field(..., description="アシスタントからのレスポンス")
