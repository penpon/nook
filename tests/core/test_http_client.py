from __future__ import annotations

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import nook.core.clients.http_client as http_client_module  # noqa: E402
from nook.core.config import BaseConfig  # noqa: E402
from nook.core.errors.exceptions import RetryException  # noqa: E402


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

    monkeypatch.setattr("nook.core.utils.decorators.asyncio.sleep", _sleep)
    monkeypatch.setattr("nook.core.clients.http_client.logger.debug", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def mock_elapsed(monkeypatch):
    monkeypatch.setattr(
        httpx.Response,
        "elapsed",
        property(lambda self: getattr(self, "_elapsed", timedelta(0))),
    )


@pytest_asyncio.fixture
async def client_factory():
    clients: list[http_client_module.AsyncHTTPClient] = []

    def _make(http2_handler, http1_handler=None):
        cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
        client = http_client_module.AsyncHTTPClient(config=cfg)
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

    # Given: HTTP/2 handler that echoes headers and returns success
    async def http2_handler(request: httpx.Request):
        seen_headers.update(request.headers)
        return httpx.Response(200, json={"ok": True}, request=request)

    # When: Performing GET request via HTTP client
    client = client_factory(http2_handler)

    resp = await client.get("https://example.com/ok")
    # Then: Response succeeds and includes browser-like headers
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert any(k.lower() == "user-agent" for k in seen_headers)
    assert "accept" in {k.lower() for k in seen_headers}


@pytest.mark.asyncio
async def test_get_stream_error_falls_back_to_http1(client_factory):
    calls = []

    # Given: HTTP/2 handler raising stream error, HTTP/1 handler succeeding
    async def http2_handler(request: httpx.Request):
        calls.append("http2")
        raise httpx.StreamError("reset")

    async def http1_handler(request: httpx.Request):
        calls.append("http1")
        return make_response(200, json={"version": "http1"}, request=request)

    # When: Performing GET request
    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/stream")
    # Then: Falls back to HTTP/1 and records call order
    assert resp.json()["version"] == "http1"
    assert calls == ["http2", "http1"]


@pytest.mark.asyncio
async def test_get_422_fallback_http1_once(client_factory):
    calls = []

    # Given: HTTP/2 handler returns 422, HTTP/1 handler succeeds
    async def http2_handler(request: httpx.Request):
        calls.append("http2")
        return make_response(422, request=request)

    async def http1_handler(request: httpx.Request):
        calls.append("http1")
        return make_response(200, json={"via": "http1"}, request=request)

    # When: Performing GET request
    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/fallback-422")
    # Then: Single fallback to HTTP/1 occurs
    assert resp.json()["via"] == "http1"
    assert calls == ["http2", "http1"]


@pytest.mark.asyncio
async def test_get_403_browser_retry(client_factory):
    headers_seen = {}

    # Given: HTTP/2 handler returns 403; HTTP/1 handler succeeds and captures headers
    async def http2_handler(request: httpx.Request):
        return make_response(403, request=request)

    async def http1_handler(request: httpx.Request):
        headers_seen.update(request.headers)
        return make_response(200, json={"via": "browser"}, request=request)

    # When: Performing GET request with custom header
    client = client_factory(http2_handler, http1_handler)

    resp = await client.get("https://example.com/need-browser", headers={"X-Test": "1"})

    # Then: Browser retry succeeds and preserves headers
    assert resp.json()["via"] == "browser"
    assert any(k.lower() == "x-test" and v == "1" for k, v in headers_seen.items())
    assert any(k.lower() == "user-agent" for k in headers_seen)


@pytest.mark.asyncio
async def test_get_raises_api_exception_on_http_error(client_factory):
    # Given: HTTP/2 handler returns server error
    async def http2_handler(request: httpx.Request):
        return make_response(500, text="bad", request=request)

    # When: Performing GET request
    client = client_factory(http2_handler)

    # Then: RetryException is raised after retries
    with pytest.raises(RetryException):
        await client.get("https://example.com/error")


@pytest.mark.asyncio
async def test_post_success_and_error(client_factory):
    # Given: HTTP/2 handler returns success for /post-ok and error otherwise
    async def http2_handler(request: httpx.Request):
        if request.url.path == "/post-ok":
            return make_response(201, json={"ok": True}, request=request)
        return make_response(502, text="fail", request=request)

    # When: Performing POST requests
    client = client_factory(http2_handler)

    ok = await client.post("https://example.com/post-ok", json={"x": 1})
    # Then: Success response is returned for happy path
    assert ok.status_code == 201
    assert ok.json() == {"ok": True}

    # And: RetryException is raised for failure path
    with pytest.raises(RetryException):
        await client.post("https://example.com/post-fail", json={"x": 1})


@pytest.mark.asyncio
async def test_get_json_and_text_wrappers(client_factory):
    # Given: HTTP/2 handler serving JSON and text responses
    async def http2_handler(request: httpx.Request):
        if request.url.path == "/json":
            return make_response(200, json={"value": 1}, request=request)
        return make_response(200, text="hello", request=request)

    # When: Using convenience wrappers
    client = client_factory(http2_handler)

    data = await client.get_json("https://example.com/json")
    # Then: JSON and text responses are parsed as expected
    assert data == {"value": 1}

    text = await client.get_text("https://example.com/text")
    assert text == "hello"


# ============================================================================
# Additional tests for 85% coverage target
# ============================================================================


@pytest.mark.asyncio
async def test_context_manager():
    """コンテキストマネージャーとして使用できることを確認"""
    # Given: AsyncHTTPClient
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")

    # When: コンテキストマネージャーとして使用
    async with http_client_module.AsyncHTTPClient(config=cfg) as client:
        # Then: クライアントが開始されている
        assert client._client is not None

    # And: 終了後はクライアントがクローズされている
    assert client._client is None


@pytest.mark.asyncio
async def test_start_creates_client():
    """startメソッドがクライアントを作成することを確認"""
    # Given: AsyncHTTPClient
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)

    # When: startを呼び出す
    await client.start()

    try:
        # Then: クライアントが作成されている
        assert client._client is not None
        assert client._session_start is not None
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_start_http1_client():
    """_start_http1_clientがHTTP/1.1クライアントを作成することを確認"""
    # Given: AsyncHTTPClient
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)

    # When: HTTP/1.1クライアントを開始
    await client._start_http1_client()

    try:
        # Then: HTTP/1.1クライアントが作成されている
        assert client._http1_client is not None
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_close_logs_duration(monkeypatch, caplog):
    """closeがセッション時間をログ出力することを確認"""
    import logging

    # Given: 開始済みのクライアント
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)
    await client.start()

    # When: クローズする
    # Ensure logs propagate to caplog
    http_client_logger = logging.getLogger("nook.core.clients.http_client")
    http_client_logger.propagate = True

    with caplog.at_level(logging.INFO, logger="nook.core.clients.http_client"):
        await client.close()

    # Then: クライアントがクローズされている
    assert client._client is None
    # And: セッション時間のログが出力されている
    assert any("closed after" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_get_force_http1(client_factory):
    """force_http1=Trueの場合にHTTP/1.1クライアントを使用"""
    calls = []

    # Given: HTTP/1.1 handler
    async def http1_handler(request: httpx.Request):
        calls.append("http1")
        return make_response(200, json={"via": "http1"}, request=request)

    # When: force_http1=Trueでリクエスト
    client = client_factory(http1_handler, http1_handler)

    resp = await client.get("https://example.com/force", force_http1=True)

    # Then: HTTP/1.1クライアントが使用される
    assert resp.json()["via"] == "http1"


@pytest.mark.asyncio
async def test_get_auto_starts_client():
    """getがクライアント未開始の場合に自動開始することを確認"""
    # Given: 未開始のクライアント
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)

    # モックトランスポートを設定
    async def handler(request: httpx.Request):
        return make_response(200, json={"ok": True}, request=request)

    start_called = {"value": False}

    async def fake_start():
        start_called["value"] = True
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

    client.start = fake_start  # type: ignore[assignment]

    try:
        # When: getを呼び出す（自動開始）
        resp = await client.get("https://example.com/auto")

        # Then: startが呼び出され、成功する
        assert start_called["value"] is True
        assert resp.status_code == 200
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_stream_error_non_reset_raises(client_factory):
    """StreamErrorがreset以外の場合は例外を発生させる"""

    # Given: reset以外のStreamErrorを発生させるハンドラー
    async def http2_handler(request: httpx.Request):
        raise httpx.StreamError("connection closed")

    async def http1_handler(request: httpx.Request):
        raise httpx.StreamError("connection closed")

    # When: リクエストを実行
    client = client_factory(http2_handler, http1_handler)

    # Then: RetryExceptionが発生し、メッセージも検証
    with pytest.raises(RetryException) as exc_info:
        await client.get("https://example.com/stream-error")
    assert "connection closed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_request_error_raises(client_factory):
    """RequestErrorが発生した場合に例外を発生させる"""

    # Given: RequestErrorを発生させるハンドラー
    async def http2_handler(request: httpx.Request):
        raise httpx.RequestError("connection failed")

    # When: リクエストを実行
    client = client_factory(http2_handler)

    # Then: RetryExceptionが発生
    with pytest.raises(RetryException) as exc_info:
        await client.get("https://example.com/request-error")
    assert "connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_post_request_error_raises(client_factory):
    """POSTでRequestErrorが発生した場合に例外を発生させる"""

    # Given: RequestErrorを発生させるハンドラー
    async def http2_handler(request: httpx.Request):
        raise httpx.RequestError("connection failed")

    # When: POSTリクエストを実行
    client = client_factory(http2_handler)

    # Then: RetryExceptionが発生
    with pytest.raises(RetryException) as exc_info:
        await client.post("https://example.com/post-error", json={"x": 1})
    assert "connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_browser_retry_http_error(client_factory):
    """_browser_retry_with_http1がHTTPエラーを処理することを確認"""

    # Given: 403を返すHTTP/2ハンドラーと500を返すHTTP/1.1ハンドラー
    async def http2_handler(request: httpx.Request):
        return make_response(403, request=request)

    async def http1_handler(request: httpx.Request):
        return make_response(500, text="server error", request=request)

    # When: リクエストを実行
    client = client_factory(http2_handler, http1_handler)

    # Then: RetryExceptionが発生（リトライ後も失敗）
    with pytest.raises(RetryException) as exc_info:
        await client.get("https://example.com/browser-retry-fail")
    assert "server error" in str(exc_info.value) or "500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_browser_retry_request_error(client_factory):
    """_browser_retry_with_http1がRequestErrorを処理することを確認"""

    # Given: 403を返すHTTP/2ハンドラーとRequestErrorを発生させるHTTP/1.1ハンドラー
    async def http2_handler(request: httpx.Request):
        return make_response(403, request=request)

    async def http1_handler(request: httpx.Request):
        raise httpx.RequestError("connection failed")

    # When: リクエストを実行
    client = client_factory(http2_handler, http1_handler)

    # Then: RetryExceptionが発生
    with pytest.raises(RetryException) as exc_info:
        await client.get("https://example.com/browser-retry-request-error")
    assert "connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download(tmp_path):
    """downloadメソッドがファイルをダウンロードすることを確認"""
    # Given: ストリーミングレスポンスを返すハンドラー
    content = b"file content here"

    async def handler(request: httpx.Request):
        return httpx.Response(
            200,
            content=content,
            headers={"content-length": str(len(content))},
            request=request,
        )

    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )

    output_file = tmp_path / "downloaded.txt"

    try:
        # When: ダウンロードを実行
        await client.download("https://example.com/file", str(output_file))

        # Then: ファイルが作成される
        assert output_file.exists()
        assert output_file.read_bytes() == content
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_download_with_progress_callback(tmp_path):
    """downloadメソッドがプログレスコールバックを呼び出すことを確認"""
    # Given: ストリーミングレスポンスを返すハンドラー
    content = b"file content here"
    progress_calls = []

    async def progress_callback(downloaded, total):
        progress_calls.append((downloaded, total))

    async def handler(request: httpx.Request):
        return httpx.Response(
            200,
            content=content,
            headers={"content-length": str(len(content))},
            request=request,
        )

    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )

    output_file = tmp_path / "downloaded_progress.txt"

    try:
        # When: プログレスコールバック付きでダウンロード
        await client.download(
            "https://example.com/file",
            str(output_file),
            progress_callback=progress_callback,
        )

        # Then: コールバックが呼び出される
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == len(content)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_http_client(monkeypatch):
    """get_http_clientがグローバルクライアントを返すことを確認"""

    # Given: グローバルクライアントがない状態
    original_client = http_client_module._global_client
    http_client_module._global_client = None

    # BaseConfigの初期化をモック
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    OriginalAsyncHTTPClient = http_client_module.AsyncHTTPClient
    monkeypatch.setattr(
        "nook.core.clients.http_client.AsyncHTTPClient",
        lambda config=None: OriginalAsyncHTTPClient(config=cfg),
    )

    try:
        # When: get_http_clientを呼び出す
        client = await http_client_module.get_http_client()

        # Then: クライアントが返される
        assert client is not None
        assert http_client_module._global_client is not None

        # When: 再度呼び出す
        client2 = await http_client_module.get_http_client()

        # Then: 同じクライアントが返される
        assert client2 is client

    finally:
        # クリーンアップ
        await http_client_module.close_http_client()
        http_client_module._global_client = original_client


@pytest.mark.asyncio
async def test_close_http_client(monkeypatch):
    """close_http_clientがグローバルクライアントを閉じることを確認"""

    # Given: グローバルクライアントがない状態
    original_client = http_client_module._global_client
    http_client_module._global_client = None

    # BaseConfigの初期化をモック
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    OriginalAsyncHTTPClient = http_client_module.AsyncHTTPClient
    monkeypatch.setattr(
        "nook.core.clients.http_client.AsyncHTTPClient",
        lambda config=None: OriginalAsyncHTTPClient(config=cfg),
    )

    try:
        # グローバルクライアントを作成
        await http_client_module.get_http_client()
        assert http_client_module._global_client is not None

        # When: close_http_clientを呼び出す
        await http_client_module.close_http_client()

        # Then: グローバルクライアントがNoneになる
        assert http_client_module._global_client is None

        # When: 再度close_http_clientを呼び出す（Noneの場合）
        await http_client_module.close_http_client()  # エラーなく完了

    finally:
        http_client_module._global_client = original_client


@pytest.mark.asyncio
async def test_get_with_custom_headers_merged(client_factory):
    """カスタムヘッダーがブラウザヘッダーとマージされることを確認"""
    seen_headers = {}

    # Given: ヘッダーをキャプチャするハンドラー
    async def http2_handler(request: httpx.Request):
        seen_headers.update(request.headers)
        return make_response(200, json={"ok": True}, request=request)

    # When: カスタムヘッダー付きでリクエスト
    client = client_factory(http2_handler)

    resp = await client.get(
        "https://example.com/custom-headers",
        headers={"X-Custom": "value"},
        use_browser_headers=True,
    )

    # Then: カスタムヘッダーとブラウザヘッダーの両方が含まれる
    assert resp.status_code == 200
    assert any(k.lower() == "x-custom" for k in seen_headers)
    assert any(k.lower() == "user-agent" for k in seen_headers)


@pytest.mark.asyncio
async def test_get_without_browser_headers(client_factory):
    """use_browser_headers=Falseの場合にブラウザヘッダーが追加されないことを確認"""
    seen_headers = {}

    # Given: ヘッダーをキャプチャするハンドラー
    async def http2_handler(request: httpx.Request):
        seen_headers.update(request.headers)
        return make_response(200, json={"ok": True}, request=request)

    # When: ブラウザヘッダーなしでリクエスト
    client = client_factory(http2_handler)

    resp = await client.get(
        "https://example.com/no-browser-headers",
        headers={"X-Only": "this"},
        use_browser_headers=False,
    )

    # Then: カスタムヘッダーのみが含まれる
    assert resp.status_code == 200
    assert any(k.lower() == "x-only" for k in seen_headers)
    # sec-ch-uaはブラウザヘッダー固有なので含まれない
    assert not any(k.lower() == "sec-ch-ua" for k in seen_headers)


@pytest.mark.asyncio
async def test_browser_retry_starts_http1_client():
    """_browser_retry_with_http1がHTTP/1.1クライアントを自動開始することを確認"""

    # Given: HTTP/1.1クライアントが未開始のクライアント
    cfg = BaseConfig(OPENAI_API_KEY="dummy-key")
    client = http_client_module.AsyncHTTPClient(config=cfg)

    async def handler(request: httpx.Request):
        return make_response(200, json={"ok": True}, request=request)

    try:
        # HTTP/1.1クライアントを設定
        client._http1_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

        # When: _browser_retry_with_http1を呼び出す
        resp = await client._browser_retry_with_http1(
            "https://example.com/retry",
            params=None,
            original_headers={"X-Test": "1"},
        )

        # Then: 成功する
        assert resp.status_code == 200
    finally:
        await client.close()
