"""
APIクライアント。
FastAPI バックエンドとの通信を担当します。
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests


class APIClient:
    """
    FastAPI バックエンドとの通信を担当するクラス。
    
    Parameters
    ----------
    base_url : str
        APIのベースURL。
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        APIClientを初期化します。
        
        Parameters
        ----------
        base_url : str, default="http://localhost:8000"
            APIのベースURL。
        """
        self.base_url = base_url
    
    def get_content(self, source: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        コンテンツを取得します。
        
        Parameters
        ----------
        source : str
            データソース（reddit, hackernews, github, techfeed, paper, all）。
        date : str, optional
            表示する日付（YYYY-MM-DD形式）。
            
        Returns
        -------
        Dict[str, Any]
            コンテンツデータ。
            
        Raises
        ------
        Exception
            APIリクエストに失敗した場合。
        """
        url = f"{self.base_url}/api/content/{source}"
        params = {}
        if date:
            params["date"] = date
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"コンテンツの取得に失敗しました: {str(e)}")
    
    def get_weather(self) -> Dict[str, Any]:
        """
        天気データを取得します。
        
        Returns
        -------
        Dict[str, Any]
            天気データ。
            
        Raises
        ------
        Exception
            APIリクエストに失敗した場合。
        """
        url = f"{self.base_url}/api/weather"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"天気データの取得に失敗しました: {str(e)}")
    
    def send_chat_message(
        self, 
        topic_id: str, 
        message: str, 
        chat_history: List[Dict[str, str]], 
        markdown: str = ""
    ) -> Dict[str, Any]:
        """
        チャットメッセージを送信します。
        
        Parameters
        ----------
        topic_id : str
            トピックID。
        message : str
            ユーザーメッセージ。
        chat_history : List[Dict[str, str]]
            チャット履歴。
        markdown : str, default=""
            関連するマークダウンコンテキスト。
            
        Returns
        -------
        Dict[str, Any]
            アシスタントからのレスポンス。
            
        Raises
        ------
        Exception
            APIリクエストに失敗した場合。
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "topic_id": topic_id,
            "message": message,
            "chat_history": chat_history,
            "markdown": markdown
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"チャットメッセージの送信に失敗しました: {str(e)}") 