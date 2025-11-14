"""OpenAI GPT APIクライアント。"""

import asyncio
import inspect
import json
import os
import warnings
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
    OpenAI GPT APIとの通信を担当するクライアントクラス。

    Parameters
    ----------
    api_key : str, optional
        OpenAI APIキー。指定しない場合は環境変数から取得。
    model : str, optional
        使用するモデル名。指定しない場合は環境変数から取得。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        GPTClientを初期化します。

        Parameters
        ----------
        api_key : str, optional
            OpenAI APIキー。指定しない場合は環境変数から取得。
        model : str, optional
            使用するモデル名。指定しない場合は環境変数から取得。
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY must be provided or set as an environment variable"
            )

        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-nano")
        if not self.model:
            raise ValueError(
                "OPENAI_MODEL must be provided or set as an environment variable"
            )

        # OpenAI APIの設定
        self.client = openai.OpenAI(api_key=self.api_key)

        # トークンエンコーダーの初期化
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

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

    def _messages_to_responses_input(
        self, messages: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """
        Chat CompletionsのmessagesをResponses APIのinput形式へ変換します。
        """
        inputs: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            inputs.append(
                {
                    "role": role,
                    "content": [{"type": "input_text", "text": content}],
                }
            )
        return inputs

    def _extract_text_from_response(self, resp: Any) -> str:
        """
        Responses APIのレスポンスからテキスト出力を抽出します。
        output_textが無い場合にフォールバックとして使用。
        """
        # まずはSDKのプロパティを試す
        text = getattr(resp, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text

        # 次に辞書化して走査
        data = None
        for attr in ("model_dump", "dict"):
            try:
                meth = getattr(resp, attr)
                if callable(meth):
                    data = meth()
                    break
            except Exception:
                pass
        if data is None:
            try:
                data = resp.__dict__
            except Exception:
                return ""

        def collect(obj: Any) -> list[str]:
            out: list[str] = []
            if isinstance(obj, dict):
                # 典型: {type: 'output_text', text: '...'}
                typ = obj.get("type")
                if (typ and "text" in str(typ)) and isinstance(obj.get("text"), str):
                    out.append(obj["text"])
                for v in obj.values():
                    out.extend(collect(v))
            elif isinstance(obj, list):
                for v in obj:
                    out.extend(collect(v))
            return out

        pieces = [p for p in collect(data) if isinstance(p, str) and p.strip()]
        return "\n".join(pieces)

    def _call_gpt5(
        self, prompt: str, system_instruction: str | None, max_tokens: int
    ) -> str:
        """
        GPT-5系モデル用のResponses API呼び出し。
        必要に応じてprevious_response_idで継続生成を試みます。
        """
        effort = "minimal"
        prev_id: str | None = None
        output_text = ""

        for attempt in range(3):
            params: dict[str, Any] = {
                "model": self.model,
                "max_output_tokens": max_tokens * (2 if attempt else 1),
            }
            if prev_id:
                params["previous_response_id"] = prev_id
            else:
                params["input"] = [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                ]
                params["reasoning"] = {"effort": effort}
                params["text"] = {"verbosity": "medium"}
                if system_instruction:
                    params["instructions"] = system_instruction

            resp = self.client.responses.create(**params)
            output_text = getattr(
                resp, "output_text", ""
            ) or self._extract_text_from_response(resp)
            if output_text:
                return output_text
            prev_id = getattr(resp, "id", None)

        return output_text

    def _call_gpt5_chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None,
        max_tokens: int,
    ) -> str:
        """
        GPT-5系向けにチャット形式のmessagesをResponses APIで処理。
        必要に応じてprevious_response_idで継続生成。
        """
        effort = "minimal"
        prev_id: str | None = None
        output_text = ""

        for attempt in range(3):
            params: dict[str, Any] = {
                "model": self.model,
                "max_output_tokens": max_tokens * (2 if attempt else 1),
            }
            if prev_id:
                params["previous_response_id"] = prev_id
            else:
                params["input"] = self._messages_to_responses_input(messages)
                params["reasoning"] = {"effort": effort}
                params["text"] = {"verbosity": "medium"}
                if system_instruction:
                    params["instructions"] = system_instruction

            resp = self.client.responses.create(**params)
            output_text = getattr(
                resp, "output_text", ""
            ) or self._extract_text_from_response(resp)
            if output_text:
                return output_text
            prev_id = getattr(resp, "id", None)

        return output_text

    def _is_gpt5_model(self) -> bool:
        """
        GPT-5モデルかどうかを判定します。

        GPT-5モデルはtemperature、top_p、logprobsをサポートせず、
        代わりにreasoning_effortとverbosityを使用します。
        """
        return self.model.lower().startswith("gpt-5")

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
            生成の多様性を制御するパラメータ（非推奨：GPT-5では無視されます）。
        max_tokens : int, default=1000
            生成するトークンの最大数。

        Returns
        -------
        str
            生成されたテキスト。
        """
        if temperature != 0.7:
            warnings.warn(
                "temperature parameter is ignored for GPT-5 models and will be removed in a future release",
                DeprecationWarning,
                stacklevel=2,
            )

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

        # GPT-5 Responses API を使用
        output_text = self._call_gpt5(prompt, system_instruction, max_tokens)

        # 出力トークン数の計算
        output_tokens = self._count_tokens(output_text)

        # 料金計算
        cost = self._calculate_cost(input_tokens, output_tokens)

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
            生成の多様性を制御するパラメータ（非推奨：GPT-5では無視されます）。
        max_tokens : int, default=1000
            生成するトークンの最大数。

        Returns
        -------
        str
            AIの応答。
        """
        if temperature != 0.7:
            warnings.warn(
                "temperature parameter is ignored for GPT-5 models and will be removed in a future release",
                DeprecationWarning,
                stacklevel=2,
            )

        chat_session["messages"].append({"role": "user", "content": message})

        # トークン数の計算
        service = self._get_calling_service()
        input_text = ""
        for msg in chat_session["messages"]:
            input_text += msg["content"] + " "
        input_tokens = self._count_tokens(input_text.strip())

        # GPT-5 Responses API を使用
        assistant_message = self._call_gpt5_chat(
            chat_session["messages"], None, max_tokens
        )
        output_tokens = self._count_tokens(assistant_message)

        # 料金計算
        cost = self._calculate_cost(input_tokens, output_tokens)

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
            生成の多様性を制御するパラメータ（非推奨：GPT-5では無視されます）。
        max_tokens : int, default=1000
            生成するトークンの最大数。

        Returns
        -------
        str
            AIの応答。
        """
        if temperature != 0.7:
            warnings.warn(
                "temperature parameter is ignored for GPT-5 models and will be removed in a future release",
                DeprecationWarning,
                stacklevel=2,
            )

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

        # GPT-5 Responses API を使用
        output_text = self._call_gpt5_chat(
            messages, system_instruction=None, max_tokens=max_tokens
        )
        output_tokens = self._count_tokens(output_text)

        # 料金計算
        cost = self._calculate_cost(input_tokens, output_tokens)

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
            生成の多様性を制御するパラメータ（非推奨：GPT-5では無視されます）。
        max_tokens : int, default=1000
            生成するトークンの最大数。

        Returns
        -------
        str
            AIの応答。
        """
        if temperature != 0.7:
            warnings.warn(
                "temperature parameter is ignored for GPT-5 models and will be removed in a future release",
                DeprecationWarning,
                stacklevel=2,
            )

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

        # GPT-5 Responses API を使用
        output_text = self._call_gpt5_chat(
            all_messages, system_instruction=None, max_tokens=max_tokens
        )
        output_tokens = self._count_tokens(output_text)

        # 料金計算
        cost = self._calculate_cost(input_tokens, output_tokens)

        return output_text
