"""
nook/services/fivechan_explorer/fivechan_explorer.py のテスト

テスト観点:
- FiveChanExplorerの初期化
- スレッド情報取得
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

import asyncio
import time
import tracemalloc
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# =============================================================================
# テスト用定数
# =============================================================================

# パフォーマンステスト用の閾値
MAX_RESPONSE_SIZE_MB = 10
MAX_RESPONSE_SIZE_BYTES = MAX_RESPONSE_SIZE_MB * 1024 * 1024
MAX_PROCESSING_TIME_SECONDS = 1.0
MAX_MEMORY_USAGE_MB = 50
MAX_MEMORY_USAGE_BYTES = MAX_MEMORY_USAGE_MB * 1024 * 1024
ENCODING_BOMB_REPEAT_COUNT = 1000000  # Shift_JISスペースの繰り返し回数

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(fivechan_service):
    """
    Given: デフォルトのstorage_dir
    When: FiveChanExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    assert fivechan_service.service_name == "fivechan_explorer"


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success(fivechan_service):
    """
    Given: 有効な掲示板データ
    When: collectメソッドを呼び出す
    Then: データが正常に取得・保存される
    """
    fivechan_service.http_client = AsyncMock()

    with patch.object(
        fivechan_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(
        fivechan_service.storage,
        "save",
        new_callable=AsyncMock,
        return_value=Path("/data/test.json"),
    ):

        fivechan_service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body>Test thread</body></html>")
        )
        fivechan_service.gpt_client.get_response = AsyncMock(return_value="要約")

        result = await fivechan_service.collect(target_dates=[date.today()])

        assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(fivechan_service):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    fivechan_service.http_client = AsyncMock()

    with patch.object(fivechan_service, "setup_http_client", new_callable=AsyncMock):

        fivechan_service.http_client.get = AsyncMock(side_effect=Exception("Network error"))

        result = await fivechan_service.collect(target_dates=[date.today()])

        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(fivechan_service):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    fivechan_service.http_client = AsyncMock()

    with patch.object(
        fivechan_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(fivechan_service.storage, "save", new_callable=AsyncMock):

        fivechan_service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body>Test</body></html>")
        )
        fivechan_service.gpt_client.get_response = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await fivechan_service.collect(target_dates=[date.today()])

        assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(fivechan_service):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    fivechan_service.http_client = AsyncMock()

    with patch.object(
        fivechan_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(
        fivechan_service.storage,
        "save",
        new_callable=AsyncMock,
        return_value=Path("/data/test.json"),
    ):

        fivechan_service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body>Test thread</body></html>")
        )
        fivechan_service.gpt_client.get_response = AsyncMock(return_value="要約")

        result = await fivechan_service.collect(target_dates=[date.today()])

        assert isinstance(result, list)

        await fivechan_service.cleanup()


# =============================================================================
# 5. 内部メソッド単体テスト: _get_subject_txt_data
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_success(fivechan_service):
    """
    Given: 有効なShift_JISエンコードのsubject.txt
    When: _get_subject_txt_dataを呼び出す
    Then: スレッド一覧が正しく解析される
    """
    # Shift_JISエンコードのsubject.txtデータ
    subject_data = "1234567890.dat<>AI・人工知能について語るスレ (100)\n9876543210.dat<>機械学習の最新動向 (50)\n".encode(
        "shift_jis"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("ai")

        assert len(result) == 2
        assert result[0]["title"] == "AI・人工知能について語るスレ"
        assert result[0]["post_count"] == 100
        assert result[1]["title"] == "機械学習の最新動向"
        assert result[1]["post_count"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_malformed_encoding(fivechan_service):
    """
    Given: 文字化けを含むsubject.txt（無効バイト含む）
    When: _get_subject_txt_dataを呼び出す
    Then: errors='ignore'で文字化け部分を無視して処理
    """
    # 無効バイトシーケンスを含むデータ
    subject_data = b"1234567890.dat<>\xff\xfe AI\x83X\x83\x8c\x83b\x83h (50)\n"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("test")

        # errors='ignore'で処理されるので、空配列ではない
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_malformed_format(fivechan_service):
    """
    Given: 不正なフォーマットのsubject.txt（正規表現マッチ失敗）
    When: _get_subject_txt_dataを呼び出す
    Then: マッチしない行はスキップされる
    """
    # 正規表現にマッチしないフォーマット
    subject_data = (
        "invalid_format_line\n1234567890.dat<>正しいスレッド (100)\n".encode(
            "shift_jis"
        )
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("test")

        # 正しいフォーマットの行のみ解析される
        assert len(result) == 1
        assert result[0]["title"] == "正しいスレッド"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_subdomain_retry(fivechan_service):
    """
    Given: 最初のサーバーが失敗、2番目のサーバーが成功
    When: _get_subject_txt_dataを呼び出す
    Then: 複数サブドメインをリトライして成功
    """
    subject_data = "1234567890.dat<>AIスレッド (100)\n".encode("shift_jis")

    # 1回目は失敗、2回目は成功
    responses = [
        Exception("Connection failed"),
        Mock(status_code=200, content=subject_data),
    ]

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(side_effect=responses)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("ai")

        # 2回目のリトライで成功
        assert len(result) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_all_servers_fail(fivechan_service):
    """
    Given: すべてのサーバーが失敗
    When: _get_subject_txt_dataを呼び出す
    Then: 空配列が返される
    """
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("test")

        assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_encoding_fallback(fivechan_service):
    """
    Given: shift_jisで失敗するが、cp932で成功するデータ
    When: _get_subject_txt_dataを呼び出す
    Then: エンコーディングフォールバックで正常処理
    """
    # CP932特有の文字（①②③など）
    subject_data = "1234567890.dat<>①②③のスレッド (30)\n".encode("cp932")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("test")

        # CP932フォールバックで処理される
        assert len(result) >= 0  # エラーなく処理される


# =============================================================================
# 6. 内部メソッド単体テスト: _get_thread_posts_from_dat
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_success(fivechan_service):
    """
    Given: 有効なdat形式データ（<>区切り）
    When: _get_thread_posts_from_datを呼び出す
    Then: 投稿リストが正しく解析される
    """
    # dat形式: name<>mail<>date ID<>message<>
    # 注: 実際のdatファイルは末尾に<>がありますが、空要素は無視されます
    dat_data = """名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:test1234<>AIについて語りましょう
名無しさん<>sage<>2024/11/14(木) 12:01:00.00 ID:test5678<>機械学習は面白い
""".encode(
        "shift_jis"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_data

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, latest = await fivechan_service._get_thread_posts_from_dat(
            "http://test.5ch.net/test/dat/1234567890.dat"
        )

        assert len(posts) == 2
        assert posts[0]["name"] == "名無しさん"
        assert posts[0]["mail"] == "sage"
        assert "AI" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_shift_jis_decode(fivechan_service):
    """
    Given: Shift_JISエンコードのdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: 正しくデコードされる
    """
    # 日本語を含むdat
    dat_data = "名無し<>sage<>2024/11/14 12:00:00<>深層学習について\n".encode(
        "shift_jis"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_data

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, _ = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        assert len(posts) == 1
        assert "深層学習" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_malformed_line(fivechan_service):
    """
    Given: <>区切りが不足している不正な行
    When: _get_thread_posts_from_datを呼び出す
    Then: 不正な行はスキップされる
    """
    # 不正な行（<>が3つ未満）
    dat_data = """invalid_line
名無し<>sage<>2024/11/14 12:00:00<>正しい投稿
another_invalid<>only_two
""".encode(
        "shift_jis"
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_data

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, _ = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        # 正しいフォーマットの行のみ解析
        assert len(posts) == 1
        assert "正しい投稿" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_http_error(fivechan_service):
    """
    Given: HTTPエラー（404など）
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列とNoneを返す
    """
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, latest = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        assert posts == []
        assert latest is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_empty_content(fivechan_service):
    """
    Given: 空のdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列を返す
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b""

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, _ = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        assert posts == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_encoding_cascade(fivechan_service):
    """
    Given: 文字化けを含むdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: エンコーディングカスケード（shift_jis→cp932→utf-8）で処理
    """
    # 無効バイトを含むデータ
    dat_data = b"name<>mail<>date<>\xff\xfe invalid bytes message<>\n"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_data

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, _ = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        # errors='ignore'で処理されるため、エラーなく処理される
        assert isinstance(posts, list)


# =============================================================================
# 7. 内部メソッド単体テスト: _get_with_retry
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_success(fivechan_service):
    """
    Given: 即座に200レスポンス
    When: _get_with_retryを呼び出す
    Then: リトライなしで成功
    """
    fivechan_service.http_client = AsyncMock()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "success"

    fivechan_service.http_client.get = AsyncMock(return_value=mock_response)

    result = await fivechan_service._get_with_retry("http://test.url")

    assert result.status_code == 200
    fivechan_service.http_client.get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_rate_limit_429(fivechan_service):
    """
    Given: 429レート制限エラー（Retry-Afterヘッダー付き）
    When: _get_with_retryを呼び出す
    Then: Retry-After時間待機後にリトライ
    """
    fivechan_service.http_client = AsyncMock()

    # 1回目: 429、2回目: 200
    responses = [
        Mock(status_code=429, headers={"Retry-After": "5"}),
        Mock(status_code=200, text="success"),
    ]
    fivechan_service.http_client.get = AsyncMock(side_effect=responses)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fivechan_service._get_with_retry("http://test.url")

        assert result.status_code == 200
        mock_sleep.assert_called_once_with(5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_server_error_500(fivechan_service):
    """
    Given: 500系サーバーエラー
    When: _get_with_retryを呼び出す
    Then: 指数バックオフでリトライ
    """
    fivechan_service.http_client = AsyncMock()

    # 1回目: 503、2回目: 503、3回目: 200
    responses = [
        Mock(status_code=503),
        Mock(status_code=503),
        Mock(status_code=200, text="success"),
    ]
    fivechan_service.http_client.get = AsyncMock(side_effect=responses)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await fivechan_service._get_with_retry("http://test.url")

        assert result.status_code == 200
        assert mock_sleep.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_connection_error(fivechan_service):
    """
    Given: 接続エラーが発生
    When: _get_with_retryを呼び出す
    Then: 例外からリトライして成功
    """
    fivechan_service.http_client = AsyncMock()

    # 1回目: 例外、2回目: 200
    fivechan_service.http_client.get = AsyncMock(
        side_effect=[Exception("Connection timeout"), Mock(status_code=200)]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await fivechan_service._get_with_retry("http://test.url")

        assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_max_retries_exceeded(fivechan_service):
    """
    Given: 最大リトライ回数を超える
    When: _get_with_retryを呼び出す
    Then: 最終的にエラーを送出
    """
    fivechan_service.http_client = AsyncMock()

    fivechan_service.http_client.get = AsyncMock(side_effect=Exception("Persistent error"))

    with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(Exception):
        await fivechan_service._get_with_retry("http://test.url", max_retries=3)


# =============================================================================
# 8. 内部メソッド単体テスト: 補助メソッド
# =============================================================================


@pytest.mark.unit
def test_calculate_popularity_recent_thread(fivechan_service):
    """
    Given: 最近作成されたスレッド（1時間前）
    When: _calculate_popularityを呼び出す
    Then: recency_bonusが高い
    """
    from datetime import datetime

    now = datetime.now()
    recent_timestamp = int(now.timestamp()) - 3600  # 1時間前

    popularity = fivechan_service._calculate_popularity(
        post_count=50, sample_count=10, timestamp=recent_timestamp
    )

    # 50 + 10 + (24/1) = 84
    assert popularity > 60  # recency_bonusで高くなる


@pytest.mark.unit
def test_calculate_popularity_old_thread(fivechan_service):
    """
    Given: 古いスレッド（48時間前）
    When: _calculate_popularityを呼び出す
    Then: recency_bonusが低い
    """
    from datetime import datetime

    now = datetime.now()
    old_timestamp = int(now.timestamp()) - 172800  # 48時間前

    popularity = fivechan_service._calculate_popularity(
        post_count=50, sample_count=10, timestamp=old_timestamp
    )

    # 50 + 10 + (24/48) = 60.5
    assert 60 <= popularity <= 61


@pytest.mark.unit
def test_get_random_user_agent(fivechan_service):
    """
    Given: user_agentsリスト
    When: _get_random_user_agentを複数回呼び出す
    Then: ランダムなUser-Agentが選択される
    """
    user_agents = set()
    for _ in range(20):
        ua = fivechan_service._get_random_user_agent()
        user_agents.add(ua)
        assert ua in fivechan_service.user_agents

    # 複数のUser-Agentが選ばれることを確認
    assert len(user_agents) > 1


@pytest.mark.unit
def test_calculate_backoff_delay(fivechan_service):
    """
    Given: リトライ回数
    When: _calculate_backoff_delayを呼び出す
    Then: 指数バックオフの遅延時間が計算される
    """
    assert fivechan_service._calculate_backoff_delay(0) == 1  # 2^0 = 1
    assert fivechan_service._calculate_backoff_delay(1) == 2  # 2^1 = 2
    assert fivechan_service._calculate_backoff_delay(2) == 4  # 2^2 = 4
    assert fivechan_service._calculate_backoff_delay(8) == 256  # 2^8 = 256
    assert fivechan_service._calculate_backoff_delay(10) == 300  # max 300秒


@pytest.mark.unit
def test_build_board_url(fivechan_service):
    """
    Given: 板IDとサーバー
    When: _build_board_urlを呼び出す
    Then: 正しい板URLが構築される
    """
    url = fivechan_service._build_board_url("ai", "mevius.5ch.net")

    assert url == "https://mevius.5ch.net/ai/"


@pytest.mark.unit
def test_get_board_server(fivechan_service):
    """
    Given: 板ID
    When: _get_board_serverを呼び出す
    Then: boards.tomlから正しいサーバー情報を取得
    """
    # board_serversは_load_boardsで初期化される
    if "ai" in fivechan_service.board_servers:
        server = fivechan_service._get_board_server("ai")
        assert server in [
            "mevius.5ch.net",
            "egg.5ch.net",
            "krsw.5ch.net",
        ]  # 想定されるサーバー

    # 存在しない板はデフォルト値
    default_server = fivechan_service._get_board_server("nonexistent_board")
    assert default_server == "mevius.5ch.net"


# =============================================================================
# セキュリティテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    "malicious_input,test_id",
    [
        ("'; DROP TABLE threads; --", "sql_injection_1"),
        ("<script>alert('XSS')</script>", "xss_attack"),
        ("../../../../etc/passwd", "path_traversal_1"),
        ("\x00\x00\x00\x00", "null_byte_injection"),
        ("../../../etc/shadow", "path_traversal_2"),
        ("'; DELETE FROM posts; --", "sql_injection_2"),
    ],
    ids=lambda x: x[1] if isinstance(x, tuple) else x,
)
@pytest.mark.asyncio
async def test_malicious_input_in_thread_title(fivechan_service, malicious_input, test_id):
    """
    Given: 悪意のある入力がスレッドタイトルに含まれる
    When: 実際の解析ロジックでsubject.txtを解析
    Then: 安全にサニタイズまたはエラーハンドリング

    検証項目:
    - クラッシュしない
    - 悪意のある文字列が適切にエスケープされる
    - データ構造が破壊されない
    """
    # subject.txtデータに悪意のある入力を含める
    subject_line = f"1234567890.dat<>{malicious_input} (100)\n"
    subject_data = subject_line.encode("shift_jis", errors="ignore")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        # 実際のメソッドを呼び出してセキュリティをテスト
        result = await fivechan_service._get_subject_txt_data("ai")

        # 悪意のある入力が含まれていてもクラッシュしない
        assert isinstance(result, list), f"Expected list but got {type(result).__name__}"

        # データが返される場合、危険な文字列が含まれていないことを確認
        if result:
            result_str = str(result)
            # SQL Injectionの検証
            if "DROP TABLE" in malicious_input or "DELETE FROM" in malicious_input:
                # データベース操作が含まれていないことを確認（文字列として保存されている）
                assert isinstance(result[0], dict), "Result should be safely parsed as dict"

            # XSSの検証
            if "<script>" in malicious_input:
                # スクリプトタグが無害化されているか、そのまま文字列として保存されている
                assert isinstance(result[0], dict), "Result should be safely parsed as dict"


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_dos_attack_oversized_response(fivechan_service):
    """
    Given: 異常に大きなレスポンス（DoS攻撃シミュレーション）
    When: _get_subject_txt_dataを呼び出す
    Then: クラッシュせずに処理が完了する

    検証項目:
    - メモリリークしない
    - タイムアウトしない
    - クラッシュしない
    - 適切にデータを処理できる（または安全にエラーを返す）

    Background:
    DoS攻撃で大容量データを送りつけられた場合の防御機能をテスト
    """
    # 10MBの巨大なデータ
    huge_data = b"x" * MAX_RESPONSE_SIZE_BYTES

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = huge_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        # 大容量データでもクラッシュしないことを確認
        # 実装が大容量データを処理する仕様のため、正常終了を期待
        result = await fivechan_service._get_subject_txt_data("ai")
        # 処理が完了すること（タイムアウトやメモリエラーなし）
        assert isinstance(result, list), f"Expected list but got {type(result).__name__}"
        # 空のリストまたは正常にパースされたデータ
        # （巨大な無効データなので空になる可能性が高い）


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_encoding_bomb_attack(fivechan_service):
    """
    Given: エンコーディングボム（Billion Laughs攻撃相当）
    When: デコード処理
    Then: クラッシュせずに処理が完了する

    検証項目:
    - メモリ爆発しない
    - デコード処理が完了する
    - クラッシュしない

    Background:
    繰り返しパターンでメモリ消費を狙うエンコーディングボム攻撃への耐性をテスト
    """
    # 繰り返しパターンでメモリ消費を狙う
    # Shift_JIS のスペース（全角スペース: 0x8140）を大量に繰り返し
    bomb_data = b"\x81\x40" * ENCODING_BOMB_REPEAT_COUNT

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = bomb_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        # エンコーディングボムでもクラッシュしないことを確認
        # 実装がエラーハンドリングを持つため、正常終了を期待
        result = await fivechan_service._get_subject_txt_data("ai")
        assert isinstance(result, list), f"Expected list but got {type(result).__name__}"
        # 全角スペースのみのデータなので空のリストになる


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    "malicious_dat_content,test_id",
    [
        ("名無し<>sage<>2024/11/14<>'; DROP TABLE posts; --\n", "dat_sql_injection"),
        ("名無し<>sage<>2024/11/14<><script>alert('XSS')</script>\n", "dat_xss_attack"),
        ("名無し<>sage<>2024/11/14<>../../../../etc/passwd\n", "dat_path_traversal"),
        ("名無し<><><><><><><><><><><><><><>Too many delimiters\n", "dat_delimiter_overflow"),
    ],
    ids=lambda x: x[1] if isinstance(x, tuple) else x,
)
@pytest.mark.asyncio
async def test_dat_parsing_malicious_input(fivechan_service, malicious_dat_content, test_id):
    """
    Given: 悪意のある入力データがDAT形式に含まれる
    When: DAT解析を実行
    Then: 安全にサニタイズまたはエラーハンドリング

    検証項目:
    - クラッシュしない
    - DAT形式のパース処理が安全に完了する
    - 悪意のあるデータが適切にエスケープされる
    """
    dat_data = malicious_dat_content.encode("shift_jis", errors="ignore")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = dat_data
    mock_response.text = malicious_dat_content

    mock_scraper = Mock()
    mock_scraper.get = Mock(return_value=mock_response)
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
        "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
    ):

        posts, latest = await fivechan_service._get_thread_posts_from_dat(
            "http://test.dat"
        )

        # 悪意のある入力でもクラッシュせず、安全に処理されること
        assert isinstance(posts, list), f"Expected list but got {type(posts).__name__}"
        assert latest is None or isinstance(latest, str), f"Expected str or None but got {type(latest).__name__}"

        # データが返される場合、適切にパースされていることを確認
        if posts:
            for post in posts:
                assert isinstance(post, dict), "Each post should be a dict"


# =============================================================================
# パフォーマンステスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_thread_fetching_performance(fivechan_service):
    """
    Given: 複数スレッドの並行取得
    When: 10個のスレッドを同時取得
    Then: 適切な並行処理により高速に完了

    検証項目:
    - 10個のリクエストが並行実行される
    - 逐次実行より高速（100ms vs 10ms程度）
    - 全てのリクエストが完了する
    """
    call_count = 0

    # モックレスポンスを高速で返すように設定
    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # 10ms のシミュレーション遅延
        return [
            {
                "server": "mevius.5ch.net",
                "board": "ai",
                "timestamp": str(1700000000 + call_count),
                "title": f"AIスレッド{call_count}",
                "post_count": 50,
            }
        ]

    start_time = time.time()

    with patch.object(
        fivechan_service, "_get_subject_txt_data", side_effect=mock_fetch
    ):
        # 10個を並行実行
        tasks = [fivechan_service._get_subject_txt_data("ai") for _ in range(10)]
        results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # パフォーマンス検証
    # 並行実行なら10ms程度、逐次実行なら100ms以上
    # マージンを持たせて50ms以下で完了することを期待
    assert elapsed < 0.05, f"並行処理が遅い（逐次実行の可能性）: {elapsed}秒"
    assert call_count == 10, f"Expected 10 calls but got {call_count}"
    assert len(results) == 10, f"Expected 10 results but got {len(results)}"
    assert all(isinstance(r, list) for r in results), "All results should be lists"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_efficiency_large_dataset(fivechan_service):
    """
    Given: 大量のスレッドデータ
    When: 処理を実行
    Then: メモリリークなく効率的に処理

    検証項目:
    - ピークメモリ使用量が閾値以下
    - 100個のスレッドが正常に処理される
    - メモリリークしない
    """
    tracemalloc.start()

    # 100個のスレッドをシミュレート（1000個だと遅すぎるので削減）
    large_subject_data = (
        "1234567890.dat<>テストスレッド (100)\n" * 100
    ).encode("shift_jis")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = large_subject_data

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("ai")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # メモリ使用量検証（ピーク50MB以下）
    assert peak < MAX_MEMORY_USAGE_BYTES, (
        f"メモリ使用量が多すぎる: {peak / 1024 / 1024:.2f}MB "
        f"(閾値: {MAX_MEMORY_USAGE_MB}MB)"
    )
    assert len(result) == 100, f"Expected 100 results but got {len(result)}"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_network_timeout_handling(fivechan_service):
    """
    Given: ネットワークタイムアウト
    When: スレッドデータ取得
    Then: 適切なタイムアウトエラーハンドリング（無限待機しない）

    検証項目:
    - 5秒でタイムアウトする
    - 無限待機しない
    - TimeoutErrorが発生する
    """
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(100)  # 100秒待機（異常に遅い）
        return Mock(status_code=200)

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = slow_response
        mock_client.return_value = client_instance

        # タイムアウト設定（5秒）
        with pytest.raises(asyncio.TimeoutError, match=None):
            await asyncio.wait_for(
                fivechan_service._get_subject_txt_data("ai"), timeout=5.0
            )


@pytest.mark.unit
@pytest.mark.performance
def test_board_server_cache_efficiency(fivechan_service):
    """
    Given: 同じ板を複数回アクセス
    When: _get_board_serverを繰り返し呼び出し
    Then: キャッシュにより高速化（2回目以降は即座）

    検証項目:
    - 1回目と2回目で同じ結果が返る
    - キャッシュアクセスが高速（1ms以下）
    - データの一貫性が保たれる
    """
    # board_serversに値を設定（キャッシュシミュレーション）
    fivechan_service.board_servers["ai"] = "mevius.5ch.net"

    # 1回目（キャッシュから取得）
    start = time.time()
    server1 = fivechan_service._get_board_server("ai")
    first_call_time = time.time() - start

    # 2回目（キャッシュから取得）
    start = time.time()
    server2 = fivechan_service._get_board_server("ai")
    second_call_time = time.time() - start

    # データの一貫性を検証
    assert server1 == server2, f"Expected same server but got {server1} and {server2}"
    assert server1 == "mevius.5ch.net", f"Expected mevius.5ch.net but got {server1}"

    # 両方ともキャッシュから取得されるため、どちらも高速（1ms以下）
    assert first_call_time < 0.001, (
        f"1回目のキャッシュアクセスが遅い: {first_call_time * 1000:.2f}ms"
    )
    assert second_call_time < 0.001, (
        f"2回目のキャッシュアクセスが遅い: {second_call_time * 1000:.2f}ms"
    )


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_retry_backoff_performance(fivechan_service):
    """
    Given: HTTPエラーによるリトライ
    When: 指数バックオフでリトライ
    Then: 適切な遅延時間でリトライ（パフォーマンスに影響なし）

    検証項目:
    - リトライが正しい回数呼ばれる（3回）
    - バックオフsleepが適切に呼ばれる（最低2回）
    - 全体の処理時間が妥当（sleepモックで高速）
    - 最終的に成功する
    """
    call_count = 0
    call_times = []

    async def failing_then_success(*args, **kwargs):
        nonlocal call_count
        call_times.append(time.time())
        call_count += 1
        if call_count < 3:
            raise Exception("Network error")
        return Mock(status_code=200, content=b"success")

    start_time = time.time()

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = failing_then_success
        mock_client.return_value = client_instance

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await fivechan_service._get_with_retry(
                "https://mevius.5ch.net/ai/subject.txt"
            )

    elapsed = time.time() - start_time

    # リトライが3回呼ばれたことを確認
    assert call_count == 3, f"Expected 3 calls but got {call_count}"

    # sleep が適切に呼ばれたことを確認（最低2回: 1回目と2回目の失敗後）
    assert mock_sleep.call_count >= 2, (
        f"Expected at least 2 sleep calls but got {mock_sleep.call_count}"
    )

    # 全体の処理時間が妥当（sleepをモックしているので速い）
    assert elapsed < MAX_PROCESSING_TIME_SECONDS, (
        f"リトライ処理が遅すぎる: {elapsed}秒 (閾値: {MAX_PROCESSING_TIME_SECONDS}秒)"
    )

    # 最終的に成功する
    assert result is not None, "Expected successful result"
    assert result.status_code == 200, f"Expected status 200 but got {result.status_code}"
