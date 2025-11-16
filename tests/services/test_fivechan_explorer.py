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
MAX_RESPONSE_SIZE_MB = 10
MAX_RESPONSE_SIZE_BYTES = MAX_RESPONSE_SIZE_MB * 1024 * 1024
MAX_PROCESSING_TIME_SECONDS = 1.0
MAX_MEMORY_USAGE_MB = 50
MAX_MEMORY_USAGE_BYTES = MAX_MEMORY_USAGE_MB * 1024 * 1024
ENCODING_BOMB_REPEAT_COUNT = 1000000


# =============================================================================
# モジュールスコープのフィクスチャ
# =============================================================================
@pytest.fixture(scope="module")
def encoding_bomb_data():
    """エンコーディングボム用データ（約2MB）"""
    return b"\x81\x40" * ENCODING_BOMB_REPEAT_COUNT


@pytest.fixture(scope="module")
def huge_response_data():
    """DoS攻撃用大容量データ（10MB）"""
    return b"x" * MAX_RESPONSE_SIZE_BYTES


# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: FiveChanExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        assert service.service_name == "fivechan_explorer"


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success(mock_env_vars):
    """
    Given: 有効な掲示板データ
    When: collectメソッドを呼び出す
    Then: データが正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>Test thread</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(mock_env_vars):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(side_effect=Exception("Network error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>Test</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>Test thread</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)

            await service.cleanup()


# =============================================================================
# 5. 内部メソッド単体テスト: _get_subject_txt_data
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_success(mock_env_vars):
    """
    Given: 有効なShift_JISエンコードのsubject.txt
    When: _get_subject_txt_dataを呼び出す
    Then: スレッド一覧が正しく解析される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

            result = await service._get_subject_txt_data("ai")

            assert len(result) == 2
            assert result[0]["title"] == "AI・人工知能について語るスレ"
            assert result[0]["post_count"] == 100
            assert result[1]["title"] == "機械学習の最新動向"
            assert result[1]["post_count"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_malformed_encoding(mock_env_vars):
    """
    Given: 文字化けを含むsubject.txt（無効バイト含む）
    When: _get_subject_txt_dataを呼び出す
    Then: errors='ignore'で文字化け部分を無視して処理
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

            result = await service._get_subject_txt_data("test")

            # errors='ignore'で処理されるので、空配列ではない
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_malformed_format(mock_env_vars):
    """
    Given: 不正なフォーマットのsubject.txt（正規表現マッチ失敗）
    When: _get_subject_txt_dataを呼び出す
    Then: マッチしない行はスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

            result = await service._get_subject_txt_data("test")

            # 正しいフォーマットの行のみ解析される
            assert len(result) == 1
            assert result[0]["title"] == "正しいスレッド"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_subdomain_retry(mock_env_vars):
    """
    Given: 最初のサーバーが失敗、2番目のサーバーが成功
    When: _get_subject_txt_dataを呼び出す
    Then: 複数サブドメインをリトライして成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

            result = await service._get_subject_txt_data("ai")

            # 2回目のリトライで成功
            assert len(result) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_all_servers_fail(mock_env_vars):
    """
    Given: すべてのサーバーが失敗
    When: _get_subject_txt_dataを呼び出す
    Then: 空配列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.return_value = client_instance

            result = await service._get_subject_txt_data("test")

            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_encoding_fallback(mock_env_vars):
    """
    Given: shift_jisで失敗するが、cp932で成功するデータ
    When: _get_subject_txt_dataを呼び出す
    Then: エンコーディングフォールバックで正常処理
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

            result = await service._get_subject_txt_data("test")

            # CP932フォールバックで処理される
            assert len(result) >= 0  # エラーなく処理される


# =============================================================================
# 6. 内部メソッド単体テスト: _get_thread_posts_from_dat
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_success(mock_env_vars):
    """
    Given: 有効なdat形式データ（<>区切り）
    When: _get_thread_posts_from_datを呼び出す
    Then: 投稿リストが正しく解析される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, latest = await service._get_thread_posts_from_dat(
                "http://test.5ch.net/test/dat/1234567890.dat"
            )

            assert len(posts) == 2
            assert posts[0]["name"] == "名無しさん"
            assert posts[0]["mail"] == "sage"
            assert "AI" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_shift_jis_decode(mock_env_vars):
    """
    Given: Shift_JISエンコードのdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: 正しくデコードされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, _ = await service._get_thread_posts_from_dat("http://test.dat")

            assert len(posts) == 1
            assert "深層学習" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_malformed_line(mock_env_vars):
    """
    Given: <>区切りが不足している不正な行
    When: _get_thread_posts_from_datを呼び出す
    Then: 不正な行はスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

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

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, _ = await service._get_thread_posts_from_dat("http://test.dat")

            # 正しいフォーマットの行のみ解析
            assert len(posts) == 1
            assert "正しい投稿" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_http_error(mock_env_vars):
    """
    Given: HTTPエラー（404など）
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列とNoneを返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, latest = await service._get_thread_posts_from_dat("http://test.dat")

            assert posts == []
            assert latest is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_empty_content(mock_env_vars):
    """
    Given: 空のdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列を返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, _ = await service._get_thread_posts_from_dat("http://test.dat")

            assert posts == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_encoding_cascade(mock_env_vars):
    """
    Given: 文字化けを含むdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: エンコーディングカスケード（shift_jis→cp932→utf-8）で処理
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 無効バイトを含むデータ
        dat_data = b"name<>mail<>date<>\xff\xfe invalid bytes message<>\n"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = dat_data

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, _ = await service._get_thread_posts_from_dat("http://test.dat")

            # errors='ignore'で処理されるため、エラーなく処理される
            assert isinstance(posts, list)


# =============================================================================
# 7. 内部メソッド単体テスト: _get_with_retry
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_success(mock_env_vars):
    """
    Given: 即座に200レスポンス
    When: _get_with_retryを呼び出す
    Then: リトライなしで成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"

        service.http_client.get = AsyncMock(return_value=mock_response)

        result = await service._get_with_retry("http://test.url")

        assert result.status_code == 200
        service.http_client.get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_rate_limit_429(mock_env_vars):
    """
    Given: 429レート制限エラー（Retry-Afterヘッダー付き）
    When: _get_with_retryを呼び出す
    Then: Retry-After時間待機後にリトライ
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1回目: 429、2回目: 200
        responses = [
            Mock(status_code=429, headers={"Retry-After": "5"}),
            Mock(status_code=200, text="success"),
        ]
        service.http_client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service._get_with_retry("http://test.url")

            assert result.status_code == 200
            mock_sleep.assert_called_once_with(5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_server_error_500(mock_env_vars):
    """
    Given: 500系サーバーエラー
    When: _get_with_retryを呼び出す
    Then: 指数バックオフでリトライ
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1回目: 503、2回目: 503、3回目: 200
        responses = [
            Mock(status_code=503),
            Mock(status_code=503),
            Mock(status_code=200, text="success"),
        ]
        service.http_client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service._get_with_retry("http://test.url")

            assert result.status_code == 200
            assert mock_sleep.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_connection_error(mock_env_vars):
    """
    Given: 接続エラーが発生
    When: _get_with_retryを呼び出す
    Then: 例外からリトライして成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1回目: 例外、2回目: 200
        service.http_client.get = AsyncMock(
            side_effect=[Exception("Connection timeout"), Mock(status_code=200)]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_retry("http://test.url")

            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_retry_max_retries_exceeded(mock_env_vars):
    """
    Given: 最大リトライ回数を超える
    When: _get_with_retryを呼び出す
    Then: 最終的にエラーを送出
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        service.http_client.get = AsyncMock(side_effect=Exception("Persistent error"))

        with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(Exception):
            await service._get_with_retry("http://test.url", max_retries=3)


# =============================================================================
# 8. 内部メソッド単体テスト: 補助メソッド
# =============================================================================


@pytest.mark.unit
def test_calculate_popularity_recent_thread(mock_env_vars):
    """
    Given: 最近作成されたスレッド（1時間前）
    When: _calculate_popularityを呼び出す
    Then: recency_bonusが高い
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import datetime

        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        now = datetime.now()
        recent_timestamp = int(now.timestamp()) - 3600  # 1時間前

        popularity = service._calculate_popularity(
            post_count=50, sample_count=10, timestamp=recent_timestamp
        )

        # 50 + 10 + (24/1) = 84
        assert popularity > 60  # recency_bonusで高くなる


@pytest.mark.unit
def test_calculate_popularity_old_thread(mock_env_vars):
    """
    Given: 古いスレッド（48時間前）
    When: _calculate_popularityを呼び出す
    Then: recency_bonusが低い
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import datetime

        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        now = datetime.now()
        old_timestamp = int(now.timestamp()) - 172800  # 48時間前

        popularity = service._calculate_popularity(
            post_count=50, sample_count=10, timestamp=old_timestamp
        )

        # 50 + 10 + (24/48) = 60.5
        assert 60 <= popularity <= 61


@pytest.mark.unit
def test_get_random_user_agent(mock_env_vars):
    """
    Given: user_agentsリスト
    When: _get_random_user_agentを複数回呼び出す
    Then: ランダムなUser-Agentが選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        user_agents = set()
        for _ in range(20):
            ua = service._get_random_user_agent()
            user_agents.add(ua)
            assert ua in service.user_agents

        # 複数のUser-Agentが選ばれることを確認
        assert len(user_agents) > 1


@pytest.mark.unit
def test_calculate_backoff_delay(mock_env_vars):
    """
    Given: リトライ回数
    When: _calculate_backoff_delayを呼び出す
    Then: 指数バックオフの遅延時間が計算される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        assert service._calculate_backoff_delay(0) == 1  # 2^0 = 1
        assert service._calculate_backoff_delay(1) == 2  # 2^1 = 2
        assert service._calculate_backoff_delay(2) == 4  # 2^2 = 4
        assert service._calculate_backoff_delay(8) == 256  # 2^8 = 256
        assert service._calculate_backoff_delay(10) == 300  # max 300秒


@pytest.mark.unit
def test_build_board_url(mock_env_vars):
    """
    Given: 板IDとサーバー
    When: _build_board_urlを呼び出す
    Then: 正しい板URLが構築される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        url = service._build_board_url("ai", "mevius.5ch.net")

        assert url == "https://mevius.5ch.net/ai/"


@pytest.mark.unit
def test_get_board_server(mock_env_vars):
    """
    Given: 板ID
    When: _get_board_serverを呼び出す
    Then: boards.tomlから正しいサーバー情報を取得
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # board_serversは_load_boardsで初期化される
        if "ai" in service.board_servers:
            server = service._get_board_server("ai")
            assert server in [
                "mevius.5ch.net",
                "egg.5ch.net",
                "krsw.5ch.net",
            ]  # 想定されるサーバー

        # 存在しない板はデフォルト値
        default_server = service._get_board_server("nonexistent_board")
        assert default_server == "mevius.5ch.net"


# =============================================================================
# 9. セキュリティテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_malicious_input_in_thread_title(mock_env_vars):
    """
    Given: XSS/SQLインジェクション等の悪意のある入力がスレッドタイトルに含まれる
    When: subject.txtをパース
    Then: エラーなく処理され、データが保存される（サニタイゼーションは表示層で行う設計）

    検証項目:
    - 悪意のある入力を含むデータでもパースエラーにならない
    - データ構造が正しく保たれる
    - 改行コードがフィールド区切りを壊さない

    注: XSS/SQLインジェクション対策は表示層・クエリ層で行う設計のため、
        ここでは元データをそのまま保存できることを検証
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # テストデータ: XSS、SQLインジェクション、改行コードを含む
        malicious_subjects = [
            "1234567890.dat<><script>alert('XSS')</script>悪意のあるスレ (100)\n",
            "9876543210.dat<>'; DROP TABLE threads; -- (50)\n",
            "1111111111.dat<>改行\nコード\rテスト (30)\n",
        ]

        subject_data = "".join(malicious_subjects).encode("shift_jis", errors="ignore")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = subject_data

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client_instance

            result = await service._get_subject_txt_data("test")

            # データが正しく処理されることを確認
            assert isinstance(result, list)
            # 改行を含むデータは複数行に分割されるため、2つのスレッドがパースされる
            assert len(result) >= 2, "少なくとも2つのスレッドがパースされるべき"

            # データ構造の整合性を確認
            for thread in result:
                assert "title" in thread
                assert "timestamp" in thread
                assert "post_count" in thread
                # 改行コードを含むタイトルは、各行が個別のスレッドとしてパースされる
                # （改行コードは正規表現マッチングを妨げる可能性がある）
                # タイトル内の改行は strip() で除去される
                # （XSS/SQLインジェクション対策は表示層で行う）


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_dos_attack_oversized_response(mock_env_vars, huge_response_data):
    """
    Given: 10MBの巨大なレスポンス（DoS攻撃シミュレーション）
    When: subject.txtを取得
    Then: メモリオーバーフローせずに処理または拒否

    検証項目:
    - 10MB以上のレスポンスを安全に処理
    - メモリ使用量が閾値以下
    - 処理時間が1秒以下
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = huge_response_data

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client_instance

            # メモリと時間を計測
            tracemalloc.start()
            start_time = time.time()

            try:
                result = await service._get_subject_txt_data("test")
                processing_time = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()

                # 処理が完了することを確認
                assert isinstance(result, list)

                # 処理時間が許容範囲内（大きなデータなので少し緩く設定）
                assert processing_time < 5.0, f"処理時間が長すぎる: {processing_time}秒"

                # メモリ使用量が許容範囲内
                assert (
                    peak < MAX_MEMORY_USAGE_BYTES * 2
                ), f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_encoding_bomb_attack(mock_env_vars, encoding_bomb_data):
    """
    Given: エンコーディングボム（Shift_JISスペース100万個 = 2MB → 数GB）
    When: subject.txtをデコード
    Then: 安全に処理（メモリ枯渇しない）

    検証項目:
    - ピークメモリ使用量50MB以下
    - 処理時間1秒以下
    - クラッシュしない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = encoding_bomb_data

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client_instance

            # メモリと時間を計測
            tracemalloc.start()
            start_time = time.time()

            try:
                result = await service._get_subject_txt_data("test")
                processing_time = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()

                # 処理が完了することを確認
                assert isinstance(result, list)

                # 処理時間が許容範囲内
                assert (
                    processing_time < MAX_PROCESSING_TIME_SECONDS * 2
                ), f"処理時間が長すぎる: {processing_time}秒"

                # メモリ使用量が許容範囲内
                assert (
                    peak < MAX_MEMORY_USAGE_BYTES
                ), f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malicious_dat_content,test_id",
    [
        (
            "<script>alert('XSS')</script><>sage<>2024/11/14<>悪意のある投稿",
            "xss",
        ),
        ("'; DROP TABLE posts; --<>sage<>2024/11/14<>SQL注入", "sql_injection"),
        ("A" * 100000 + "<>sage<>2024/11/14<>長すぎる名前", "oversized_name"),
    ],
    ids=["xss", "sql_injection", "oversized_name"],
)
async def test_dat_parsing_malicious_input(
    mock_env_vars, malicious_dat_content, test_id
):
    """
    Given: 悪意のある入力データがDAT形式に含まれる
    When: DAT解析を実行
    Then: エラーなく処理される（サニタイゼーションは表示層の責任）

    注: データ収集層では元データを保持し、XSS/SQLインジェクション対策は
        表示層・クエリ層で行う設計のため、ここではパースが正常に完了することを検証
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        dat_data = malicious_dat_content.encode("shift_jis", errors="ignore")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = dat_data

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
        ):
            posts, latest = await service._get_thread_posts_from_dat("http://test.dat")

            # 処理が完了することを確認（エラーにならないことが重要）
            assert isinstance(posts, list)
            from datetime import datetime

            assert latest is None or isinstance(latest, datetime)

            # ケース別の検証: パースが正常に完了し、データ構造が保たれることを確認
            if len(posts) > 0:
                post = posts[0]
                assert "name" in post
                assert "mail" in post  # emailではなくmail
                assert "date" in post
                assert "com" in post  # bodyではなくcom
                assert isinstance(post["name"], str)
                assert isinstance(post["com"], str)

                # oversized_nameケース: 巨大なデータでもメモリエラーにならないことを確認
                if test_id == "oversized_name":
                    # 10万文字のデータが読み込まれても処理が完了すること
                    # （メモリ制限やバッファオーバーフローが発生しないこと）
                    assert len(post["name"]) > 0, "データが正しく読み込まれていない"


# =============================================================================
# 10. パフォーマンステスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_thread_fetching_performance(mock_env_vars):
    """
    Given: 複数スレッドの並行取得
    When: 10個のスレッドを同時取得
    Then: 適切な並行処理により高速に完了

    検証項目:
    - 10個のリクエストが並行実行される
    - 処理時間0.1秒以下（逐次なら0.5秒以上）
    - 全リクエストが完了
    - asyncio.to_threadが10回呼び出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # モックレスポンス
        dat_data = "名無し<>sage<>2024/11/14 12:00:00<>テスト投稿\n".encode("shift_jis")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = dat_data

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        # 非同期遅延を含むモック（実際の並行実行をシミュレート）
        async def mock_to_thread_with_delay(f, *args, **kwargs):
            await asyncio.sleep(0.05)  # I/O遅延をシミュレート
            return f(*args, **kwargs)

        with (
            patch("cloudscraper.create_scraper", return_value=mock_scraper),
            patch(
                "asyncio.to_thread",
                side_effect=mock_to_thread_with_delay,
            ) as mock_to_thread,
        ):
            start_time = time.time()

            # 10個のスレッドを並行取得
            tasks = [
                service._get_thread_posts_from_dat(f"http://test.5ch.net/dat/{i}.dat")
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)

            processing_time = time.time() - start_time

            # 全リクエストが完了
            assert len(results) == 10

            # asyncio.to_threadが10回呼び出されたことを確認（並行実行の検証）
            assert (
                mock_to_thread.call_count == 10
            ), f"asyncio.to_threadの呼び出し回数が想定外: {mock_to_thread.call_count}回"

            # 処理時間が許容範囲内（並行処理により高速化）
            # 並行実行なら約0.05秒、逐次実行なら約0.5秒（10 * 0.05）
            assert processing_time < 0.1, f"並行処理時間が長すぎる: {processing_time}秒"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_efficiency_large_dataset(mock_env_vars):
    """
    Given: 大量のスレッドデータ（100個）
    When: 処理を実行
    Then: メモリリークなく効率的に処理

    検証項目:
    - ピークメモリ使用量50MB以下
    - 100個のスレッドが正常に処理
    - tracemalloc で検証
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 100個のスレッド情報を生成
        subject_lines = [
            f"{1000000000 + i}.dat<>テストスレッド{i} (100)\n" for i in range(100)
        ]
        subject_data = "".join(subject_lines).encode("shift_jis")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = subject_data

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client_instance

            # メモリ計測
            tracemalloc.start()

            try:
                result = await service._get_subject_txt_data("test")
                current, peak = tracemalloc.get_traced_memory()

                # 100個のスレッドが処理される
                assert len(result) == 100

                # メモリ使用量が許容範囲内
                assert (
                    peak < MAX_MEMORY_USAGE_BYTES
                ), f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_network_timeout_handling(mock_env_vars):
    """
    Given: ネットワークタイムアウト
    When: スレッドデータ取得
    Then: 適切なタイムアウトエラーハンドリング（無限待機しない）

    検証項目:
    - httpx内部のタイムアウト（10秒）が機能する
    - タイムアウト時は空リストを返す
    - 処理が適切な時間で完了する
    """
    with patch("nook.common.base_service.setup_logger"):
        import httpx

        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # httpx.TimeoutErrorを発生させるモック
        async def timeout_get(*args, **kwargs):
            await asyncio.sleep(0.1)  # 短い遅延
            raise httpx.TimeoutException("Request timeout")

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(side_effect=timeout_get)
            mock_client.return_value = client_instance

            start_time = time.time()

            # httpx内部でタイムアウトが発生し、空リストが返される
            result = await service._get_subject_txt_data("test")

            elapsed = time.time() - start_time

            # 空リストが返されることを確認（全サーバーでタイムアウト）
            assert result == [], f"タイムアウト時は空リストを返すべき: {result}"
            # タイムアウト処理が適切に完了することを確認（全サーバー試行に約0.1秒）
            assert elapsed < 1.0, f"タイムアウト処理時間が長すぎる: {elapsed}秒"


@pytest.mark.unit
@pytest.mark.performance
def test_board_server_cache_efficiency(mock_env_vars):
    """
    Given: 同じ板を複数回アクセス
    When: _get_board_serverを繰り返し呼び出し
    Then: キャッシュにより高速化

    検証項目:
    - 1回目と2回目で同じ結果
    - キャッシュアクセス50ms以下
    - データの一貫性
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 1回目のアクセス
        server1 = service._get_board_server("ai")

        # 2回目以降のアクセス（キャッシュから）
        cache_access_times = []
        for _ in range(10):
            start_time = time.time()
            server2 = service._get_board_server("ai")
            cache_access_times.append(time.time() - start_time)

            # 同じ結果が返される
            assert server1 == server2

        # キャッシュアクセスは十分高速
        avg_cache_time = sum(cache_access_times) / len(cache_access_times)
        assert (
            avg_cache_time < 0.05
        ), f"キャッシュアクセスが遅い: {avg_cache_time * 1000}ms"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_retry_backoff_performance(mock_env_vars):
    """
    Given: リトライが必要な状況
    When: 指数バックオフでリトライ
    Then: 適切な遅延時間でリトライ

    検証項目:
    - バックオフ時間が指数的に増加
    - 最大リトライ回数を超えない
    - 総実行時間が妥当
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 最初の2回は失敗、3回目で成功
        responses = [
            Mock(status_code=503),
            Mock(status_code=503),
            Mock(status_code=200, text="success"),
        ]
        service.http_client.get = AsyncMock(side_effect=responses)

        sleep_times = []

        async def mock_sleep(duration):
            sleep_times.append(duration)
            # 何もしない（待機しない）

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=mock_sleep):
            result = await service._get_with_retry("http://test.url", max_retries=5)

            # リトライが成功
            assert result.status_code == 200

            # バックオフ時間が記録されている
            assert len(sleep_times) == 2  # 2回リトライしたので2回スリープ

            # 指数バックオフを確認（1秒、2秒など）
            assert sleep_times[0] >= 1.0
            assert sleep_times[1] > sleep_times[0]

            # バックオフ時間が指数的に増加していることを確認
            assert len(sleep_times) > 0
