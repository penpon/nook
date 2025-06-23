"""GPT-4.1-nano API（OpenAI）クライアント。"""

import os
from typing import Dict, List, Optional, Union, Any

import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class GPTClient:
    """
    GPT-4.1-nano API（OpenAI）との通信を担当するクライアントクラス。
    
    Parameters
    ----------
    api_key : str, optional
        OpenAI APIキー。指定しない場合は環境変数から取得。
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        GPTClientを初期化します。
        
        Parameters
        ----------
        api_key : str, optional
            OpenAI APIキー。指定しない場合は環境変数から取得。
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be provided or set as an environment variable")
        
        # OpenAI APIの設定
        self.client = openai.OpenAI(api_key=self.api_key)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_content(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        テキストを生成します。
        
        Parameters
        ----------
        prompt : str
            生成のためのプロンプト。
        system_instruction : str, optional
            システム指示。
        temperature : float, default=0.7
            生成の多様性を制御するパラメータ。
        max_tokens : int, default=1000
            生成するトークンの最大数。
            
        Returns
        -------
        str
            生成されたテキスト。
        """
        messages = []
        
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        messages.append({"role": "user", "content": prompt})
        
        # 新しいOpenAI APIの使用方法
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_chat(
        self,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        チャットセッションを作成します。
        
        Parameters
        ----------
        system_instruction : str, optional
            システム指示。
            
        Returns
        -------
        Dict[str, Any]
            チャットセッション情報。
        """
        messages = []
        
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        return {"messages": messages}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def send_message(
        self,
        chat_session: Dict[str, Any],
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        チャットセッションにメッセージを送信します。
        
        Parameters
        ----------
        chat_session : Dict[str, Any]
            チャットセッション情報。
        message : str
            送信するメッセージ。
        temperature : float, default=0.7
            生成の多様性を制御するパラメータ。
        max_tokens : int, default=1000
            生成するトークンの最大数。
            
        Returns
        -------
        str
            AIの応答。
        """
        chat_session["messages"].append({"role": "user", "content": message})
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=chat_session["messages"],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        assistant_message = response.choices[0].message.content
        chat_session["messages"].append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat_with_search(
        self,
        message: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        検索機能付きチャットを実行します。
        
        Parameters
        ----------
        message : str
            ユーザーメッセージ。
        context : str
            検索コンテキスト。
        chat_history : List[Dict[str, str]], optional
            チャット履歴。
        temperature : float, default=0.7
            生成の多様性を制御するパラメータ。
        max_tokens : int, default=1000
            生成するトークンの最大数。
            
        Returns
        -------
        str
            AIの応答。
        """
        system_instruction = """
        あなたは役立つアシスタントです。ユーザーの質問に対して、提供されたコンテキストに基づいて回答してください。
        コンテキストに情報がない場合は、その旨を正直に伝えてください。
        """
        
        messages = [{"role": "system", "content": system_instruction}]
        
        if chat_history:
            messages.extend(chat_history)
        
        messages.append({"role": "user", "content": f"コンテキスト: {context}\n\n質問: {message}"})
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
        
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        チャットを実行します。
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            メッセージのリスト。
        system : str, optional
            システム指示。
        temperature : float, default=0.7
            生成の多様性を制御するパラメータ。
        max_tokens : int, default=1000
            生成するトークンの最大数。
            
        Returns
        -------
        str
            AIの応答。
        """
        all_messages = []
        
        if system:
            all_messages.append({"role": "system", "content": system})
        
        all_messages.extend(messages)
        
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content 