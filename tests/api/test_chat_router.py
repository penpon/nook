from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app
from nook.api.routers import chat as chat_module


def _make_client() -> TestClient:
    """Create a FastAPI TestClient for chat tests.

    Returns:
        TestClient: Configured client instance.
    """

    return TestClient(app)


def _base_payload() -> dict[str, Any]:
    """Build the baseline chat payload for POST requests.

    Returns:
        dict[str, Any]: Request body containing topic, message, history, and markdown.
    """

    return {
        "topic_id": "topic-1",
        "message": "hello",
        "chat_history": [{"role": "user", "content": "hi"}],
        "markdown": "## Context",
    }


def test_chat_returns_dummy_response_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test chat fallback when the OpenAI API key is unset.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If fallback response does not mention missing key.
    """

    # Given: Test client without OPENAI_API_KEY environment variable
    client = _make_client()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # When: Posting chat request
    resp = client.post("/api/chat", json=_base_payload())

    # Then: Response informs about missing API key
    assert resp.status_code == 200
    data = resp.json()
    assert "OPENAI_API_KEY" in data["response"]
    assert "設定されていない" in data["response"]


def test_chat_calls_gptclient_with_expected_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test GPTClient receives expected arguments from chat endpoint.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If GPTClient is not invoked with expected payload.
    """

    # Given: Patched GPT client capturing invocation arguments
    client = _make_client()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    calls: dict[str, Any] = {}

    class DummyGPTClient:
        def __init__(self, api_key: str):
            calls["api_key"] = api_key

        def chat(
            self,
            messages: list[dict[str, str]],
            system: str,
            temperature: float,
            max_tokens: int,
        ) -> str:
            calls["messages"] = messages
            calls["system"] = system
            calls["temperature"] = temperature
            calls["max_tokens"] = max_tokens
            return "dummy-response"

    monkeypatch.setattr(chat_module, "GPTClient", DummyGPTClient)

    # When: Sending POST request to chat endpoint
    resp = client.post("/api/chat", json=_base_payload())

    # Then: GPTClient receives expected payload and response is forwarded
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "dummy-response"
    assert calls["api_key"] == "test-key"
    assert calls["messages"][0]["role"] == "user"
    assert calls["messages"][0]["content"] == "hi"
    assert "親切なアシスタント" in calls["system"]
    assert "Context" in calls["system"]
    assert calls["temperature"] == 0.7
    assert calls["max_tokens"] == 1000


def test_chat_returns_500_when_gptclient_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test chat endpoint propagates 500 when GPT client raises.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If server does not return 500.
    """

    # Given: GPT client patched to raise at runtime
    client = _make_client()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingClient:
        def __init__(self, api_key: str) -> None:
            _ = api_key

        def chat(self, *args: Any, **kwargs: Any) -> str:
            raise RuntimeError("boom")

    monkeypatch.setattr(chat_module, "GPTClient", FailingClient)

    # When: Posting chat request
    resp = client.post("/api/chat", json=_base_payload())

    # Then: Endpoint returns 500 with friendly error message
    assert resp.status_code == 500
    data = resp.json()
    assert "チャットリクエストの処理中にエラーが発生しました" in data["detail"]
