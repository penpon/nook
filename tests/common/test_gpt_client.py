"""
nook/common/gpt_client.py のテスト

テスト観点:
- 初期化処理（API key取得、モデル設定）
- トークン数カウント・コスト計算
- テキスト生成（同期・非同期）
- チャット機能（セッション管理、メッセージ送信）
- GPT-5モデル対応
- エラーハンドリング・リトライ
"""

from unittest.mock import Mock, patch

import pytest
from openai import OpenAI

from nook.common.gpt_client import GPTClient

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_explicit_api_key(monkeypatch):
    """
    Given: API keyとモデル名を明示的に指定
    When: GPTClientを初期化
    Then: 指定したAPI keyとモデル名が設定される
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = GPTClient(api_key="test-key-123", model="gpt-4o-mini")
    assert client.api_key == "test-key-123"
    assert client.model == "gpt-4o-mini"
    assert isinstance(client.client, OpenAI)


@pytest.mark.unit
def test_init_from_env_api_key(monkeypatch):
    """
    Given: 環境変数OPENAI_API_KEYが設定されている
    When: API keyを指定せずにGPTClientを初期化
    Then: 環境変数からAPI keyが取得される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "env-key-456")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    client = GPTClient()
    assert client.api_key == "env-key-456"


@pytest.mark.unit
def test_init_with_explicit_model(monkeypatch):
    """
    Given: モデル名を明示的に指定
    When: GPTClientを初期化
    Then: 指定したモデル名が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")
    assert client.model == "gpt-5-turbo"


@pytest.mark.unit
def test_init_model_from_env(monkeypatch):
    """
    Given: 環境変数OPENAI_MODELが設定されている
    When: モデル名を指定せずにGPTClientを初期化
    Then: 環境変数からモデル名が取得される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-preview")
    client = GPTClient()
    assert client.model == "gpt-5-preview"


@pytest.mark.unit
def test_init_model_default_value(monkeypatch):
    """
    Given: モデル名未指定・環境変数もなし
    When: GPTClientを初期化
    Then: デフォルト値"gpt-4.1-nano"が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = GPTClient()
    assert client.model == "gpt-4.1-nano"


@pytest.mark.unit
def test_init_no_api_key_raises_error(monkeypatch):
    """
    Given: API keyが指定されず、環境変数も未設定
    When: GPTClientを初期化しようとする
    Then: ValueErrorが発生する
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        GPTClient()


@pytest.mark.unit
def test_init_empty_api_key_raises_error(monkeypatch):
    """
    Given: 空文字列のAPI keyを指定
    When: GPTClientを初期化しようとする
    Then: ValueErrorが発生する
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        GPTClient(api_key="")


@pytest.mark.unit
def test_init_empty_model_uses_default(monkeypatch):
    """
    Given: 空文字列のモデル名を指定（環境変数もなし）
    When: GPTClientを初期化
    Then: デフォルト値"gpt-4.1-nano"が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    # 空文字列はFalsyなので、デフォルト値が使用される
    client = GPTClient(model="")
    assert client.model == "gpt-4.1-nano"


@pytest.mark.unit
def test_init_tiktoken_encoding_success(monkeypatch):
    """
    Given: 正常な環境
    When: GPTClientを初期化
    Then: tiktokenのencodingが正常に取得される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    assert client.encoding is not None


@pytest.mark.unit
def test_init_tiktoken_fallback_to_cl100k_base(monkeypatch):
    """
    Given: tiktoken.encoding_for_modelがKeyErrorを発生
    When: GPTClientを初期化
    Then: cl100k_baseエンコーダーにフォールバックする
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("tiktoken.encoding_for_model", side_effect=KeyError):
        client = GPTClient()
        assert client.encoding is not None


@pytest.mark.unit
def test_init_openai_client_created(monkeypatch):
    """
    Given: 正常なAPI key
    When: GPTClientを初期化
    Then: OpenAI clientインスタンスが作成される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    assert isinstance(client.client, OpenAI)


@pytest.mark.unit
def test_init_none_api_key_no_env(monkeypatch):
    """
    Given: API keyにNoneを明示指定・環境変数なし
    When: GPTClientを初期化しようとする
    Then: ValueErrorが発生する
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be provided"):
        GPTClient(api_key=None)


# =============================================================================
# 2. _count_tokens メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_count_tokens_normal_text(monkeypatch):
    """
    Given: 通常の英語テキスト
    When: _count_tokensを呼び出す
    Then: 正の整数が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    count = client._count_tokens("Hello, world!")
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.unit
def test_count_tokens_empty_string(monkeypatch):
    """
    Given: 空文字列
    When: _count_tokensを呼び出す
    Then: 0が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    count = client._count_tokens("")
    assert count == 0


@pytest.mark.unit
def test_count_tokens_japanese_text(monkeypatch):
    """
    Given: 日本語テキスト
    When: _count_tokensを呼び出す
    Then: 正の整数が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    count = client._count_tokens("こんにちは世界")
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.unit
def test_count_tokens_long_text(monkeypatch):
    """
    Given: 長文テキスト（10000文字）
    When: _count_tokensを呼び出す
    Then: 正の整数が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    long_text = "a" * 10000
    count = client._count_tokens(long_text)
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.unit
def test_count_tokens_special_characters(monkeypatch):
    """
    Given: 特殊文字を含むテキスト
    When: _count_tokensを呼び出す
    Then: 正の整数が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    count = client._count_tokens("!@#$%^&*()")
    assert isinstance(count, int)
    assert count >= 0


@pytest.mark.unit
def test_count_tokens_encoding_error_returns_zero(monkeypatch):
    """
    Given: encoding.encodeがExceptionを発生
    When: _count_tokensを呼び出す
    Then: 0が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    with patch.object(
        client.encoding, "encode", side_effect=Exception("Encoding error")
    ):
        count = client._count_tokens("test")
        assert count == 0


@pytest.mark.unit
def test_count_tokens_unicode_emoji(monkeypatch):
    """
    Given: Unicode絵文字を含むテキスト
    When: _count_tokensを呼び出す
    Then: 正の整数が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    count = client._count_tokens("😀🎉🌟")
    assert isinstance(count, int)
    assert count >= 0


# =============================================================================
# 3. _calculate_cost メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_calculate_cost_normal(monkeypatch):
    """
    Given: 入力トークン1000、出力トークン500
    When: _calculate_costを呼び出す
    Then: 正しいコスト（0.0006）が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(1000, 500)
    # (1000/1M * 0.20) + (500/1M * 0.80) = 0.0002 + 0.0004 = 0.0006
    assert abs(cost - 0.0006) < 1e-10


@pytest.mark.unit
def test_calculate_cost_zero_input_tokens(monkeypatch):
    """
    Given: 入力トークン0、出力トークン500
    When: _calculate_costを呼び出す
    Then: 出力トークン分のみのコストが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(0, 500)
    # (0/1M * 0.20) + (500/1M * 0.80) = 0 + 0.0004 = 0.0004
    assert abs(cost - 0.0004) < 1e-10


@pytest.mark.unit
def test_calculate_cost_zero_output_tokens(monkeypatch):
    """
    Given: 入力トークン1000、出力トークン0
    When: _calculate_costを呼び出す
    Then: 入力トークン分のみのコストが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(1000, 0)
    # (1000/1M * 0.20) + (0/1M * 0.80) = 0.0002 + 0 = 0.0002
    assert abs(cost - 0.0002) < 1e-10


@pytest.mark.unit
def test_calculate_cost_both_zero(monkeypatch):
    """
    Given: 入力トークン0、出力トークン0
    When: _calculate_costを呼び出す
    Then: 0.0が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(0, 0)
    assert cost == 0.0


@pytest.mark.unit
def test_calculate_cost_large_numbers(monkeypatch):
    """
    Given: 巨大なトークン数（入力10M、出力5M）
    When: _calculate_costを呼び出す
    Then: 正しいコストが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(10000000, 5000000)
    # (10M/1M * 0.20) + (5M/1M * 0.80) = 2.0 + 4.0 = 6.0
    assert abs(cost - 6.0) < 1e-10


@pytest.mark.unit
def test_calculate_cost_decimal_precision(monkeypatch):
    """
    Given: 小数点以下の精度が必要なトークン数
    When: _calculate_costを呼び出す
    Then: 小数点以下の精度が保たれる
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    cost = client._calculate_cost(123, 456)
    # (123/1M * 0.20) + (456/1M * 0.80) = 0.0000246 + 0.0003648 = 0.0003894
    assert isinstance(cost, float)
    assert cost > 0


# =============================================================================
# 4. _is_gpt5_model メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_is_gpt5_model_lowercase(monkeypatch):
    """
    Given: モデル名が"gpt-5-turbo"（小文字）
    When: _is_gpt5_modelを呼び出す
    Then: Trueが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")
    assert client._is_gpt5_model() is True


@pytest.mark.unit
def test_is_gpt5_model_uppercase(monkeypatch):
    """
    Given: モデル名が"GPT-5-PREVIEW"（大文字）
    When: _is_gpt5_modelを呼び出す
    Then: Trueが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="GPT-5-PREVIEW")
    assert client._is_gpt5_model() is True


@pytest.mark.unit
def test_is_gpt5_model_gpt41_false(monkeypatch):
    """
    Given: モデル名が"gpt-4.1-nano"
    When: _is_gpt5_modelを呼び出す
    Then: Falseが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-4.1-nano")
    assert client._is_gpt5_model() is False


@pytest.mark.unit
def test_is_gpt5_model_gpt4o_false(monkeypatch):
    """
    Given: モデル名が"gpt-4o-mini"
    When: _is_gpt5_modelを呼び出す
    Then: Falseが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-4o-mini")
    assert client._is_gpt5_model() is False


# =============================================================================
# 6. _get_calling_service メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_calling_service_not_in_services(monkeypatch):
    """
    Given: services/配下でない場所からの呼び出し
    When: _get_calling_serviceを呼び出す
    Then: "unknown"が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    service = client._get_calling_service()
    # テストコードからの呼び出しなので"unknown"が返される
    assert service == "unknown"


@pytest.mark.unit
def test_get_calling_service_inspect_error(monkeypatch):
    """
    Given: inspect.currentframe()がExceptionを発生
    When: _get_calling_serviceを呼び出す
    Then: "unknown"が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    with patch("inspect.currentframe", side_effect=Exception("Frame error")):
        service = client._get_calling_service()
        assert service == "unknown"


# =============================================================================
# 7. _messages_to_responses_input メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_messages_to_responses_input_normal(monkeypatch):
    """
    Given: 正常なメッセージリスト
    When: _messages_to_responses_inputを呼び出す
    Then: Responses API形式に変換される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    messages = [{"role": "user", "content": "Hello"}]
    result = client._messages_to_responses_input(messages)
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"][0]["type"] == "input_text"
    assert result[0]["content"][0]["text"] == "Hello"


@pytest.mark.unit
def test_messages_to_responses_input_with_system(monkeypatch):
    """
    Given: systemメッセージを含むメッセージリスト
    When: _messages_to_responses_inputを呼び出す
    Then: 両方のメッセージが変換される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi"},
    ]
    result = client._messages_to_responses_input(messages)
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"


@pytest.mark.unit
def test_messages_to_responses_input_empty_list(monkeypatch):
    """
    Given: 空のメッセージリスト
    When: _messages_to_responses_inputを呼び出す
    Then: 空リストが返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    result = client._messages_to_responses_input([])
    assert result == []


@pytest.mark.unit
def test_messages_to_responses_input_no_role(monkeypatch):
    """
    Given: roleキーがないメッセージ
    When: _messages_to_responses_inputを呼び出す
    Then: デフォルトで"user"が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    messages = [{"content": "Hello"}]
    result = client._messages_to_responses_input(messages)
    assert result[0]["role"] == "user"


@pytest.mark.unit
def test_messages_to_responses_input_no_content(monkeypatch):
    """
    Given: contentキーがないメッセージ
    When: _messages_to_responses_inputを呼び出す
    Then: 空文字列""が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    messages = [{"role": "user"}]
    result = client._messages_to_responses_input(messages)
    assert result[0]["content"][0]["text"] == ""


@pytest.mark.unit
def test_messages_to_responses_input_multiple(monkeypatch):
    """
    Given: 複数のメッセージリスト
    When: _messages_to_responses_inputを呼び出す
    Then: 全て正しく変換される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Message 2"},
        {"role": "user", "content": "Message 3"},
    ]
    result = client._messages_to_responses_input(messages)
    assert len(result) == 3
    assert all("content" in item for item in result)


# =============================================================================
# 8. _extract_text_from_response メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_extract_text_output_text_attribute(monkeypatch):
    """
    Given: respにoutput_text属性がある
    When: _extract_text_from_responseを呼び出す
    Then: output_textの値が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    mock_resp = Mock()
    mock_resp.output_text = "Response text"
    result = client._extract_text_from_response(mock_resp)
    assert result == "Response text"


@pytest.mark.unit
def test_extract_text_empty_output_text(monkeypatch):
    """
    Given: output_textが空文字列
    When: _extract_text_from_responseを呼び出す
    Then: 辞書から走査して抽出を試みる
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    mock_resp = Mock()
    mock_resp.output_text = ""
    mock_resp.model_dump = Mock(
        return_value={"output": [{"type": "output_text", "text": "Extracted"}]}
    )
    result = client._extract_text_from_response(mock_resp)
    assert result == "Extracted"


@pytest.mark.unit
def test_extract_text_via_model_dump(monkeypatch):
    """
    Given: output_textがNoneでmodel_dumpで辞書取得可能
    When: _extract_text_from_responseを呼び出す
    Then: 辞書から走査してテキストが抽出される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    mock_resp = Mock()
    mock_resp.output_text = None
    mock_resp.model_dump = Mock(
        return_value={"data": {"type": "output_text", "text": "Model dump text"}}
    )
    result = client._extract_text_from_response(mock_resp)
    assert "Model dump text" in result


@pytest.mark.unit
def test_extract_text_no_text_found(monkeypatch):
    """
    Given: レスポンスにテキスト要素が見つからない
    When: _extract_text_from_responseを呼び出す
    Then: 空文字列""が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    mock_resp = Mock()
    mock_resp.output_text = None
    mock_resp.model_dump = Mock(return_value={"data": "no text here"})
    result = client._extract_text_from_response(mock_resp)
    assert result == ""


# =============================================================================
# 9. generate_content メソッドのテスト（GPT-5専用）
# =============================================================================


@pytest.mark.unit
def test_generate_content_gpt5_basic(monkeypatch):
    """
    Given: gpt-5モデルでプロンプト指定
    When: generate_contentを呼び出す
    Then: GPT-5 Responses APIでテキストが生成される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    # Responses APIのモック
    mock_response = Mock()
    mock_response.output_text = "GPT-5 generated text"
    mock_response.id = "resp-123"

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.generate_content(prompt="Hello")
        assert result == "GPT-5 generated text"


# =============================================================================
# 10. generate_async メソッドのテスト（GPT-5専用）
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_async_gpt5_basic(monkeypatch):
    """
    Given: gpt-5モデルでプロンプト指定
    When: generate_asyncを呼び出す
    Then: 非同期でGPT-5がテキストを生成する
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    # Responses APIのモック
    mock_response = Mock()
    mock_response.output_text = "Async GPT-5 generated"
    mock_response.id = "resp-async-123"

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = await client.generate_async(prompt="Hello async")
        assert result == "Async GPT-5 generated"


# =============================================================================
# 11. create_chat メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_create_chat_without_system(monkeypatch):
    """
    Given: system_instructionなし
    When: create_chatを呼び出す
    Then: 空のmessagesリストを持つ辞書が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    chat_session = client.create_chat()
    assert "messages" in chat_session
    assert chat_session["messages"] == []


@pytest.mark.unit
def test_create_chat_with_system(monkeypatch):
    """
    Given: system_instructionを指定
    When: create_chatを呼び出す
    Then: systemメッセージを含む辞書が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    chat_session = client.create_chat(system_instruction="You are helpful.")
    assert len(chat_session["messages"]) == 1
    assert chat_session["messages"][0]["role"] == "system"
    assert chat_session["messages"][0]["content"] == "You are helpful."


@pytest.mark.unit
def test_create_chat_return_structure(monkeypatch):
    """
    Given: デフォルト引数
    When: create_chatを呼び出す
    Then: {"messages": [...]}の形式が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()
    chat_session = client.create_chat()
    assert isinstance(chat_session, dict)
    assert "messages" in chat_session
    assert isinstance(chat_session["messages"], list)


# =============================================================================
# 12. send_message メソッドのテスト（GPT-5専用）
# =============================================================================


@pytest.mark.unit
def test_send_message_gpt5_basic(monkeypatch):
    """
    Given: gpt-5でチャットセッションとメッセージ
    When: send_messageを呼び出す
    Then: GPT-5がAIの応答を返す
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 AI response"
    mock_response.id = "resp-chat-123"

    chat_session = client.create_chat()

    with patch.object(client.client.responses, "create", return_value=mock_response):
        response = client.send_message(chat_session, "Hello")
        assert response == "GPT-5 AI response"


@pytest.mark.unit
def test_send_message_gpt5_history_updated(monkeypatch):
    """
    Given: gpt-5でチャットセッションにメッセージを送信
    When: send_messageを呼び出す
    Then: user/assistantメッセージが履歴に追加される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "Response"
    mock_response.id = "resp-chat-456"

    chat_session = client.create_chat()

    with patch.object(client.client.responses, "create", return_value=mock_response):
        client.send_message(chat_session, "Test message")
        assert len(chat_session["messages"]) == 2
        assert chat_session["messages"][0]["role"] == "user"
        assert chat_session["messages"][1]["role"] == "assistant"


# =============================================================================
# 13. chat_with_search メソッドのテスト（GPT-5専用）
# =============================================================================


@pytest.mark.unit
def test_chat_with_search_gpt5_basic(monkeypatch):
    """
    Given: gpt-5でメッセージとコンテキスト
    When: chat_with_searchを呼び出す
    Then: GPT-5がAIの応答を返す
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 search response"
    mock_response.id = "resp-search-123"

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.chat_with_search(
            message="What is this?", context="This is context."
        )
        assert result == "GPT-5 search response"


@pytest.mark.unit
def test_chat_with_search_gpt5_with_history(monkeypatch):
    """
    Given: gpt-5でchat_historyを含むメッセージ
    When: chat_with_searchを呼び出す
    Then: 履歴を含めて処理される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 history response"
    mock_response.id = "resp-search-456"

    history = [{"role": "user", "content": "Previous message"}]

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.chat_with_search(
            message="New question", context="Context", chat_history=history
        )
        assert result == "GPT-5 history response"


# =============================================================================
# 14. chat メソッドのテスト（GPT-5専用）
# =============================================================================


@pytest.mark.unit
def test_chat_gpt5_basic(monkeypatch):
    """
    Given: gpt-5でメッセージリスト
    When: chatを呼び出す
    Then: GPT-5がAIの応答を返す
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 chat response"
    mock_response.id = "resp-chat-basic"

    messages = [{"role": "user", "content": "Hello"}]

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.chat(messages=messages)
        assert result == "GPT-5 chat response"


@pytest.mark.unit
def test_chat_gpt5_with_system(monkeypatch):
    """
    Given: gpt-5でsystemメッセージ付きメッセージリスト
    When: chatを呼び出す
    Then: systemメッセージを含めて処理される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 system chat response"
    mock_response.id = "resp-chat-system"

    messages = [{"role": "user", "content": "Hello"}]

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.chat(messages=messages, system="You are helpful.")
        assert result == "GPT-5 system chat response"


@pytest.mark.unit
def test_chat_gpt5_multiple_messages(monkeypatch):
    """
    Given: gpt-5で複数ターンのメッセージリスト
    When: chatを呼び出す
    Then: 複数メッセージで処理される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "GPT-5 multi response"
    mock_response.id = "resp-chat-multi"

    messages = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Second"},
    ]

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client.chat(messages=messages)
        assert result == "GPT-5 multi response"


# =============================================================================
# 15. GPT-5 内部メソッドのテスト（_call_gpt5, _call_gpt5_chat）
# =============================================================================


@pytest.mark.unit
def test_call_gpt5_first_attempt_success(monkeypatch):
    """
    Given: GPT-5モデルで1回目のAPI呼び出しが成功
    When: _call_gpt5を呼び出す
    Then: 1回のAPI呼び出しで完了する
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "First attempt success"
    mock_response.id = "resp-123"

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client._call_gpt5("Test prompt", "System instruction", 1000)
        assert result == "First attempt success"


@pytest.mark.unit
def test_call_gpt5_continuation_success(monkeypatch):
    """
    Given: 1回目のoutput_textが空、2回目で成功
    When: _call_gpt5を呼び出す
    Then: previous_response_idで継続生成される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    # 1回目: output_textが空
    mock_response1 = Mock()
    mock_response1.output_text = ""
    mock_response1.id = "resp-123"

    # 2回目: output_textあり
    mock_response2 = Mock()
    mock_response2.output_text = "Second attempt success"
    mock_response2.id = "resp-456"

    with patch.object(
        client.client.responses, "create", side_effect=[mock_response1, mock_response2]
    ):
        result = client._call_gpt5("Test prompt", None, 1000)
        assert result == "Second attempt success"


@pytest.mark.unit
def test_call_gpt5_chat_first_success(monkeypatch):
    """
    Given: GPT-5チャット形式で1回目が成功
    When: _call_gpt5_chatを呼び出す
    Then: 1回のAPI呼び出しで完了する
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "Chat response"
    mock_response.id = "resp-chat-123"

    messages = [{"role": "user", "content": "Hello"}]

    with patch.object(client.client.responses, "create", return_value=mock_response):
        result = client._call_gpt5_chat(messages, None, 1000)
        assert result == "Chat response"


@pytest.mark.unit
def test_extract_text_via_dict_attribute(monkeypatch):
    """
    Given: model_dump/dictメソッドがなく__dict__属性を使用
    When: _extract_text_from_responseを呼び出す
    Then: __dict__から走査してテキストが抽出される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    # model_dump/dictメソッドがないオブジェクト
    class CustomResponse:
        def __init__(self):
            self.output_text = None
            self.data = {"type": "output_text", "text": "Dict attribute text"}

    mock_resp = CustomResponse()
    result = client._extract_text_from_response(mock_resp)
    assert "Dict attribute text" in result


@pytest.mark.unit
def test_call_gpt5_all_attempts_fail(monkeypatch):
    """
    Given: 3回ともoutput_textが空
    When: _call_gpt5を呼び出す
    Then: 空文字列が返される（エラーなし）
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = ""
    mock_response.id = "resp-fail"

    with patch.object(
        client.client.responses, "create", return_value=mock_response
    ) as mock_create:
        result = client._call_gpt5("Test prompt", None, 1000)
        # 3回試行されることを確認
        assert mock_create.call_count == 3
        # 結果は何も返らない（Noneまたは空文字列）
        assert result is None or result == ""


# =============================================================================
# 16. エッジケーステスト（カバレッジ向上用）
# =============================================================================


@pytest.mark.unit
def test_init_none_model_with_no_env(monkeypatch):
    """
    Given: modelにNoneを指定、環境変数もなし
    When: GPTClientを初期化
    Then: デフォルト値"gpt-4.1-nano"が設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    client = GPTClient(model=None)
    assert client.model == "gpt-4.1-nano"


@pytest.mark.unit
def test_extract_text_dict_access_exception(monkeypatch):
    """
    Given: __dict__アクセスが例外を発生するレスポンス
    When: _extract_text_from_responseを呼び出す
    Then: 空文字列が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    class BadResponse:
        output_text = None

        @property
        def __dict__(self):
            raise AttributeError("No __dict__")

    mock_resp = BadResponse()
    result = client._extract_text_from_response(mock_resp)
    assert result == ""


@pytest.mark.unit
def test_call_gpt5_with_prev_id(monkeypatch):
    """
    Given: 1回目が空、2回目でprevious_response_idを使用
    When: _call_gpt5を呼び出す
    Then: previous_response_idで継続生成される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response1 = Mock()
    mock_response1.output_text = ""
    mock_response1.id = "resp-123"

    mock_response2 = Mock()
    mock_response2.output_text = "Continued text"
    mock_response2.id = "resp-456"

    with patch.object(
        client.client.responses, "create", side_effect=[mock_response1, mock_response2]
    ) as mock_create:
        result = client._call_gpt5("Test", None, 1000)
        assert result == "Continued text"
        # 2回目の呼び出しでprevious_response_idが使用されることを確認
        assert mock_create.call_count == 2
        second_call_kwargs = mock_create.call_args_list[1][1]
        assert "previous_response_id" in second_call_kwargs


@pytest.mark.unit
def test_call_gpt5_chat_with_prev_id(monkeypatch):
    """
    Given: 1回目が空、2回目でprevious_response_idを使用
    When: _call_gpt5_chatを呼び出す
    Then: previous_response_idで継続生成される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response1 = Mock()
    mock_response1.output_text = ""
    mock_response1.id = "resp-chat-123"

    mock_response2 = Mock()
    mock_response2.output_text = "Chat continued"
    mock_response2.id = "resp-chat-456"

    messages = [{"role": "user", "content": "Hello"}]

    with patch.object(
        client.client.responses, "create", side_effect=[mock_response1, mock_response2]
    ) as mock_create:
        result = client._call_gpt5_chat(messages, None, 1000)
        assert result == "Chat continued"
        assert mock_create.call_count == 2
        second_call_kwargs = mock_create.call_args_list[1][1]
        assert "previous_response_id" in second_call_kwargs


@pytest.mark.unit
def test_call_gpt5_with_system_instruction(monkeypatch):
    """
    Given: system_instructionを指定
    When: _call_gpt5を呼び出す
    Then: instructionsパラメータが設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "Response with system"
    mock_response.id = "resp-sys"

    with patch.object(
        client.client.responses, "create", return_value=mock_response
    ) as mock_create:
        result = client._call_gpt5("Test", "You are helpful", 1000)
        assert result == "Response with system"
        call_kwargs = mock_create.call_args[1]
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "You are helpful"


@pytest.mark.unit
def test_call_gpt5_chat_with_system_instruction(monkeypatch):
    """
    Given: system_instructionを指定
    When: _call_gpt5_chatを呼び出す
    Then: instructionsパラメータが設定される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient(model="gpt-5-turbo")

    mock_response = Mock()
    mock_response.output_text = "Chat with system"
    mock_response.id = "resp-chat-sys"

    messages = [{"role": "user", "content": "Hello"}]

    with patch.object(
        client.client.responses, "create", return_value=mock_response
    ) as mock_create:
        result = client._call_gpt5_chat(messages, "You are helpful", 1000)
        assert result == "Chat with system"
        call_kwargs = mock_create.call_args[1]
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "You are helpful"


@pytest.mark.unit
def test_get_calling_service_from_services_directory(monkeypatch):
    """
    Given: services/reddit_explorer/からの呼び出しをシミュレート
    When: _get_calling_serviceを呼び出す
    Then: "reddit_explorer"が返される
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    # モックフレームチェーンを作成
    mock_frame2 = Mock()
    mock_frame2.f_code.co_filename = (
        "/path/to/nook/services/reddit_explorer/reddit_explorer.py"
    )
    mock_frame2.f_back = None

    mock_frame1 = Mock()
    mock_frame1.f_code.co_filename = "/path/to/tests/test_gpt_client.py"
    mock_frame1.f_back = mock_frame2

    with patch("inspect.currentframe", return_value=mock_frame1):
        service = client._get_calling_service()
        assert service == "reddit_explorer"


@pytest.mark.unit
def test_get_calling_service_special_cases(monkeypatch):
    """
    Given: run_services.pyや__pycache__からの呼び出し
    When: _get_calling_serviceを呼び出す
    Then: それらをスキップして次のフレームをチェックする
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    # run_services.pyをスキップするケース
    mock_frame3 = Mock()
    mock_frame3.f_code.co_filename = (
        "/path/to/nook/services/reddit_explorer/reddit_explorer.py"
    )
    mock_frame3.f_back = None

    mock_frame2 = Mock()
    mock_frame2.f_code.co_filename = "/path/to/nook/services/run_services.py"
    mock_frame2.f_back = mock_frame3

    mock_frame1 = Mock()
    mock_frame1.f_code.co_filename = "/path/to/tests/test_gpt_client.py"
    mock_frame1.f_back = mock_frame2

    with patch("inspect.currentframe", return_value=mock_frame1):
        service = client._get_calling_service()
        assert service == "reddit_explorer"


@pytest.mark.unit
def test_get_calling_service_pycache_skip(monkeypatch):
    """
    Given: __pycache__ディレクトリからの呼び出し
    When: _get_calling_serviceを呼び出す
    Then: __で始まるディレクトリをスキップする
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    # 有効なサービスフレーム
    mock_frame3 = Mock()
    mock_frame3.f_code.co_filename = "/path/to/nook/services/tech_feed/tech_feed.py"
    mock_frame3.f_back = None

    # __pycache__をスキップ
    mock_frame2 = Mock()
    mock_frame2.f_code.co_filename = "/path/to/nook/services/__pycache__/cached.py"
    mock_frame2.f_back = mock_frame3

    mock_frame1 = Mock()
    mock_frame1.f_code.co_filename = "/path/to/tests/test_gpt_client.py"
    mock_frame1.f_back = mock_frame2

    with patch("inspect.currentframe", return_value=mock_frame1):
        service = client._get_calling_service()
        assert service == "tech_feed"


@pytest.mark.unit
def test_get_calling_service_py_file_skip(monkeypatch):
    """
    Given: .pyで終わるサービス名（ファイル名が直接services/直下）
    When: _get_calling_serviceを呼び出す
    Then: .pyで終わるものをスキップする
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = GPTClient()

    # 有効なサービスフレーム
    mock_frame3 = Mock()
    mock_frame3.f_code.co_filename = (
        "/path/to/nook/services/github_trending/github_trending.py"
    )
    mock_frame3.f_back = None

    # .pyファイルをスキップ
    mock_frame2 = Mock()
    mock_frame2.f_code.co_filename = "/path/to/nook/services/helper.py"
    mock_frame2.f_back = mock_frame3

    mock_frame1 = Mock()
    mock_frame1.f_code.co_filename = "/path/to/tests/test_gpt_client.py"
    mock_frame1.f_back = mock_frame2

    with patch("inspect.currentframe", return_value=mock_frame1):
        service = client._get_calling_service()
        assert service == "github_trending"
