from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.config import BaseConfig
from nook.common.exceptions import APIException, RetryException
from nook.common.http_client import AsyncHTTPClient


def make_response(
    status_code: int,
    *,
    json: dict | None = None,
    text: str | None = None,
    request: httpx.Request,
) -> httpx.Response:
    resp = httpx.Response(
        status_code,
        json=json,
        text=text,
        request=request,
        extensions={"elapsed": timedelta(0)},
    )
    # Consume the response to satisfy elapsed access checks
    resp.read()
    return resp


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _sleep(seconds: float):
        return None

    monkeypatch.setattr("nook.common.decorators.asyncio.sleep", _sleep)
    monkeypatch.setattr("nook.common.http_client.logger.debug", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def mock_elapsed(monkeypatch):
    monkeypatch.setattr(
        httpx.Response,
        "elapsed",
        property(lambda self: getattr(self, "_elapsed", timedelta(0))),
    )


@pytest_asyncio.fixture
async def client_factory():
    clients: list[AsyncHTTPClient] = []

    def _make(http2_handler, http1_handler=None):
        cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
        client = AsyncHTTPClient(config=cfg)
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(http2_handler),
            follow_redirects=True,
            http2=False,
        )
        client._http1_client = httpx.AsyncClient(
            transport=httpx.MockTransport(http1_handler or http2_handler),
            follow_redirects=True,
            http2=False,
        )
        clients.append(client)
        return client

    yield _make

    await asyncio.gather(*(c.close() for c in clients))


@pytest.mark.asyncio
async def test_get_success_uses_browser_headers(client_factory):
    seen_headers = {}

    async def http2_handler(request: httpx.Request):
        seen_headers.update(request.headers)
        return httpx.Response(200, json={"ok": True}, request=request)

    client = client_factory(http2_handler)

    resp = await client.get("https://example.com/ok")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert any(k.lower() == "user-agent" for k in seen_headers)
    assert "accept" in {k.lower() for k in seen_headers}


@pytest.mark.asyncio
async def test_get_stream_error_falls_back_to_http1(client_factory):
    calls = []

    async def http2_handler(request: httpx.Request):
        calls.append("http2")
        raise httpx.StreamError("reset")

    async def http1_handler(request: httpx.Request):
        calls.append("http1")
        return make_response(200, json={"version": "http1"}, request=request)

    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/stream")
    assert resp.json()["version"] == "http1"
    assert calls == ["http2", "http1"]


@pytest.mark.asyncio
async def test_get_422_fallback_http1_once(client_factory):
    calls = []

    async def http2_handler(request: httpx.Request):
        calls.append("http2")
        return make_response(422, request=request)

    async def http1_handler(request: httpx.Request):
        calls.append("http1")
        return make_response(200, json={"via": "http1"}, request=request)

    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/fallback-422")
    assert resp.json()["via"] == "http1"
    assert calls == ["http2", "http1"]


@pytest.mark.asyncio
async def test_get_403_browser_retry(client_factory):
    headers_seen = {}

    async def http2_handler(request: httpx.Request):
        return make_response(403, request=request)

    async def http1_handler(request: httpx.Request):
        headers_seen.update(request.headers)
        return make_response(200, json={"via": "browser"}, request=request)

    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/need-browser", headers={"X-Test": "1"})

    assert resp.json()["via"] == "browser"
    assert any(k.lower() == "x-test" and v == "1" for k, v in headers_seen.items())
    assert any(k.lower() == "user-agent" for k in headers_seen)


@pytest.mark.asyncio
async def test_get_raises_api_exception_on_http_error(client_factory):
    async def http2_handler(request: httpx.Request):
        return make_response(500, text="bad", request=request)

    client = client_factory(http2_handler)

    with pytest.raises(RetryException):
        await client.get("https://example.com/error")


@pytest.mark.asyncio
async def test_post_success_and_error(client_factory):
    async def http2_handler(request: httpx.Request):
        if request.url.path == "/post-ok":
            return make_response(201, json={"ok": True}, request=request)
        return make_response(502, text="fail", request=request)

    client = client_factory(http2_handler)

    ok = await client.post("https://example.com/post-ok", json={"x": 1})
    assert ok.status_code == 201
    assert ok.json() == {"ok": True}

    with pytest.raises(RetryException):
        await client.post("https://example.com/post-fail", json={"x": 1})


@pytest.mark.asyncio
async def test_get_json_and_text_wrappers(client_factory):
    async def http2_handler(request: httpx.Request):
        if request.url.path == "/json":
            return make_response(200, json={"value": 1}, request=request)
        return make_response(200, text="hello", request=request)

    client = client_factory(http2_handler)

    data = await client.get_json("https://example.com/json")
    assert data == {"value": 1}

    text = await client.get_text("https://example.com/text")
    assert text == "hello"
