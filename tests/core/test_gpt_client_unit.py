from __future__ import annotations

import sys
import types
from pathlib import Path

import openai
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.core.clients.gpt_client import GPTClient  # noqa: E402


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
        "nook.core.clients.gpt_client.tiktoken.encoding_for_model",
        lambda model: DummyEncoding(),
    )
    monkeypatch.setattr(
        "nook.core.clients.gpt_client.tiktoken.get_encoding",
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


def test_count_tokens_and_calculate_cost(client):
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
        "nook.core.clients.gpt_client.inspect.currentframe", lambda: caller_frame
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


# ============================================================================
# Additional tests for 85% coverage target
# ============================================================================


def test_init_raises_without_api_key(monkeypatch, patch_encoding):
    """APIキーが未設定の場合にValueErrorが発生することを確認"""
    # Given: 環境変数にAPIキーがない
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # When/Then: ValueErrorが発生
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        GPTClient(api_key=None)


def test_init_raises_without_model(monkeypatch, patch_encoding):
    """モデルが未設定の場合にValueErrorが発生することを確認"""
    # Given: 環境変数にモデルがなく、空文字列を設定
    monkeypatch.setenv("OPENAI_MODEL", "")

    # When/Then: ValueErrorが発生
    with pytest.raises(ValueError, match="OPENAI_MODEL must be provided"):
        GPTClient(api_key="test-key", model="")


def test_tiktoken_keyerror_fallback(monkeypatch):
    """tiktoken.encoding_for_modelがKeyErrorを発生させた場合のフォールバック"""

    # Given: encoding_for_modelがKeyErrorを発生させる
    def raise_key_error(model):
        raise KeyError("model not found")

    fallback_called = []

    def get_encoding_mock(name):
        fallback_called.append(name)
        return DummyEncoding()

    monkeypatch.setattr(
        "nook.core.clients.gpt_client.tiktoken.encoding_for_model", raise_key_error
    )
    monkeypatch.setattr(
        "nook.core.clients.gpt_client.tiktoken.get_encoding", get_encoding_mock
    )
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda api_key: types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=DummyChatCompletions()),
            responses=DummyResponses(),
        ),
    )

    # When: GPTClientを初期化（フォールバック経路を通すだけでよい）
    GPTClient(api_key="test-key", model="unknown-model")

    # Then: フォールバックエンコーディングが使用される
    assert "cl100k_base" in fallback_called


def test_extract_text_from_response_with_output_text(client):
    """output_textプロパティがある場合の抽出"""
    # Given: output_textを持つレスポンス
    resp = types.SimpleNamespace(output_text="direct text")

    # When: テキストを抽出
    result = client._extract_text_from_response(resp)

    # Then: output_textが返される
    assert result == "direct text"


def test_extract_text_from_response_with_model_dump(client):
    """model_dumpメソッドからテキストを抽出"""
    # Given: output_textがなく、model_dumpで辞書を返すレスポンス
    resp = types.SimpleNamespace(
        output_text=None,
        model_dump=lambda: {
            "output": [{"type": "output_text", "text": "from model_dump"}]
        },
    )

    # When: テキストを抽出
    result = client._extract_text_from_response(resp)

    # Then: model_dumpから抽出される
    assert result == "from model_dump"


def test_extract_text_from_response_with_dict_method(client):
    """dictメソッドからテキストを抽出"""

    # Given: model_dumpがなく、dictメソッドで辞書を返すレスポンス
    def failing_model_dump():
        raise AttributeError("no model_dump")

    resp = types.SimpleNamespace(
        output_text="",
        model_dump=failing_model_dump,
        dict=lambda: {"output": [{"type": "text", "text": "from dict"}]},
    )

    # When: テキストを抽出
    result = client._extract_text_from_response(resp)

    # Then: dictから抽出される
    assert result == "from dict"


def test_extract_text_from_response_fallback_to_dict_attr(client):
    """__dict__からテキストを抽出するフォールバック"""

    # Given: model_dumpもdictもないレスポンス
    class CustomResponse:
        def __init__(self):
            self.output_text = ""
            self.output = [{"type": "output_text", "text": "from __dict__"}]

    resp = CustomResponse()

    # When: テキストを抽出
    result = client._extract_text_from_response(resp)

    # Then: __dict__から抽出される
    assert result == "from __dict__"


def test_extract_text_from_response_returns_empty_on_failure(client):
    """抽出に失敗した場合は空文字を返す"""

    # Given: 何も抽出できないレスポンス
    class NoTextResponse:
        pass

    # __dict__アクセスを防ぐ
    resp = NoTextResponse()
    resp.__dict__ = {}

    # When: テキストを抽出
    result = client._extract_text_from_response(resp)

    # Then: 空文字が返される
    assert result == ""


def test_call_gpt5_returns_output_text(dummy_openai):
    """_call_gpt5がoutput_textを返すことを確認"""
    # Given: gpt-5モデルのクライアント
    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    # When: _call_gpt5を呼び出す
    result = client._call_gpt5("test prompt", "system instruction", 100)

    # Then: responses-outputが返される
    assert result == "responses-output"


def test_call_gpt5_with_previous_response_id(dummy_openai):
    """_call_gpt5が現在の実装で動作することを確認"""
    # Given: 最初の呼び出しで空を返し、2回目で成功するレスポンス
    _, responses = dummy_openai
    call_count = [0]
    call_params: list[dict] = []

    def mock_create(**params):
        call_count[0] += 1
        call_params.append(params)
        if call_count[0] == 1:
            return types.SimpleNamespace(
                output_text="",
                id="resp-1",
                model_dump=lambda: {},
            )
        return types.SimpleNamespace(
            output_text="continued output",
            id="resp-2",
            model_dump=lambda: {},
        )

    responses.create = mock_create

    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    # When: _call_gpt5を呼び出す（空文字の場合は継続して2回目が呼ばれる）
    result = client._call_gpt5("test", None, 100)

    # Then: 2回呼び出され、継続出力が返される
    assert call_count[0] == 2
    assert result == "continued output"
    # 2回目の呼び出しではprevious_response_idが設定されていることを確認
    assert call_params[1]["previous_response_id"] == "resp-1"


def test_call_gpt5_chat_returns_output_text(dummy_openai):
    """_call_gpt5_chatがoutput_textを返すことを確認"""
    # Given: gpt-5モデルのクライアント
    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    messages = [{"role": "user", "content": "hello"}]

    # When: _call_gpt5_chatを呼び出す
    result = client._call_gpt5_chat(messages, "system instruction", 100)

    # Then: responses-outputが返される
    assert result == "responses-output"


def test_call_gpt5_chat_with_continuation(dummy_openai):
    """_call_gpt5_chatが継続生成を試みることを確認"""
    # Given: 最初の呼び出しで空を返すレスポンス
    _, responses = dummy_openai
    call_count = [0]

    def mock_create(**params):
        call_count[0] += 1
        if call_count[0] <= 2:
            return types.SimpleNamespace(
                output_text="",
                id=f"resp-{call_count[0]}",
                model_dump=lambda: {},
            )
        return types.SimpleNamespace(
            output_text="final output",
            id="resp-final",
            model_dump=lambda: {},
        )

    responses.create = mock_create

    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    messages = [{"role": "user", "content": "hello"}]

    # When: _call_gpt5_chatを呼び出す
    result = client._call_gpt5_chat(messages, None, 100)

    # Then: 最大3回まで継続生成が試みられ、最終的な出力が返される
    assert call_count[0] == 3
    assert result == "final output"


def test_get_calling_service_returns_unknown_for_non_services(monkeypatch, client):
    """services配下でない場合はunknownを返す"""
    # Given: services配下でないスタックフレーム
    non_service_frame = types.SimpleNamespace(
        f_back=None,
        f_code=types.SimpleNamespace(co_filename="/home/bob/nook/main.py"),
    )

    monkeypatch.setattr(
        "nook.core.clients.gpt_client.inspect.currentframe", lambda: non_service_frame
    )

    # When/Then: unknownが返される
    assert client._get_calling_service() == "unknown"


def test_get_calling_service_skips_run_services_files(monkeypatch, client):
    """run_services.pyなどの特殊ファイルはスキップされる"""
    # Given: run_services.pyからの呼び出しスタック
    actual_service_frame = types.SimpleNamespace(
        f_back=None,
        f_code=types.SimpleNamespace(
            co_filename="/home/bob/nook/services/actual_service/main.py"
        ),
    )
    run_services_frame = types.SimpleNamespace(
        f_back=actual_service_frame,
        f_code=types.SimpleNamespace(
            co_filename="/home/bob/nook/services/runner/run_services.py"
        ),
    )
    caller_frame = types.SimpleNamespace(
        f_back=run_services_frame,
        f_code=types.SimpleNamespace(co_filename="/home/bob/nook/worker.py"),
    )

    monkeypatch.setattr(
        "nook.core.clients.gpt_client.inspect.currentframe", lambda: caller_frame
    )

    # When/Then: actual_serviceが返される
    assert client._get_calling_service() == "actual_service"


def test_get_calling_service_handles_exception(monkeypatch, client):
    """例外発生時はunknownを返す"""

    # Given: currentframeが例外を発生させる
    def raise_error():
        raise RuntimeError("frame error")

    monkeypatch.setattr(
        "nook.core.clients.gpt_client.inspect.currentframe", raise_error
    )

    # When/Then: unknownが返される
    assert client._get_calling_service() == "unknown"


def test_generate_content_uses_max_tokens_for_old_models(dummy_openai):
    """gpt-3.5-turboなどの古いモデルではmax_tokensを使用"""
    # Given: gpt-3.5-turboモデル
    client = GPTClient(api_key="test-key", model="gpt-3.5-turbo")
    client.encoding = DummyEncoding()

    # When: generate_contentを呼び出す
    result = client.generate_content(prompt="hello", max_tokens=50)

    # Then: max_tokensが使用される
    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["max_tokens"] == 50
    assert "max_completion_tokens" not in params


@pytest.mark.asyncio
async def test_generate_async(dummy_openai):
    """generate_asyncが非同期で動作することを確認"""
    # Given: クライアント
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")
    client.encoding = DummyEncoding()

    # When: generate_asyncを呼び出す
    result = await client.generate_async(
        prompt="async test",
        system_instruction="be helpful",
        temperature=0.5,
        max_tokens=100,
    )

    # Then: 結果が返される
    assert result == "chat-output"


def test_create_chat_with_system_instruction(dummy_openai):
    """create_chatがシステム指示付きでセッションを作成"""
    # Given: クライアント
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")

    # When: システム指示付きでチャットを作成
    session = client.create_chat(system_instruction="You are helpful")

    # Then: システムメッセージが含まれる
    assert session["messages"][0]["role"] == "system"
    assert session["messages"][0]["content"] == "You are helpful"


def test_create_chat_without_system_instruction(dummy_openai):
    """create_chatがシステム指示なしでセッションを作成"""
    # Given: クライアント
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")

    # When: システム指示なしでチャットを作成
    session = client.create_chat()

    # Then: 空のメッセージリスト
    assert session["messages"] == []


def test_send_message_uses_gpt5_path(monkeypatch, dummy_openai):
    """send_messageがgpt-5モデルでgpt5パスを使用"""
    # Given: gpt-5モデルのクライアント
    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    called = {}

    def fake_call_gpt5_chat(messages, system_instruction, max_tokens):
        called["args"] = (messages, system_instruction, max_tokens)
        return "gpt5-chat-output"

    monkeypatch.setattr(client, "_call_gpt5_chat", fake_call_gpt5_chat)

    chat_session = {"messages": [{"role": "system", "content": "sys"}]}

    # When: send_messageを呼び出す
    result = client.send_message(chat_session, "question", max_tokens=50)

    # Then: gpt5パスが使用される
    assert result == "gpt5-chat-output"
    assert called["args"][2] == 50


def test_send_message_uses_max_tokens_for_old_models(dummy_openai):
    """send_messageが古いモデルでmax_tokensを使用"""
    # Given: gpt-3.5-turboモデル
    client = GPTClient(api_key="test-key", model="gpt-3.5-turbo")
    client.encoding = DummyEncoding()

    chat_session = {"messages": []}

    # When: send_messageを呼び出す
    result = client.send_message(chat_session, "question", max_tokens=50)

    # Then: max_tokensが使用される
    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["max_tokens"] == 50
    assert "max_completion_tokens" not in params


def test_chat_with_search_uses_gpt5_path(monkeypatch, dummy_openai):
    """chat_with_searchがgpt-5モデルでgpt5パスを使用"""
    # Given: gpt-5モデルのクライアント
    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    called = {}

    def fake_call_gpt5_chat(messages, system_instruction, max_tokens):
        called["args"] = (messages, system_instruction, max_tokens)
        return "gpt5-search-output"

    monkeypatch.setattr(client, "_call_gpt5_chat", fake_call_gpt5_chat)

    # When: chat_with_searchを呼び出す
    result = client.chat_with_search(message="query", context="context", max_tokens=100)

    # Then: gpt5パスが使用される
    assert result == "gpt5-search-output"


def test_chat_with_search_uses_max_tokens_for_old_models(dummy_openai):
    """chat_with_searchが古いモデルでmax_tokensを使用"""
    # Given: gpt-3.5-turboモデル
    client = GPTClient(api_key="test-key", model="gpt-3.5-turbo")
    client.encoding = DummyEncoding()

    # When: chat_with_searchを呼び出す
    result = client.chat_with_search(message="query", context="context", max_tokens=100)

    # Then: max_tokensが使用される
    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["max_tokens"] == 100
    assert "max_completion_tokens" not in params


def test_chat_uses_gpt5_path(monkeypatch, dummy_openai):
    """chatがgpt-5モデルでgpt5パスを使用"""
    # Given: gpt-5モデルのクライアント
    client = GPTClient(api_key="test-key", model="gpt-5-preview")
    client.encoding = DummyEncoding()

    called = {}

    def fake_call_gpt5_chat(messages, system_instruction, max_tokens):
        called["args"] = (messages, system_instruction, max_tokens)
        return "gpt5-chat-output"

    monkeypatch.setattr(client, "_call_gpt5_chat", fake_call_gpt5_chat)

    # When: chatを呼び出す
    result = client.chat(
        messages=[{"role": "user", "content": "hi"}],
        system="sys",
        max_tokens=100,
    )

    # Then: gpt5パスが使用される
    assert result == "gpt5-chat-output"


def test_chat_uses_max_tokens_for_old_models(dummy_openai):
    """chatが古いモデルでmax_tokensを使用"""
    # Given: gpt-3.5-turboモデル
    client = GPTClient(api_key="test-key", model="gpt-3.5-turbo")
    client.encoding = DummyEncoding()

    # When: chatを呼び出す
    result = client.chat(
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
    )

    # Then: max_tokensが使用される
    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["max_tokens"] == 100
    assert "max_completion_tokens" not in params


def test_chat_without_system(dummy_openai):
    """chatがシステム指示なしで動作"""
    # Given: クライアント
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")
    client.encoding = DummyEncoding()

    # When: システム指示なしでchatを呼び出す
    result = client.chat(messages=[{"role": "user", "content": "hi"}])

    # Then: システムメッセージなしで動作
    params = client.client.chat.completions.last_params
    assert result == "chat-output"
    assert params["messages"][0]["role"] == "user"


def test_chat_with_search_without_history(dummy_openai):
    """chat_with_searchが履歴なしで動作"""
    # Given: クライアント
    client = GPTClient(api_key="test-key", model="gpt-4.1-mini")
    client.encoding = DummyEncoding()

    # When: 履歴なしでchat_with_searchを呼び出す
    result = client.chat_with_search(
        message="query",
        context="context",
        chat_history=None,
    )

    # Then: 正常に動作
    assert result == "chat-output"
