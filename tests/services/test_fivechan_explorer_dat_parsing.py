"""FiveChanExplorer._get_thread_posts_from_dat() の単体テスト

.datファイルから投稿を取得するロジックを検証。
文字エンコーディング、最大投稿数制限、エラーハンドリングをテスト。
"""

from unittest.mock import Mock, patch

import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_parse_valid_dat(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

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
async def test_get_thread_posts_from_dat_handle_decoding_errors_shift_jis(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert error is None
    assert len(posts) == 1
    assert posts[0].content == "テスト"


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_decoding_errors_cp932(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert error is None
    assert len(posts) == 1


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_max_posts_limit(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert error is None
    assert len(posts) == 10  # MAX_POSTS_PER_THREADまで制限される


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_http_error(tmp_path):
    """Given: HTTPエラー(404)が発生
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert posts == []
    assert error == "HTTP 404"


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_network_exception(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert posts == []
    assert "Network timeout" in error


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_empty_dat(tmp_path):
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
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert posts == []
    assert error is None


@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_handle_malformed_dat(tmp_path):
    """Given: 不正な形式の.datファイル(フィールドが不足)
    When: _get_thread_posts_from_dat()を呼び出す
    Then: パース可能な行のみを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # 正常な行と不正な行の混在
    dat_content = (
        "名無し<><>2020/01/01<>正常な投稿<>\n"
        "不正な行\n"
        "名無し2<><>2020/01/01<>正常な投稿2<>\n"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_content.encode("shift_jis")

    mock_scraper = Mock()
    mock_scraper.get.return_value = mock_response

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        # Execute
        posts, error = await service._get_thread_posts_from_dat(
            "https://example.com/test.dat"
        )

    # Verify
    assert error is None
    assert len(posts) == 2  # 不正な行はスキップされる
    assert posts[0].content == "正常な投稿"
    assert posts[1].content == "正常な投稿2"
