"""FiveChanExplorer._get_subject_txt_data() の単体テスト

subject.txt形式でスレッド一覧を取得するロジックを検証。
文字エンコーディング、エラーハンドリング、不正データの処理をテスト。
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


@pytest.mark.asyncio
async def test_get_subject_txt_data_parse_valid_subject_txt(tmp_path):
    """Given: 正常なsubject.txtレスポンス
    When: _get_subject_txt_data()を呼び出す
    Then: スレッド情報のリストを正しく解析して返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # subject.txt形式のデータ(Shift_JISでエンコード)
    subject_txt_unicode = (
        "1577836800.dat<>【AI】ChatGPT (100)\n"
        "1577836900.dat<>機械学習 (50)\n"
    )
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
async def test_get_subject_txt_data_handle_decoding_errors_shift_jis(tmp_path):
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
async def test_get_subject_txt_data_handle_decoding_errors_cp932(tmp_path):
    """Given: CP932でエンコードされたsubject.txt(Shift_JISデコード失敗)
    When: _get_subject_txt_data()を呼び出す
    Then: CP932フォールバックでデコードに成功する
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # CP932特有の文字を含むデータ(①など)
    subject_txt_content = "1577836800.dat<>①テストスレッド (10)\n".encode("cp932")

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


@pytest.mark.asyncio
async def test_get_subject_txt_data_handle_empty_data(tmp_path):
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
async def test_get_subject_txt_data_handle_malformed_data(tmp_path):
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
async def test_get_subject_txt_data_network_error_all_servers_fail(tmp_path):
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
async def test_get_subject_txt_data_404_error(tmp_path):
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
