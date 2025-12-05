import asyncio
import types
from pathlib import Path

import pytest
from pydantic import SecretStr

from nook.common.base_service import BaseService
from nook.common.config import BaseConfig


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """必須環境変数をテスト用ダミーで埋める"""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")


class DummyConfig(BaseConfig):
    """テスト用の設定（必須キーをデフォルトで埋める）"""

    OPENAI_API_KEY: SecretStr = SecretStr("dummy-key")


class DummyService(BaseService):
    def __init__(self, request_delay: float = 0.05, config: BaseConfig | None = None):
        super().__init__("dummy", config=config or DummyConfig())
        self.request_delay = request_delay

    async def collect(self):
        return None


@pytest.mark.asyncio
async def test_save_data_uses_storage(monkeypatch, tmp_path: Path):
    service = DummyService()
    calls: dict[str, object] = {}

    async def fake_save(data, filename):
        calls["data"] = data
        calls["filename"] = filename
        return tmp_path / filename

    service.storage = types.SimpleNamespace(save=fake_save)

    path = await service.save_data({"x": 1}, "foo.json")

    assert path == tmp_path / "foo.json"
    assert calls == {"data": {"x": 1}, "filename": "foo.json"}


@pytest.mark.asyncio
async def test_rate_limit_uses_request_delay(monkeypatch):
    service = DummyService(request_delay=0.2)

    recorded: dict[str, float] = {}

    async def fake_sleep(delay):
        recorded["delay"] = delay

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await service.rate_limit()

    assert recorded["delay"] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_setup_http_client_called_once(monkeypatch):
    service = DummyService()
    sentinel_client = object()
    calls = {"count": 0}

    async def fake_get_http_client():
        calls["count"] += 1
        return sentinel_client

    monkeypatch.setattr("nook.common.http_client.get_http_client", fake_get_http_client)

    await service.setup_http_client()
    first_client = service.http_client

    # 再呼び出しでも新規取得しない
    await service.setup_http_client()

    assert first_client is sentinel_client
    assert service.http_client is sentinel_client
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_initialize_calls_setup_http_client(monkeypatch):
    service = DummyService()
    sentinel_client = object()
    calls = {"count": 0}

    async def fake_setup():
        calls["count"] += 1
        service.http_client = sentinel_client

    monkeypatch.setattr(service, "setup_http_client", fake_setup)

    await service.initialize()

    assert calls["count"] == 1
    assert service.http_client is sentinel_client
