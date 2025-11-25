"""FiveChanExplorer._get_with_403_tolerance() の単体テスト

403エラー耐性HTTP GETリクエストのロジックを検証。
複数の戦略を試行し、403エラーを回避する機能をテスト。
"""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


@pytest.mark.asyncio
async def test_get_with_403_tolerance_success_on_first_attempt(tmp_path):
    """Given: 正常なHTTPレスポンス
    When: _get_with_403_tolerance()を呼び出す
    Then: 最初の戦略で成功し、レスポンスを返す
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
    result = await service._get_with_403_tolerance("https://example.com/test", "test_board")

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 1


@pytest.mark.asyncio
async def test_get_with_403_tolerance_success_after_retry(tmp_path):
    """Given: 最初の戦略が403エラー、2番目の戦略が成功
    When: _get_with_403_tolerance()を呼び出す
    Then: リトライ後に成功し、レスポンスを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # 最初は403、2回目は200
    mock_response_403 = Mock()
    mock_response_403.status_code = 403

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"test content"

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [mock_response_403, mock_response_200]
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_403_tolerance("https://example.com/test", "test_board")

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_with_403_tolerance_exhaustion_of_retries(tmp_path):
    """Given: すべての戦略が403エラー
    When: _get_with_403_tolerance()を呼び出す
    Then: すべてのリトライを使い果たし、Noneを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_403 = Mock()
    mock_response_403.status_code = 403

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response_403
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_403_tolerance("https://example.com/test", "test_board")

    # Verify
    assert result is None
    assert mock_http_client.get.call_count == 3  # 3つの戦略すべて試行


@pytest.mark.asyncio
async def test_get_with_403_tolerance_exception_handling(tmp_path):
    """Given: HTTPリクエストで例外が発生
    When: _get_with_403_tolerance()を呼び出す
    Then: 例外をキャッチし、次の戦略を試行する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"test content"

    mock_http_client = AsyncMock()
    # 最初は例外、2回目は成功
    mock_http_client.get.side_effect = [
        httpx.RequestError("Network error", request=Mock()),
        mock_response_200,
    ]
    service.http_client = mock_http_client

    # Execute
    result = await service._get_with_403_tolerance("https://example.com/test", "test_board")

    # Verify
    assert result is not None
    assert result.status_code == 200
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_with_403_tolerance_no_http_client(tmp_path):
    """Given: http_clientがNone
    When: _get_with_403_tolerance()を呼び出す
    Then: Noneを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))
    service.http_client = None

    # Execute
    result = await service._get_with_403_tolerance("https://example.com/test", "test_board")

    # Verify
    assert result is None
