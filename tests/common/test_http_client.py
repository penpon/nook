"""
nook/common/http_client.py のテスト

テスト観点:
- AsyncHTTPClientの初期化とセッション管理
- HTTP GET/POSTリクエスト
- HTTP/2・HTTP/1.1対応とフォールバック
- リトライロジック
- タイムアウト処理
- エラーハンドリング
- cloudscraperフォールバック
- 接続プール管理
- グローバルHTTPクライアント管理
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from nook.common.config import BaseConfig
from nook.common.exceptions import APIException, RetryException
from nook.common.http_client import (
    AsyncHTTPClient,
    close_http_client,
    get_http_client,
)

# =============================================================================
# 1. 初期化とセッション管理のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_with_default_config():
    """
    Given: configを指定しない
    When: AsyncHTTPClientを初期化
    Then: デフォルトのBaseConfigが使用される
    """
    client = AsyncHTTPClient()
    assert client.config is not None
    assert isinstance(client.config, BaseConfig)
    assert client._client is None
    assert client._http1_client is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_with_custom_config():
    """
    Given: カスタムBaseConfigを指定
    When: AsyncHTTPClientを初期化
    Then: カスタム設定が反映される
    """
    custom_config = BaseConfig()
    custom_config.REQUEST_TIMEOUT = 60
    client = AsyncHTTPClient(config=custom_config)
    assert client.config.REQUEST_TIMEOUT == 60
    assert client.timeout.read == 60


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_session():
    """
    Given: AsyncHTTPClientインスタンス
    When: start()を呼び出す
    Then: _clientが初期化され、_session_startが設定される
    """
    client = AsyncHTTPClient()
    await client.start()
    assert client._client is not None
    assert isinstance(client._client, httpx.AsyncClient)
    assert client._session_start is not None
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_http1_session():
    """
    Given: AsyncHTTPClientインスタンス
    When: _start_http1_client()を呼び出す
    Then: _http1_clientが初期化される
    """
    client = AsyncHTTPClient()
    await client._start_http1_client()
    assert client._http1_client is not None
    assert isinstance(client._http1_client, httpx.AsyncClient)
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_session():
    """
    Given: 開始されたセッション
    When: close()を呼び出す
    Then: 両クライアントがクローズされ、Noneになる
    """
    client = AsyncHTTPClient()
    await client.start()
    await client._start_http1_client()
    await client.close()
    assert client._client is None
    assert client._http1_client is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager():
    """
    Given: AsyncHTTPClientをコンテキストマネージャーで使用
    When: async withブロックを実行
    Then: 自動的にstart/closeが呼ばれる
    """
    async with AsyncHTTPClient() as client:
        assert client._client is not None
    # コンテキスト終了後はクローズされる
    assert client._client is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_duration_logging():
    """
    Given: セッション開始
    When: closeを呼び出す
    Then: ログにセッション時間が記録される
    """
    client = AsyncHTTPClient()
    await client.start()
    await asyncio.sleep(0.1)
    with patch("nook.common.http_client.logger") as mock_logger:
        await client.close()
        # ログが呼ばれたことを確認
        assert any(
            "session closed" in str(call).lower()
            for call in mock_logger.info.call_args_list
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_start_session():
    """
    Given: 既に開始されたセッション
    When: start()を2回呼び出す
    Then: 2回目は何もしない（既存のクライアントを維持）
    """
    client = AsyncHTTPClient()
    await client.start()
    first_client = client._client
    await client.start()
    assert client._client is first_client
    await client.close()


# =============================================================================
# 2. get_browser_headersのテスト
# =============================================================================


@pytest.mark.unit
def test_get_browser_headers():
    """
    Given: get_browser_headers()を呼び出す
    When: staticメソッドを実行
    Then: User-Agent等を含むヘッダー辞書が返される
    """
    headers = AsyncHTTPClient.get_browser_headers()
    assert isinstance(headers, dict)
    assert "User-Agent" in headers
    assert "Chrome" in headers["User-Agent"]


@pytest.mark.unit
def test_browser_headers_contains_required_keys():
    """
    Given: get_browser_headers()を呼び出す
    When: 返されたヘッダーを検証
    Then: 必須キーが存在する
    """
    headers = AsyncHTTPClient.get_browser_headers()
    required_keys = ["User-Agent", "Accept", "Accept-Language", "Accept-Encoding"]
    for key in required_keys:
        assert key in headers


# =============================================================================
# 3. GETリクエストのテスト（正常系）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_http2_success(respx_mock):
    """
    Given: 正常なHTTPエンドポイント
    When: GETリクエストを送信（HTTP/2）
    Then: 200レスポンスが返される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_http1_success(respx_mock):
    """
    Given: 正常なHTTPエンドポイント
    When: force_http1=Trueでリクエスト
    Then: 200レスポンスが返され、HTTP/1.1が使用される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api", force_http1=True)
        assert response.status_code == 200
        assert client._http1_client is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_with_params(respx_mock):
    """
    Given: クエリパラメータを指定
    When: GETリクエストを送信
    Then: パラメータ付きでリクエストが成功する
    """
    respx_mock.get("https://example.com/api", params={"key": "value"}).mock(
        return_value=httpx.Response(200, json={"result": "success"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api", params={"key": "value"})
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_with_custom_headers(respx_mock):
    """
    Given: カスタムヘッダーを指定
    When: GETリクエストを送信
    Then: カスタムヘッダーが送信される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get(
            "https://example.com/api",
            headers={"X-Custom": "test"},
            use_browser_headers=False,
        )
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_with_browser_headers(respx_mock):
    """
    Given: use_browser_headers=True（デフォルト）
    When: GETリクエストを送信
    Then: ブラウザヘッダーが自動設定される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_without_browser_headers(respx_mock):
    """
    Given: use_browser_headers=False, headers=None
    When: GETリクエストを送信
    Then: ブラウザヘッダーなしでリクエストされる
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get(
            "https://example.com/api", use_browser_headers=False, headers=None
        )
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_merge_browser_and_custom_headers(respx_mock):
    """
    Given: use_browser_headers=True & カスタムヘッダー指定
    When: GETリクエストを送信
    Then: ブラウザヘッダーとカスタムヘッダーが統合される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get(
            "https://example.com/api",
            headers={"X-Custom": "test"},
            use_browser_headers=True,
        )
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_follows_redirect(respx_mock):
    """
    Given: 301リダイレクトするURL
    When: GETリクエストを送信
    Then: 自動的にリダイレクト先に移動する
    """
    respx_mock.get("https://example.com/old").mock(
        return_value=httpx.Response(
            301, headers={"Location": "https://example.com/new"}
        )
    )
    respx_mock.get("https://example.com/new").mock(
        return_value=httpx.Response(200, json={"status": "redirected"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/old")
        assert response.status_code == 200


# =============================================================================
# 4. GETリクエストのテスト（異常系 - HTTPエラー）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_404_error(respx_mock):
    """
    Given: 404を返すエンドポイント
    When: GETリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.get("https://example.com/notfound").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/notfound")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_500_error(respx_mock):
    """
    Given: 500を返すエンドポイント
    When: GETリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.get("https://example.com/error").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/error")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_503_error(respx_mock):
    """
    Given: 503を返すエンドポイント
    When: GETリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.get("https://example.com/unavailable").mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/unavailable")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_403_cloudscraper_success(respx_mock):
    """
    Given: 403エラー後、cloudscraperが成功
    When: GETリクエストを送信
    Then: 200レスポンスが返される（cloudscraperフォールバック）
    """
    respx_mock.get("https://example.com/protected").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Success"
    mock_response.content = b"Success"
    mock_response.headers = {}
    mock_response.json.return_value = {"status": "ok"}

    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.return_value = mock_response
            response = await client.get("https://example.com/protected")
            assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_403_cloudscraper_failure(respx_mock):
    """
    Given: 403エラー後、cloudscraperも失敗
    When: GETリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.get("https://example.com/protected").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.side_effect = Exception("Cloudscraper failed")
            with pytest.raises(RetryException):
                await client.get("https://example.com/protected")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_422_http1_fallback_success(respx_mock):
    """
    Given: HTTP/2で422エラー、HTTP/1.1で成功
    When: GETリクエストを送信
    Then: 200レスポンスが返される（HTTP/1.1フォールバック）
    """
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(422, text="Unprocessable Entity")
        else:
            return httpx.Response(200, json={"status": "ok"})

    respx_mock.get("https://example.com/api").mock(side_effect=side_effect)

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_422_http1_fallback_failure(respx_mock):
    """
    Given: HTTP/2で422エラー、HTTP/1.1でも422
    When: GETリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(422, text="Unprocessable Entity")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_422_no_retry_http1(respx_mock):
    """
    Given: 422エラー、_retry_http1=False
    When: GETリクエストを送信
    Then: RetryException発生（HTTP/1.1リトライなし）
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(422, text="Unprocessable Entity")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api", _retry_http1=False)


# =============================================================================
# 5. GETリクエストのテスト（異常系 - ネットワークエラー）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_timeout_error(respx_mock):
    """
    Given: タイムアウトが発生
    When: GETリクエストを送信
    Then: リトライ後、RetryException発生
    """
    respx_mock.get("https://example.com/slow").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/slow")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_connection_error(respx_mock):
    """
    Given: 接続エラーが発生
    When: GETリクエストを送信
    Then: リトライ後、RetryException発生
    """
    respx_mock.get("https://example.com/unreachable").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/unreachable")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_stream_error_http1_fallback_success(respx_mock):
    """
    Given: StreamError発生後、HTTP/1.1で成功
    When: GETリクエストを送信
    Then: 200レスポンスが返される（HTTP/1.1フォールバック）
    """
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.StreamError("Stream reset")
        else:
            return httpx.Response(200, json={"status": "ok"})

    respx_mock.get("https://example.com/api").mock(side_effect=side_effect)

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_stream_error_http1_fallback_failure(respx_mock):
    """
    Given: StreamError発生、HTTP/1.1でも失敗
    When: GETリクエストを送信
    Then: RetryException発生
    """
    respx_mock.get("https://example.com/api").mock(
        side_effect=httpx.StreamError("Stream reset")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_stream_error_no_fallback_when_forced_http1(respx_mock):
    """
    Given: force_http1=True時にStreamError発生
    When: GETリクエストを送信
    Then: RetryException発生（フォールバックなし）
    """
    respx_mock.get("https://example.com/api").mock(
        side_effect=httpx.StreamError("Stream error")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api", force_http1=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_request_general_request_error(respx_mock):
    """
    Given: 一般的なRequestErrorが発生
    When: GETリクエストを送信
    Then: RetryException発生
    """
    respx_mock.get("https://example.com/api").mock(
        side_effect=httpx.RequestError("Request failed")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api")


# =============================================================================
# 6. POSTリクエストのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_with_json_success(respx_mock):
    """
    Given: JSONデータを指定
    When: POSTリクエストを送信
    Then: 200レスポンスが返される
    """
    respx_mock.post("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"result": "created"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.post("https://example.com/api", json={"key": "value"})
        assert response.status_code == 200
        assert response.json() == {"result": "created"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_with_data_success(respx_mock):
    """
    Given: フォームデータを指定
    When: POSTリクエストを送信
    Then: 200レスポンスが返される
    """
    respx_mock.post("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"result": "submitted"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.post("https://example.com/api", data={"key": "value"})
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_with_bytes_success(respx_mock):
    """
    Given: バイトデータを指定
    When: POSTリクエストを送信
    Then: 200レスポンスが返される
    """
    respx_mock.post("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"result": "uploaded"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.post("https://example.com/api", data=b"binary data")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_with_custom_headers(respx_mock):
    """
    Given: カスタムヘッダーを指定
    When: POSTリクエストを送信
    Then: カスタムヘッダーが送信される
    """
    respx_mock.post("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"result": "ok"})
    )

    async with AsyncHTTPClient() as client:
        response = await client.post(
            "https://example.com/api",
            json={"key": "value"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_404_error(respx_mock):
    """
    Given: 404を返すエンドポイント
    When: POSTリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.post("https://example.com/notfound").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.post("https://example.com/notfound", json={"key": "value"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_500_error(respx_mock):
    """
    Given: 500を返すエンドポイント
    When: POSTリクエストを送信
    Then: RetryException発生（リトライ後）
    """
    respx_mock.post("https://example.com/error").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.post("https://example.com/error", json={"key": "value"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_timeout_error(respx_mock):
    """
    Given: タイムアウトが発生
    When: POSTリクエストを送信
    Then: リトライ後、RetryException発生
    """
    respx_mock.post("https://example.com/slow").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.post("https://example.com/slow", json={"key": "value"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_request_connection_error(respx_mock):
    """
    Given: 接続エラーが発生
    When: POSTリクエストを送信
    Then: リトライ後、RetryException発生
    """
    respx_mock.post("https://example.com/unreachable").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.post("https://example.com/unreachable", json={"key": "value"})


# =============================================================================
# 7. ヘルパーメソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_success(respx_mock):
    """
    Given: JSONレスポンスを返すエンドポイント
    When: get_json()を呼び出す
    Then: JSON辞書が返される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"key": "value"})
    )

    async with AsyncHTTPClient() as client:
        result = await client.get_json("https://example.com/api")
        assert result == {"key": "value"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_invalid_json(respx_mock):
    """
    Given: 不正なJSONを返すエンドポイント
    When: get_json()を呼び出す
    Then: JSONDecodeError発生
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, text="invalid json")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(Exception):  # JSONDecodeError or similar
            await client.get_json("https://example.com/api")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_text_success(respx_mock):
    """
    Given: テキストレスポンスを返すエンドポイント
    When: get_text()を呼び出す
    Then: テキスト文字列が返される
    """
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, text="Hello, World!")
    )

    async with AsyncHTTPClient() as client:
        result = await client.get_text("https://example.com/api")
        assert result == "Hello, World!"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_file_success(respx_mock):
    """
    Given: ダウンロード可能なファイル
    When: download()を呼び出す
    Then: ファイルがダウンロードされる
    """
    respx_mock.get("https://example.com/file.zip").mock(
        return_value=httpx.Response(
            200, content=b"file content", headers={"content-length": "12"}
        )
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "downloaded.zip"
        async with AsyncHTTPClient() as client:
            await client.download("https://example.com/file.zip", str(output_path))
            assert output_path.exists()
            assert output_path.read_bytes() == b"file content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_with_progress_callback(respx_mock):
    """
    Given: プログレスコールバックを指定
    When: download()を呼び出す
    Then: コールバックが呼ばれる
    """
    respx_mock.get("https://example.com/file.zip").mock(
        return_value=httpx.Response(
            200, content=b"file content", headers={"content-length": "12"}
        )
    )

    progress_called = False

    async def progress_callback(downloaded, total):
        nonlocal progress_called
        progress_called = True

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "downloaded.zip"
        async with AsyncHTTPClient() as client:
            await client.download(
                "https://example.com/file.zip",
                str(output_path),
                progress_callback=progress_callback,
            )
            assert progress_called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_404_error(respx_mock):
    """
    Given: 404を返すエンドポイント
    When: download()を呼び出す
    Then: HTTPStatusError発生
    """
    respx_mock.get("https://example.com/notfound.zip").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "downloaded.zip"
        async with AsyncHTTPClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.download(
                    "https://example.com/notfound.zip", str(output_path)
                )


# =============================================================================
# 8. cloudscraperフォールバックのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cloudscraper_fallback_success():
    """
    Given: cloudscraperが成功するレスポンスを返す
    When: _cloudscraper_fallback()を呼び出す
    Then: httpx互換レスポンスが返される
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Success"
    mock_response.content = b"Success"
    mock_response.headers = {}
    mock_response.json.return_value = {"status": "ok"}

    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.return_value = mock_response
            response = await client._cloudscraper_fallback(
                "https://example.com/protected"
            )
            assert response.status_code == 200
            assert response.text == "Success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cloudscraper_fallback_timeout():
    """
    Given: cloudscraperでタイムアウト発生
    When: _cloudscraper_fallback()を呼び出す
    Then: APIException発生、status_code=403
    """
    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.side_effect = Exception("timeout")
            with pytest.raises(APIException) as exc_info:
                await client._cloudscraper_fallback("https://example.com/protected")
            assert exc_info.value.status_code == 403


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cloudscraper_fallback_ssl_error():
    """
    Given: cloudscraperでSSLエラー発生
    When: _cloudscraper_fallback()を呼び出す
    Then: APIException発生、status_code=403
    """
    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.side_effect = Exception("SSL handshake error")
            with pytest.raises(APIException) as exc_info:
                await client._cloudscraper_fallback("https://example.com/protected")
            assert exc_info.value.status_code == 403


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cloudscraper_fallback_403_error():
    """
    Given: cloudscraperでも403エラー
    When: _cloudscraper_fallback()を呼び出す
    Then: APIException発生、status_code=403
    """
    async with AsyncHTTPClient() as client:
        with patch("cloudscraper.create_scraper") as mock_scraper:
            mock_scraper.return_value.get.side_effect = Exception("403 Forbidden")
            with pytest.raises(APIException) as exc_info:
                await client._cloudscraper_fallback("https://example.com/protected")
            assert exc_info.value.status_code == 403


@pytest.mark.unit
def test_convert_to_httpx_response():
    """
    Given: requests.Responseオブジェクト
    When: _convert_to_httpx_response()を呼び出す
    Then: CloudscraperResponseAdapterが作成される
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Success"
    mock_response.content = b"Success"
    mock_response.headers = {}

    client = AsyncHTTPClient()
    adapter = client._convert_to_httpx_response(mock_response)
    assert adapter.status_code == 200
    assert adapter.text == "Success"


@pytest.mark.unit
def test_cloudscraper_response_adapter_json():
    """
    Given: CloudscraperResponseAdapter
    When: json()メソッドを呼び出す
    Then: JSON辞書が返される
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{"key": "value"}'
    mock_response.content = b'{"key": "value"}'
    mock_response.headers = {}
    mock_response.json.return_value = {"key": "value"}

    client = AsyncHTTPClient()
    adapter = client._convert_to_httpx_response(mock_response)
    assert adapter.json() == {"key": "value"}


@pytest.mark.unit
def test_cloudscraper_response_adapter_raise_for_status_success():
    """
    Given: status_code=200のCloudscraperResponseAdapter
    When: raise_for_status()を呼び出す
    Then: 例外が発生しない
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Success"
    mock_response.content = b"Success"
    mock_response.headers = {}

    client = AsyncHTTPClient()
    adapter = client._convert_to_httpx_response(mock_response)
    adapter.raise_for_status()  # 例外が発生しないことを確認


@pytest.mark.unit
def test_cloudscraper_response_adapter_raise_for_status_error():
    """
    Given: status_code=404のCloudscraperResponseAdapter
    When: raise_for_status()を呼び出す
    Then: HTTPStatusError発生
    """
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.content = b"Not Found"
    mock_response.headers = {}

    client = AsyncHTTPClient()
    adapter = client._convert_to_httpx_response(mock_response)
    with pytest.raises(httpx.HTTPStatusError):
        adapter.raise_for_status()


# =============================================================================
# 9. グローバル関数のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_http_client_first_call():
    """
    Given: _global_client=None
    When: get_http_client()を呼び出す
    Then: 新規クライアントが作成され返される
    """
    # グローバル変数をリセット
    import nook.common.http_client as http_client_module

    http_client_module._global_client = None

    client = await get_http_client()
    assert client is not None
    assert isinstance(client, AsyncHTTPClient)

    # クリーンアップ
    await close_http_client()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_http_client_singleton():
    """
    Given: _global_client既存
    When: get_http_client()を2回呼び出す
    Then: 同じインスタンスが返される
    """
    import nook.common.http_client as http_client_module

    http_client_module._global_client = None

    client1 = await get_http_client()
    client2 = await get_http_client()
    assert client1 is client2

    # クリーンアップ
    await close_http_client()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_http_client():
    """
    Given: _global_client存在
    When: close_http_client()を呼び出す
    Then: クライアントがクローズされ、Noneになる
    """
    import nook.common.http_client as http_client_module

    http_client_module._global_client = None

    await get_http_client()
    await close_http_client()

    assert http_client_module._global_client is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_http_client_already_none():
    """
    Given: _global_client=None
    When: close_http_client()を呼び出す
    Then: 何もしない（エラーなし）
    """
    import nook.common.http_client as http_client_module

    http_client_module._global_client = None

    await close_http_client()  # エラーが発生しないことを確認
    assert http_client_module._global_client is None


# =============================================================================
# 10. リトライロジックのテスト（@handle_errors）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_retry_success_on_second_attempt(respx_mock):
    """
    Given: 1回目エラー、2回目成功
    When: GETリクエストを送信
    Then: 200レスポンスが返される（リトライ成功）
    """
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Connection failed")
        else:
            return httpx.Response(200, json={"status": "ok"})

    respx_mock.get("https://example.com/api").mock(side_effect=side_effect)

    async with AsyncHTTPClient() as client:
        response = await client.get("https://example.com/api")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_retry_max_retries_exceeded(respx_mock):
    """
    Given: 3回すべて失敗
    When: GETリクエストを送信
    Then: RetryException発生（リトライ最大回数到達）
    """
    respx_mock.get("https://example.com/api").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.get("https://example.com/api")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_retry_success_on_second_attempt(respx_mock):
    """
    Given: 1回目エラー、2回目成功
    When: POSTリクエストを送信
    Then: 200レスポンスが返される（リトライ成功）
    """
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Connection failed")
        else:
            return httpx.Response(200, json={"result": "created"})

    respx_mock.post("https://example.com/api").mock(side_effect=side_effect)

    async with AsyncHTTPClient() as client:
        response = await client.post("https://example.com/api", json={"key": "value"})
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_retry_max_retries_exceeded(respx_mock):
    """
    Given: 3回すべて失敗
    When: POSTリクエストを送信
    Then: RetryException発生（リトライ最大回数到達）
    """
    respx_mock.post("https://example.com/api").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with AsyncHTTPClient() as client:
        with pytest.raises(RetryException):
            await client.post("https://example.com/api", json={"key": "value"})


# =============================================================================
# 11. タイムアウト設定のテスト
# =============================================================================


@pytest.mark.unit
def test_default_timeout_configuration():
    """
    Given: config.REQUEST_TIMEOUT=30（デフォルト）
    When: AsyncHTTPClientを初期化
    Then: timeoutが正しく設定される
    """
    config = BaseConfig()
    config.REQUEST_TIMEOUT = 30
    client = AsyncHTTPClient(config=config)
    assert client.timeout.read == 30


@pytest.mark.unit
def test_custom_timeout_configuration():
    """
    Given: config.REQUEST_TIMEOUT=60（カスタム）
    When: AsyncHTTPClientを初期化
    Then: カスタムタイムアウトが反映される
    """
    config = BaseConfig()
    config.REQUEST_TIMEOUT = 60
    client = AsyncHTTPClient(config=config)
    assert client.timeout.read == 60


@pytest.mark.unit
def test_timeout_zero_seconds():
    """
    Given: REQUEST_TIMEOUT=0（境界値）
    When: AsyncHTTPClientを初期化
    Then: タイムアウト0が設定される
    """
    config = BaseConfig()
    config.REQUEST_TIMEOUT = 0
    client = AsyncHTTPClient(config=config)
    assert client.timeout.read == 0


@pytest.mark.unit
def test_timeout_large_value():
    """
    Given: REQUEST_TIMEOUT=99999（極大値）
    When: AsyncHTTPClientを初期化
    Then: 設定が反映される
    """
    config = BaseConfig()
    config.REQUEST_TIMEOUT = 99999
    client = AsyncHTTPClient(config=config)
    assert client.timeout.read == 99999


# =============================================================================
# 12. 接続プール管理のテスト
# =============================================================================


@pytest.mark.unit
def test_connection_pool_limits():
    """
    Given: AsyncHTTPClientを初期化
    When: limitsを確認
    Then: max_connections=100等が設定される
    """
    client = AsyncHTTPClient()
    assert client.limits.max_connections == 100
    assert client.limits.max_keepalive_connections == 20


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_reuse_multiple_requests(respx_mock):
    """
    Given: 同一ホストへ複数回リクエスト
    When: 複数のGETリクエストを送信
    Then: 接続が再利用される（エラーなく完了）
    """
    respx_mock.get("https://example.com/api1").mock(
        return_value=httpx.Response(200, json={"result": "1"})
    )
    respx_mock.get("https://example.com/api2").mock(
        return_value=httpx.Response(200, json={"result": "2"})
    )
    respx_mock.get("https://example.com/api3").mock(
        return_value=httpx.Response(200, json={"result": "3"})
    )

    async with AsyncHTTPClient() as client:
        response1 = await client.get("https://example.com/api1")
        response2 = await client.get("https://example.com/api2")
        response3 = await client.get("https://example.com/api3")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
