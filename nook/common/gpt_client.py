"""GPT-4.1-nano API（OpenAI）クライアント。"""

import asyncio
import inspect
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import openai
import tiktoken
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# 環境変数の読み込み
load_dotenv()

# 料金設定（USD per 1M tokens）
PRICING = {"input": 0.20, "cached_input": 0.05, "output": 0.80}


class GPTClient:
    """
    GPT-4.1-nano API（OpenAI）との通信を担当するクライアントクラス。
    
    Parameters
    ----------
    api_key : str, optional
        OpenAI APIキー。指定しない場合は環境変数から取得。
    """

    def __init__(self, api_key: str | None = None):
        """
        GPTClientを初期化します。
        
        Parameters
        ----------
        api_key : str, optional
            OpenAI APIキー。指定しない場合は環境変数から取得。
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY must be provided or set as an environment variable"
            )

        # OpenAI APIの設定
        self.client = openai.OpenAI(api_key=self.api_key)

        # トークンエンコーダーの初期化
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        # ログファイルパスの設定
        self.log_file = Path("data/api_usage/llm_usage_log.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 累計コストの管理
        self.cumulative_cost = self._load_cumulative_cost()

    def _count_tokens(self, text: str) -> int:
        """テキストのトークン数を計算します。"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            return 0

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """料金を計算します。"""
        input_cost = (input_tokens / 1_000_000) * PRICING["input"]
        output_cost = (output_tokens / 1_000_000) * PRICING["output"]
        return input_cost + output_cost

    def _get_calling_service(self) -> str:
        """呼び出し元のサービス名を取得します。"""
        try:
            frame = inspect.currentframe()
            while frame:
                frame = frame.f_back
                if frame and frame.f_code.co_filename:
                    filepath = Path(frame.f_code.co_filename)
                    # services/ディレクトリ内のファイルを検出
                    if "services" in filepath.parts:
                        # services/の次のディレクトリ名をサービス名として使用
                        service_idx = filepath.parts.index("services")
                        if service_idx + 1 < len(filepath.parts):
                            service_name = filepath.parts[service_idx + 1]
                            # 特殊ケースの処理
                            if service_name in [
                                "run_services.py",
                                "run_services_sync.py",
                            ]:
                                continue
                            # __pycache__や.pyファイルを除外
                            if service_name.startswith("__") or service_name.endswith(
                                ".py"
                            ):
                                continue
                            return service_name
            # services/ディレクトリ内でない場合はunknownを返す
            return "unknown"
        except Exception:
            return "unknown"

    def _load_cumulative_cost(self) -> float:
        """累計コストを読み込みます。"""
        if not self.log_file.exists():
            return 0.0

        try:
            with open(self.log_file, encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if last_line:
                        last_record = json.loads(last_line)
                        return last_record.get("cumulative_cost_usd", 0.0)
        except Exception:
            pass

        return 0.0

    def _log_usage(
        self,
        service: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ):
        """使用量をログに記録します。"""
        try:
            self.cumulative_cost += cost

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "service": service,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "cumulative_cost_usd": self.cumulative_cost,
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Warning: Failed to log API usage: {e}")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_content(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        service_name: str | None = None,
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

        # トークン数の計算
        service = service_name or self._get_calling_service()
        input_text = ""
        for msg in messages:
            input_text += msg["content"] + " "
        input_tokens = self._count_tokens(input_text.strip())

        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 出力トークン数の計算
        output_text = response.choices[0].message.content
        output_tokens = self._count_tokens(output_text)

        # 料金計算とログ記録
        cost = self._calculate_cost(input_tokens, output_tokens)
        self._log_usage(service, "gpt-4.1-nano", input_tokens, output_tokens, cost)

        return output_text

    async def generate_async(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        service_name: str | None = None,
    ) -> str:
        """
        非同期でテキストを生成します。
        
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
        # 同期メソッドを非同期で実行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_content,
            prompt,
            system_instruction,
            temperature,
            max_tokens,
            service_name,
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def create_chat(self, system_instruction: str | None = None) -> dict[str, Any]:
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

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def send_message(
        self,
        chat_session: dict[str, Any],
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
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

        # トークン数の計算
        service = self._get_calling_service()
        input_text = ""
        for msg in chat_session["messages"]:
            input_text += msg["content"] + " "
        input_tokens = self._count_tokens(input_text.strip())

        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=chat_session["messages"],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        assistant_message = response.choices[0].message.content
        output_tokens = self._count_tokens(assistant_message)

        # 料金計算とログ記録
        cost = self._calculate_cost(input_tokens, output_tokens)
        self._log_usage(service, "gpt-4.1-nano", input_tokens, output_tokens, cost)

        chat_session["messages"].append(
            {"role": "assistant", "content": assistant_message}
        )

        return assistant_message

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat_with_search(
        self,
        message: str,
        context: str,
        chat_history: list[dict[str, str]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
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

        messages.append(
            {"role": "user", "content": f"コンテキスト: {context}\n\n質問: {message}"}
        )

        # トークン数の計算
        service = self._get_calling_service()
        input_text = ""
        for msg in messages:
            input_text += msg["content"] + " "
        input_tokens = self._count_tokens(input_text.strip())

        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 出力トークン数の計算
        output_text = response.choices[0].message.content
        output_tokens = self._count_tokens(output_text)

        # 料金計算とログ記録
        cost = self._calculate_cost(input_tokens, output_tokens)
        self._log_usage(service, "gpt-4.1-nano", input_tokens, output_tokens, cost)

        return output_text

    def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
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

        # トークン数の計算
        service = self._get_calling_service()
        input_text = ""
        for msg in all_messages:
            input_text += msg["content"] + " "
        input_tokens = self._count_tokens(input_text.strip())

        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 出力トークン数の計算
        output_text = response.choices[0].message.content
        output_tokens = self._count_tokens(output_text)

        # 料金計算とログ記録
        cost = self._calculate_cost(input_tokens, output_tokens)
        self._log_usage(service, "gpt-4.1-nano", input_tokens, output_tokens, cost)

        return output_text
