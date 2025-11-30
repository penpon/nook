"""nook/services/fivechan_explorer/fivechan_explorer.py の単体テスト

FiveChanExplorer内部メソッドのロジックを検証するunit testスイート。
Integration testではカバーしきれない詳細なエラーハンドリングと境界条件を検証。

テスト対象:
- _get_with_403_tolerance: 403エラー耐性HTTP GETリクエスト
- _get_subject_txt_data: subject.txt形式でスレッド一覧を取得
- _get_thread_posts_from_dat: .datファイルから投稿を取得
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.fivechan_explorer.fivechan_explorer import (
    FiveChanExplorer,
)

# =============================================================================
# テスト対象: _get_with_403_tolerance
# =============================================================================


@pytest.mark.asyncio
async def test_get_with_403_tolerance_success_on_first_attempt(tmp_path: Path) -> None:
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
async def test_get_with_403_tolerance_success_after_retry(tmp_path: Path) -> None:
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
async def test_get_with_403_tolerance_exhaustion_of_retries(tmp_path: Path) -> None:
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
async def test_get_with_403_tolerance_exception_handling(tmp_path: Path) -> None:
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
async def test_get_with_403_tolerance_no_http_client(tmp_path: Path) -> None:
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


# =============================================================================
# テスト対象: _get_subject_txt_data
# =============================================================================


@pytest.mark.asyncio
async def test_get_subject_txt_data_parse_valid_subject_txt(tmp_path: Path) -> None:
    """Given: 正常なsubject.txtレスポンス
    When: _get_subject_txt_data()を呼び出す
    Then: スレッド情報のリストを正しく解析して返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # subject.txt形式のデータ（Shift_JISでエンコード）
    subject_txt_unicode = "1577836800.dat<>【AI】ChatGPT (100)\n1577836900.dat<>機械学習 (50)\n"
    subject_txt_content = subject_txt_unicode.encode("shift_jis")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_txt_content

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert len(result) == 2
    assert result[0]["timestamp"] == "1577836800"
    assert "AI" in result[0]["title"]
    assert result[0]["post_count"] == 100
    assert result[1]["timestamp"] == "1577836900"
    assert result[1]["post_count"] == 50


@pytest.mark.asyncio
async def test_get_subject_txt_data_handle_decoding_errors_shift_jis(tmp_path: Path) -> None:
    """Given: Shift_JISでエンコードされたsubject.txt
    When: _get_subject_txt_data()を呼び出す
    Then: 正しくデコードしてスレッド情報を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Shift_JISでエンコード
    subject_txt_content = "1577836800.dat<>テストスレッド (10)\n".encode("shift_jis")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_txt_content

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert len(result) == 1
    assert result[0]["timestamp"] == "1577836800"
    assert "テストスレッド" in result[0]["title"]


@pytest.mark.asyncio
async def test_get_subject_txt_data_handle_decoding_errors_cp932(tmp_path: Path) -> None:
    """Given: CP932でエンコードされたsubject.txt（Shift_JISデコード失敗）
    When: _get_subject_txt_data()を呼び出す
    Then: CP932フォールバックでデコードに成功する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # CP932特有の文字を含むデータでShift_JISデコード失敗→CP932フォールバック
    content_mock = Mock()

    def decode_side_effect(encoding: str, errors: str = "strict") -> str:
        if encoding == "shift_jis":
            raise UnicodeDecodeError("shift_jis", b"", 0, 1, "decode error")
        return "1577836800.dat<>①テストスレッド (10)\n"

    content_mock.decode.side_effect = decode_side_effect

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = content_mock

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert len(result) == 1
    assert result[0]["timestamp"] == "1577836800"


@pytest.mark.asyncio
async def test_get_subject_txt_data_handle_empty_data(tmp_path: Path) -> None:
    """Given: 空のsubject.txtレスポンス
    When: _get_subject_txt_data()を呼び出す
    Then: 空のリストを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b""

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert result == []


@pytest.mark.asyncio
async def test_get_subject_txt_data_handle_malformed_data(tmp_path: Path) -> None:
    """Given: 不正な形式のsubject.txt
    When: _get_subject_txt_data()を呼び出す
    Then: パース可能な行のみを返し、不正な行はスキップする
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # 正常な行と不正な行の混在
    subject_txt_content = (
        b"1577836800.dat<>Valid Thread (10)\n"
        b"invalid line without dat extension\n"
        b"1577836900.dat<>Another Valid (20)\n"
        b"no_angle_brackets.dat\n"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_txt_content

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert len(result) == 2  # 不正な行2つはスキップされる
    assert result[0]["timestamp"] == "1577836800"
    assert result[1]["timestamp"] == "1577836900"


@pytest.mark.asyncio
async def test_get_subject_txt_data_network_error_all_servers_fail(tmp_path: Path) -> None:
    """Given: すべてのサーバーでネットワークエラー
    When: _get_subject_txt_data()を呼び出す
    Then: 空のリストを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_client.get.side_effect = httpx.RequestError("Network error", request=Mock())

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert result == []


@pytest.mark.asyncio
async def test_get_subject_txt_data_404_error(tmp_path: Path) -> None:
    """Given: サーバーが404エラーを返す
    When: _get_subject_txt_data()を呼び出す
    Then: 次のサーバーを試行する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response_404 = Mock()
    mock_response_404.status_code = 404

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"1577836800.dat<>Test Thread (10)\n"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    # 最初のサーバーは404、2番目のサーバーは成功
    mock_client.get.side_effect = [mock_response_404, mock_response_200]

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Execute
        result = await service._get_subject_txt_data("ai")

    # Verify
    assert len(result) == 1
    assert result[0]["timestamp"] == "1577836800"


# =============================================================================
# テスト対象: _get_thread_posts_from_dat
# =============================================================================


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_parse_valid_dat(tmp_path: Path) -> None:
    """Given: 正常な.datファイルレスポンス
    When: _get_thread_posts_from_dat()を呼び出す
    Then: 投稿リストを正しく解析して返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # .dat形式: name<>mail<>date<>content<>title
    dat_content = (
        "名無しさん<>sage<>2020/01/01(水) 12:34:56<>これはテスト投稿です<>\n"
        "テスターB<><>2020/01/01(水) 12:35:00<>返信テストです<>\n"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("shift_jis")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert error is None
    assert len(posts) == 2
    assert posts[0].no == 1
    assert posts[0].name == "名無しさん"
    assert posts[0].mail == "sage"
    assert "テスト投稿" in posts[0].content
    assert posts[1].no == 2
    assert posts[1].name == "テスターB"


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_decoding_errors_shift_jis(tmp_path: Path) -> None:
    """Given: Shift_JISでエンコードされた.dat
    When: _get_thread_posts_from_dat()を呼び出す
    Then: 正しくデコードして投稿を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    dat_content = "名無し<><>2020/01/01<>テスト<>\n"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("shift_jis")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert error is None
    assert len(posts) == 1
    assert posts[0].content == "テスト"


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_decoding_errors_cp932(tmp_path: Path) -> None:
    """Given: CP932でエンコードされた.dat
    When: _get_thread_posts_from_dat()を呼び出す
    Then: CP932フォールバックでデコードに成功する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # CP932特有の文字
    dat_content = "名無し<><>2020/01/01<>①テスト<>\n"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("cp932")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert error is None
    assert len(posts) == 1


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_max_posts_limit(tmp_path: Path) -> None:
    """Given: 最大投稿数を超える.datファイル
    When: _get_thread_posts_from_dat()を呼び出す
    Then: MAX_POSTS_PER_THREAD件まで取得する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # MAX_POSTS_PER_THREADは10なので、15件の投稿を作成
    lines = []
    for i in range(15):
        lines.append(f"名無し{i}<><>2020/01/01<>投稿{i}<>\n")
    dat_content = "".join(lines)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("shift_jis")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert error is None
    assert len(posts) == 10  # MAX_POSTS_PER_THREADまで制限される


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_http_error(tmp_path: Path) -> None:
    """Given: HTTPエラー（404）が発生
    When: _get_thread_posts_from_dat()を呼び出す
    Then: 空のリストとエラーメッセージを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response = Mock()
    mock_response.status_code = 404

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert posts == []
    assert error == "HTTP 404"


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_network_exception(tmp_path: Path) -> None:
    """Given: ネットワーク例外が発生
    When: _get_thread_posts_from_dat()を呼び出す
    Then: 空のリストとエラーメッセージを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_scraper = Mock()
    mock_scraper.get.side_effect = Exception("Network timeout")

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert posts == []
    assert "Network timeout" in error


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_empty_dat(tmp_path: Path) -> None:
    """Given: 空の.datファイル
    When: _get_thread_posts_from_dat()を呼び出す
    Then: 空のリストを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b""

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert posts == []
    assert error is None


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_malformed_dat(tmp_path: Path) -> None:
    """Given: 不正な形式の.datファイル（フィールドが不足）
    When: _get_thread_posts_from_dat()を呼び出す
    Then: パース可能な行のみを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # 正常な行と不正な行の混在
    dat_content = (
        "名無し<><>2020/01/01<>正常な投稿<>\n不正な行\n名無し2<><>2020/01/01<>正常な投稿2<>\n"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("shift_jis")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat("https://example.com/test.dat")

    # Verify
    assert error is None
    assert len(posts) == 2  # 不正な行はスキップされる
    assert posts[0].content == "正常な投稿"
    assert posts[1].content == "正常な投稿2"


# =============================================================================
# テスト対象: _get_with_retry
# =============================================================================


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
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await service._get_with_retry("https://example.com/test")
        mock_sleep.assert_awaited_once_with(1)

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
    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(httpx.RequestError, match="Network error"),
    ):
        await service._get_with_retry("https://example.com/test", max_retries=2)


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


# =============================================================================
# テスト対象: Helper Methods
# =============================================================================


def test_calculate_backoff_delay(tmp_path: Path) -> None:
    """Given: リトライ回数
    When: _calculate_backoff_delay()を呼び出す
    Then: 指数バックオフによる遅延時間を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute & Verify
    assert service._calculate_backoff_delay(0) == 1  # 2^0
    assert service._calculate_backoff_delay(1) == 2  # 2^1
    assert service._calculate_backoff_delay(2) == 4  # 2^2
    assert service._calculate_backoff_delay(3) == 8  # 2^3
    assert service._calculate_backoff_delay(10) == 300  # 2^10 > 300, capped at 300


def test_get_random_user_agent(tmp_path: Path) -> None:
    """Given: user_agentsリスト
    When: _get_random_user_agent()を呼び出す
    Then: user_agentsからランダムに選択した文字列を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    user_agent = service._get_random_user_agent()

    # Verify
    assert user_agent in service.user_agents
    assert isinstance(user_agent, str)
    assert len(user_agent) > 0


def test_build_board_url(tmp_path: Path) -> None:
    """Given: 板IDとサーバー
    When: _build_board_url()を呼び出す
    Then: 正しい板URLを構築して返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    url = service._build_board_url("ai", "krsw.5ch.net")

    # Verify
    assert url == "https://krsw.5ch.net/ai/"


def test_get_board_server_known_board(tmp_path: Path) -> None:
    """Given: 既知の板ID
    When: _get_board_server()を呼び出す
    Then: boards.tomlから読み込んだサーバーを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    server = service._get_board_server("ai")

    # Verify
    assert server == "krsw.5ch.net"  # boards.tomlの設定値


def test_get_board_server_unknown_board(tmp_path: Path) -> None:
    """Given: 未知の板ID
    When: _get_board_server()を呼び出す
    Then: デフォルトサーバーを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    server = service._get_board_server("unknown_board_xyz")

    # Verify
    assert server == "mevius.5ch.net"  # デフォルト値
