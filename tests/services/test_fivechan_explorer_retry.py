"""FiveChanExplorer._get_with_retry() の単体テスト

リトライ機能付きHTTP GETリクエストのロジックを検証。
指数バックオフ、レート制限処理、エラーハンドリングをテスト。
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


@pytest.mark.asyncio
async def test_get_with_retry_success_on_first_attempt(tmp_path: Path) -> None:
    """Given: 正常なHTTPレスポンス
    When: _get_with_retry()を呼び出す
    Then: 最初の試行で成功し、レスポンスを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test content"

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_retry("https://example.com/test")

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 1


@pytest.mark.asyncio
async def test_get_with_retry_success_after_500_error(tmp_path: Path) -> None:
    """Given: 最初の試行が500エラー、2回目が成功
    When: _get_with_retry()を呼び出す
    Then: リトライ後に成功し、レスポンスを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_500 = Mock()
    mock_response_500.status_code = 500

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"test content"

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [mock_response_500, mock_response_200]
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_retry("https://example.com/test", max_retries=3)

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_with_retry_rate_limit_429(tmp_path: Path) -> None:
    """Given: 429レート制限エラーが発生
    When: _get_with_retry()を呼び出す
    Then: Retry-Afterヘッダーに従って待機後、リトライする
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_429 = Mock()
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "1"}

    mock_response_200 = Mock()
    mock_response_200.status_code = 200

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [mock_response_429, mock_response_200]
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_retry("https://example.com/test")

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_with_retry_exhaustion_of_retries(tmp_path: Path) -> None:
    """Given: すべての試行が500エラー
    When: _get_with_retry()を呼び出す
    Then: 最後のエラーレスポンスを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_500 = Mock()
    mock_response_500.status_code = 500

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response_500
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_retry("https://example.com/test", max_retries=2)

    # Verify
    assert result is not None
    assert result.status_code == 500
    assert mock_http_client.get.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_get_with_retry_exception_handling(tmp_path: Path) -> None:
    """Given: 最初の試行で例外、2回目で成功
    When: _get_with_retry()を呼び出す
    Then: リトライ後に成功する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_200 = Mock()
    mock_response_200.status_code = 200

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [
        httpx.RequestError("Network error", request=Mock()),
        mock_response_200,
    ]
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_retry("https://example.com/test")

    # Verify
    assert result is not None
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_get_with_retry_no_http_client(tmp_path: Path) -> None:
    """Given: http_clientがNone
    When: _get_with_retry()を呼び出す
    Then: Noneを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))
    service.http_client = None

    # Execute
    result = await service._get_with_retry("https://example.com/test")

    # Verify
    assert result is None


@pytest.mark.asyncio
async def test_get_with_retry_raises_exception_after_max_retries(tmp_path: Path) -> None:
    """Given: 毎回例外が発生
    When: _get_with_retry()を呼び出す
    Then: 最大リトライ到達時に例外を再送出する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    request = Mock()
    network_error = httpx.RequestError("Network error", request=request)

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [network_error, network_error, network_error]
    service.http_client = mock_http_client

    # Execute & Verify
    with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(httpx.RequestError):
        await service._get_with_retry("https://example.com/test", max_retries=2)
