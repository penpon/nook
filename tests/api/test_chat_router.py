from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app
from nook.api.routers import chat as chat_module


def _make_client() -> TestClient:
    return TestClient(app)


def _base_payload() -> dict:
    return {
        "topic_id": "topic-1",
        "message": "hello",
        "chat_history": [{"role": "user", "content": "hi"}],
        "markdown": "## Context",
    }


def test_chat_returns_dummy_response_when_api_key_missing(monkeypatch):
    client = _make_client()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = client.post("/api/chat", json=_base_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "OPENAI_API_KEY" in data["response"]
    assert "設定されていない" in data["response"]


def test_chat_calls_gptclient_with_expected_arguments(monkeypatch):
    client = _make_client()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    calls: dict = {}

    class DummyGPTClient:
        def __init__(self, api_key: str):
            calls["api_key"] = api_key

        def chat(self, messages, system, temperature, max_tokens):
            calls["messages"] = messages
            calls["system"] = system
            calls["temperature"] = temperature
            calls["max_tokens"] = max_tokens
            return "dummy-response"

    monkeypatch.setattr(chat_module, "GPTClient", DummyGPTClient)

    resp = client.post("/api/chat", json=_base_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "dummy-response"

    # GPTClient が期待どおりに呼び出されていることを確認
    assert calls["api_key"] == "test-key"
    assert calls["messages"][0]["role"] == "user"
    assert calls["messages"][0]["content"] == "hi"
    assert "親切なアシスタント" in calls["system"]
    assert "Context" in calls["system"]
    assert calls["temperature"] == 0.7
    assert calls["max_tokens"] == 1000


def test_chat_returns_500_when_gptclient_raises(monkeypatch):
    client = _make_client()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingClient:
        def __init__(self, api_key: str):
            pass

        def chat(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(chat_module, "GPTClient", FailingClient)

    resp = client.post("/api/chat", json=_base_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert "チャットリクエストの処理中にエラーが発生しました" in data["detail"]
