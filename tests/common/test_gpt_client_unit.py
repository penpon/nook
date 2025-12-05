from __future__ import annotations

import types
from pathlib import Path
import sys

import openai
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.gpt_client import GPTClient


class DummyEncoding:
    def encode(self, text: str):
        return list(text)


class DummyChatCompletions:
    def __init__(self):
        self.last_params: dict | None = None

    def create(self, **params):
        self.last_params = params
        message = types.SimpleNamespace(content="chat-output")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


class DummyResponses:
    def __init__(self):
        self.last_params: dict | None = None

    def create(self, **params):
        self.last_params = params
        return types.SimpleNamespace(
            output_text="responses-output",
            id=params.get("previous_response_id", "resp-id"),
            model_dump=lambda: {},
            dict=lambda: {},
        )


@pytest.fixture(autouse=True)
def patch_encoding(monkeypatch):
    monkeypatch.setattr(
        "nook.common.gpt_client.tiktoken.encoding_for_model",
        lambda model: DummyEncoding(),
    )
    monkeypatch.setattr(
        "nook.common.gpt_client.tiktoken.get_encoding",
        lambda name: DummyEncoding(),
    )


@pytest.fixture
def dummy_openai(monkeypatch):
    chat_completions = DummyChatCompletions()
    responses = DummyResponses()

    class DummyOpenAI:
        def __init__(self, api_key: str):
            self.chat = types.SimpleNamespace(completions=chat_completions)
            self.responses = responses

    monkeypatch.setattr(openai, "OpenAI", DummyOpenAI)
    return chat_completions, responses


@pytest.fixture
def client(dummy_openai):
    chat_completions, responses = dummy_openai
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")
    client.encoding = DummyEncoding()
    client.chat_completions = chat_completions
    client.responses = responses
    return client


def test_count_tokens_and_calculate_cost(client, monkeypatch):
    # Given: クライアントは通常のエンコーディングを使用
    # When: トークンカウントと料金計算を行う
    assert client._count_tokens("abc") == 3
    assert client._calculate_cost(1_000_000, 500_000) == pytest.approx(0.2 + 0.4)

    class FailingEncoding:
        def encode(self, text):
            raise RuntimeError("encoding failed")

    client.encoding = FailingEncoding()
    # Then: エンコード失敗時は0を返す
    assert client._count_tokens("won't matter") == 0


def test_messages_to_responses_input(client):
    # Given: system/userのメッセージリスト
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    # When: Responses API形式に変換
    converted = client._messages_to_responses_input(messages)
    # Then: 期待フォーマットで返却される
    assert converted == [
        {"role": "system", "content": [{"type": "input_text", "text": "sys"}]},
        {"role": "user", "content": [{"type": "input_text", "text": "hi"}]},
    ]


def test_supports_and_gpt5_detection(dummy_openai):
    # Given/When/Then: モデル名に応じてmax_completion_tokensとgpt5判定を確認
    assert GPTClient(api_key="k", model="gpt-5-abc")._supports_max_completion_tokens()
    assert GPTClient(
        api_key="k", model="gpt-4.1-mini"
    )._supports_max_completion_tokens()
    assert (
        GPTClient(api_key="k", model="gpt-3.5-turbo")._supports_max_completion_tokens()
        is False
    )
    assert GPTClient(api_key="k", model="gpt-5-xyz")._is_gpt5_model() is True
    assert GPTClient(api_key="k", model="gpt-4.1-mini")._is_gpt5_model() is False


def test_get_calling_service(monkeypatch, client):
    # Given: services配下から呼ばれたスタックフレームを用意
    service_frame = types.SimpleNamespace(
        f_back=None,
        f_code=types.SimpleNamespace(
            co_filename="/home/bob/nook/services/my_service/run.py"
        ),
    )
    caller_frame = types.SimpleNamespace(
        f_back=service_frame,
        f_code=types.SimpleNamespace(co_filename="/home/bob/nook/worker.py"),
    )

    monkeypatch.setattr(
        "nook.common.gpt_client.inspect.currentframe", lambda: caller_frame
    )

    # When/Then: サービス名を抽出できる
    assert client._get_calling_service() == "my_service"


def test_generate_content_uses_chat_completions_params(client):
    # Given: chat completionsに差し込むパラメータ
    result = client.generate_content(
        prompt="hello", system_instruction="sys", temperature=0.5, max_tokens=50
    )

    params = client.client.chat.completions.last_params
    # Then: SDK呼び出しのパラメータが期待通り
    assert result == "chat-output"
    assert params["model"] == "gpt-4.1-mini"
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][1]["content"] == "hello"
    assert params["temperature"] == 0.5
    assert params["max_completion_tokens"] == 50
    assert "max_tokens" not in params


def test_generate_content_calls_gpt5_path(monkeypatch, dummy_openai):
    # Given: gpt-5系モデルとモックのコール関数
    client = GPTClient(api_key="k", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    called = {}

    def fake_call(prompt, sys_inst, max_tokens):
        called["args"] = (prompt, sys_inst, max_tokens)
        return "gpt5-output"

    monkeypatch.setattr(client, "_call_gpt5", fake_call)

    # When: generate_contentを呼ぶ
    result = client.generate_content(prompt="p", system_instruction="s", max_tokens=10)
    # Then: gpt5パスが呼ばれ、引数が渡る
    assert result == "gpt5-output"
    assert called["args"] == ("p", "s", 10)


def test_chat_uses_system_and_max_completion_tokens(client):
    # Given: systemメッセージとmax_completion_tokens
    result = client.chat(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        temperature=0.2,
        max_tokens=30,
    )

    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][1]["content"] == "hi"
    assert params["max_completion_tokens"] == 30
    assert "max_tokens" not in params


def test_send_message_appends_and_returns_reply(client):
    # Given: システムメッセージのみを持つチャットセッション
    chat_session = {"messages": [{"role": "system", "content": "sys"}]}

    # When: 質問を送信
    reply = client.send_message(chat_session, "question", temperature=0.1, max_tokens=5)

    # Then: 応答が追加され、パラメータが期待通り
    assert reply == "chat-output"
    assert chat_session["messages"][-1]["role"] == "assistant"
    assert chat_session["messages"][-1]["content"] == "chat-output"
    params = client.client.chat.completions.last_params
    assert params["messages"][-2]["content"] == "question"
    assert params["max_completion_tokens"] == 5


def test_chat_with_search_uses_history(client):
    # Given: 既存履歴とコンテキスト付きメッセージ
    history = [{"role": "user", "content": "old"}]
    output = client.chat_with_search(
        message="new",
        context="ctx",
        chat_history=history,
        temperature=0.9,
        max_tokens=12,
    )

    # Then: システム・履歴・新メッセージが含まれ、max_completion_tokensを使用
    params = client.client.chat.completions.last_params
    assert output == "chat-output"
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][1]["content"] == "old"
    assert "ctx" in params["messages"][-1]["content"]
    assert params["max_completion_tokens"] == 12
