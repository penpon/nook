"""APIスキーマ。
APIリクエストとレスポンスのデータモデルを定義します。
"""

from pydantic import BaseModel, Field


class ContentRequest(BaseModel):
    """コンテンツリクエスト。

    Parameters
    ----------
    date : str, optional
        取得する日付（YYYY-MM-DD形式）。

    """

    date: str | None = Field(None, description="取得する日付（YYYY-MM-DD形式）")


class ContentItem(BaseModel):
    """コンテンツ項目。

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
    source: str = Field(..., description="ソース（reddit, hackernews, github, techfeed, paper）")


class ContentResponse(BaseModel):
    """コンテンツレスポンス。

    Parameters
    ----------
    items : List[ContentItem]
        コンテンツ項目のリスト。

    """

    items: list[ContentItem] = Field(..., description="コンテンツ項目のリスト")


class WeatherResponse(BaseModel):
    """天気レスポンス。

    Parameters
    ----------
    temperature : float
        気温（摂氏）。
    icon : str
        天気アイコン。

    """

    temperature: float = Field(..., description="気温（摂氏）")
    icon: str = Field(..., description="天気アイコン")
