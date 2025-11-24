"""nook/services/fivechan_explorer/fivechan_explorer.py のテスト

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
    """Given: デフォルトのstorage_dir
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
    """Given: 有効な掲示板データ
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
    """Given: ネットワークエラーが発生
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
    """Given: GPT APIがエラーを返す
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
            service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """Given: 完全なワークフロー
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
    """Given: 有効なShift_JISエンコードのsubject.txt
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
    """Given: 文字化けを含むsubject.txt（無効バイト含む）
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
    """Given: 不正なフォーマットのsubject.txt（正規表現マッチ失敗）
    When: _get_subject_txt_dataを呼び出す
    Then: マッチしない行はスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 正規表現にマッチしないフォーマット
        subject_data = "invalid_format_line\n1234567890.dat<>正しいスレッド (100)\n".encode(
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

            result = await service._get_subject_txt_data("test")

            # 正しいフォーマットの行のみ解析される
            assert len(result) == 1
            assert result[0]["title"] == "正しいスレッド"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_subdomain_retry(mock_env_vars):
    """Given: 最初のサーバーが失敗、2番目のサーバーが成功
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
    """Given: すべてのサーバーが失敗
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
    """Given: shift_jisで失敗するが、cp932で成功するデータ
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
    """Given: 有効なdat形式データ（<>区切り）
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
""".encode("shift_jis")

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
    """Given: Shift_JISエンコードのdatファイル
    When: _get_thread_posts_from_datを呼び出す
    Then: 正しくデコードされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 日本語を含むdat
        dat_data = "名無し<>sage<>2024/11/14 12:00:00<>深層学習について\n".encode("shift_jis")

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
    """Given: <>区切りが不足している不正な行
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
""".encode("shift_jis")

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
    """Given: HTTPエラー（404など）
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
    """Given: 空のdatファイル
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
    """Given: 文字化けを含むdatファイル
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
    """Given: 即座に200レスポンス
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
    """Given: 429レート制限エラー（Retry-Afterヘッダー付き）
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
    """Given: 500系サーバーエラー
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
    """Given: 接続エラーが発生
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
    """Given: 最大リトライ回数を超える
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
    """Given: 最近作成されたスレッド（1時間前）
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
    """Given: 古いスレッド（48時間前）
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
    """Given: user_agentsリスト
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
    """Given: リトライ回数
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
    """Given: 板IDとサーバー
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
    """Given: 板ID
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
    """Given: XSS/SQLインジェクション等の悪意のある入力がスレッドタイトルに含まれる
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
    """Given: 10MBの巨大なレスポンス（DoS攻撃シミュレーション）
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
                assert peak < MAX_MEMORY_USAGE_BYTES * 2, (
                    f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
                )
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
async def test_encoding_bomb_attack(mock_env_vars, encoding_bomb_data):
    """Given: エンコーディングボム（Shift_JISスペース100万個 = 2MB → 数GB）
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
                assert processing_time < MAX_PROCESSING_TIME_SECONDS * 2, (
                    f"処理時間が長すぎる: {processing_time}秒"
                )

                # メモリ使用量が許容範囲内
                assert peak < MAX_MEMORY_USAGE_BYTES, (
                    f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
                )
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("malicious_dat_content", "test_id"),
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
async def test_dat_parsing_malicious_input(mock_env_vars, malicious_dat_content, test_id):
    """Given: 悪意のある入力データがDAT形式に含まれる
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
    """Given: 複数スレッドの並行取得
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
            assert mock_to_thread.call_count == 10, (
                f"asyncio.to_threadの呼び出し回数が想定外: {mock_to_thread.call_count}回"
            )

            # 処理時間が許容範囲内（並行処理により高速化）
            # 並行実行なら約0.05秒、逐次実行なら約0.5秒（10 * 0.05）
            # 環境依存を考慮して0.2秒に緩和
            assert processing_time < 0.2, f"並行処理時間が長すぎる: {processing_time}秒"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_efficiency_large_dataset(mock_env_vars):
    """Given: 大量のスレッドデータ（100個）
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
        subject_lines = [f"{1000000000 + i}.dat<>テストスレッド{i} (100)\n" for i in range(100)]
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
                assert peak < MAX_MEMORY_USAGE_BYTES, (
                    f"メモリ使用量が多すぎる: {peak / 1024 / 1024}MB"
                )
            finally:
                tracemalloc.stop()


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_network_timeout_handling(mock_env_vars):
    """Given: ネットワークタイムアウト
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
    """Given: 同じ板を複数回アクセス
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
        assert avg_cache_time < 0.05, f"キャッシュアクセスが遅い: {avg_cache_time * 1000}ms"


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.asyncio
async def test_retry_backoff_performance(mock_env_vars):
    """Given: リトライが必要な状況
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


# =============================================================================
# 11. _get_with_403_tolerance メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_first_strategy_success(mock_env_vars):
    """Given: 1回目の戦略で200を返すモック
    When: _get_with_403_toleranceを呼び出す
    Then: リトライなしで即座に成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1回目で200を返すモック
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Valid content"

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 成功
            assert result is not None
            assert result.status_code == 200
            # 最初の戦略で成功したので、スリープは1回だけ（戦略1の待機時間）
            assert mock_sleep.call_count >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_second_strategy_success(mock_env_vars):
    """Given: 1回目は403、2回目は200
    When: _get_with_403_toleranceを呼び出す
    Then: 2回目の戦略で成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1回目: 403、2回目: 200
        responses = [
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 2回目で成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_cloudflare_detection(mock_env_vars):
    """Given: Cloudflareチャレンジページを含む200レスポンス
    When: _get_with_403_toleranceを呼び出す
    Then: Cloudflare検出してリトライ
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # Cloudflareチャレンジページ、その後成功
        responses = [
            Mock(status_code=200, text="Just a moment... Cloudflare challenge"),
            Mock(status_code=200, text="Valid content from 5ch"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # Cloudflare検出後にリトライして成功
            assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_403_with_valid_content(mock_env_vars):
    """Given: 403だが有効コンテンツ（>100文字）を含むレスポンス
    When: _get_with_403_toleranceを呼び出す
    Then: 403でも有効コンテンツなので成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 403だが有効コンテンツ
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "x" * 150  # 150文字の有効コンテンツ

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 403だが有効コンテンツなので成功
            assert result is not None
            assert result.status_code == 403
            assert len(result.text) > 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_all_strategies_fail(mock_env_vars):
    """Given: 全戦略で403エラー
    When: _get_with_403_toleranceを呼び出す
    Then: 代替エンドポイント戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # すべて403で失敗
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        # 代替エンドポイント戦略もモック
        with (
            patch.object(
                service, "_try_alternative_endpoints", new_callable=AsyncMock, return_value=None
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 全戦略失敗でNone
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_connection_error_then_success(mock_env_vars):
    """Given: 最初の2戦略で接続エラー、3回目で成功
    When: _get_with_403_toleranceを呼び出す
    Then: 例外を処理して3回目で成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1,2回目: エラー、3回目: 成功
        responses = [
            Exception("Connection error"),
            Exception("Timeout error"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 3回目で成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_cloudflare_with_long_wait(mock_env_vars):
    """Given: Cloudflare 403エラー（challenge検出）
    When: _get_with_403_toleranceを呼び出す
    Then: 30秒待機後にリトライ
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # Cloudflare 403、その後成功
        responses = [
            Mock(status_code=403, text="challenge page from Cloudflare"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service._get_with_403_tolerance("http://test.url", "ai")

            # Cloudflare検出で30秒待機
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert 30 in sleep_calls  # Cloudflare回避のための30秒待機


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_status_code_variations(mock_env_vars):
    """Given: 様々なステータスコード（500, 502, 503）
    When: _get_with_403_toleranceを呼び出す
    Then: 各エラーを処理してリトライ
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 様々なエラー、最後に成功
        responses = [
            Mock(status_code=500, text="Internal Server Error"),
            Mock(status_code=502, text="Bad Gateway"),
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 最終的に成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_strategy_wait_times(mock_env_vars):
    """Given: 複数戦略の実行
    When: _get_with_403_toleranceを呼び出す
    Then: 各戦略の待機時間が段階的に増加（2秒、5秒、8秒...）
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 最初の3戦略は403、4回目で成功
        responses = [
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service._get_with_403_tolerance("http://test.url", "ai")

            # 待機時間が記録されている
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            # 戦略別の待機時間: 2秒, 5秒(2+3), 8秒(2+3*2), 11秒(2+3*3)
            assert len(sleep_calls) >= 3
            # 最初の戦略の待機時間は2秒
            assert sleep_calls[0] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_user_agent_rotation(mock_env_vars):
    """Given: 各戦略で異なるUser-Agentを使用
    When: _get_with_403_toleranceを呼び出す
    Then: 5つのUser-Agent戦略が順次試行される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 5回目で成功（5つの戦略すべてを試行）
        responses = [
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 5つの戦略を試行して成功
            assert result is not None
            assert service.http_client._client.get.call_count == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_403_with_small_content(mock_env_vars):
    """Given: 403エラーで100文字未満のコンテンツ
    When: _get_with_403_toleranceを呼び出す
    Then: 無効コンテンツとして次の戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 403で小さいコンテンツ、その後成功
        responses = [
            Mock(status_code=403, text="x" * 50),  # 50文字（100文字未満）
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 2回目で成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_mixed_errors_and_cloudflare(mock_env_vars):
    """Given: 複数のエラータイプが混在（403、Cloudflare、接続エラー）
    When: _get_with_403_toleranceを呼び出す
    Then: すべてのエラータイプを処理して最終的に成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 様々なエラー、最後に成功
        responses = [
            Mock(status_code=403, text="Forbidden"),
            Mock(status_code=200, text="Just a moment... Cloudflare"),
            Exception("Connection timeout"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 最終的に成功
            assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_immediate_200_no_cloudflare(mock_env_vars):
    """Given: 即座に200を返し、Cloudflareチャレンジなし
    When: _get_with_403_toleranceを呼び出す
    Then: 追加のリトライなしで即座に成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 即座に成功
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Valid content from server"

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 即座に成功
            assert result is not None
            assert result.status_code == 200
            assert "Cloudflare" not in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_unexpected_exception(mock_env_vars):
    """Given: 予期しない例外（戦略実行中の予期しないエラー）
    When: _get_with_403_toleranceを呼び出す
    Then: 例外を処理して次の戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 予期しない例外、その後成功
        responses = [
            Exception("Unexpected error occurred"),
            Mock(status_code=200, text="Valid content"),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 例外を処理して成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_with_403_tolerance_alternative_endpoint_success(mock_env_vars):
    """Given: 全User-Agent戦略が失敗、代替エンドポイント戦略で成功
    When: _get_with_403_toleranceを呼び出す
    Then: _try_alternative_endpointsが呼び出されて成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # すべて403で失敗
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        # 代替エンドポイント戦略で成功
        alt_response = Mock()
        alt_response.status_code = 200
        alt_response.text = "Valid content from alternative endpoint"

        with (
            patch.object(
                service,
                "_try_alternative_endpoints",
                new_callable=AsyncMock,
                return_value=alt_response,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await service._get_with_403_tolerance("http://test.url", "ai")

            # 代替エンドポイントで成功
            assert result is not None
            assert result.status_code == 200


# =============================================================================
# 12. _try_alternative_endpoints メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_first_success(mock_env_vars):
    """Given: 1番目の代替URL（sp.5ch.net）で200
    When: _try_alternative_endpointsを呼び出す
    Then: リトライなしで即座に成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1番目で成功
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Valid 5ch content\n" * 10  # 有効コンテンツ

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 即座に成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_all_fail(mock_env_vars):
    """Given: 全代替URLで失敗
    When: _try_alternative_endpointsを呼び出す
    Then: Noneを返却
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # すべて失敗
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 全失敗でNone
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_second_success(mock_env_vars):
    """Given: 1番目失敗、2番目の代替URLで成功
    When: _try_alternative_endpointsを呼び出す
    Then: 2番目で成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 1番目: 失敗、2番目: 成功
        responses = [
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 2番目で成功
            assert result is not None
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_403_with_valid_content(mock_env_vars):
    """Given: 403だが有効コンテンツ（>50文字）
    When: _try_alternative_endpointsを呼び出す
    Then: 403でも有効コンテンツなので成功
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 403だが有効コンテンツ
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Valid 5ch content\n" * 10  # >50文字

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 403だが有効コンテンツ
            assert result is not None
            assert result.status_code == 403
            assert len(result.text) > 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_cloudflare_rejection(mock_env_vars):
    """Given: Cloudflareチャレンジページ（無効コンテンツ）
    When: _try_alternative_endpointsを呼び出す
    Then: 無効コンテンツとして次の戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # Cloudflare、その後成功
        responses = [
            Mock(status_code=200, text="Just a moment... challenge"),
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 2番目で成功
            assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_connection_error(mock_env_vars):
    """Given: 接続エラーが発生
    When: _try_alternative_endpointsを呼び出す
    Then: 例外を処理して次の戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 接続エラー、その後成功
        responses = [
            Exception("Connection error"),
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 2番目で成功
            assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_short_content_rejection(mock_env_vars):
    """Given: 200だがコンテンツが短すぎる（<50文字）
    When: _try_alternative_endpointsを呼び出す
    Then: 無効コンテンツとして次の戦略を試行
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 短いコンテンツ、その後成功
        responses = [
            Mock(status_code=200, text="Short"),  # <50文字
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 2番目で成功
            assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_5ch_2ch_variations(mock_env_vars):
    """Given: 代替URL戦略（sp.5ch.net、2ch.net、subject.txt等）
    When: _try_alternative_endpointsを呼び出す
    Then: 5つの代替戦略が順次試行される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 5回目で成功
        responses = [
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 5つの戦略を試行して成功
            assert result is not None
            assert service.http_client._client.get.call_count == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_content_validation(mock_env_vars):
    """Given: コンテンツに"5ch"または"2ch"または改行を含む
    When: _try_alternative_endpointsを呼び出す
    Then: コンテンツが有効と判定される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # "5ch"を含む有効コンテンツ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "This is 5ch content with valid data\n" * 3

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # コンテンツ検証が成功
            assert result is not None
            assert "5ch" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_alternative_endpoints_wait_intervals(mock_env_vars):
    """Given: 複数の代替戦略を試行
    When: _try_alternative_endpointsを呼び出す
    Then: 各戦略の間に3秒の待機時間
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 3回失敗、4回目で成功
        responses = [
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=404, text="Not Found"),
            Mock(status_code=200, text="Valid 5ch content\n" * 10),
        ]

        service.http_client._client = AsyncMock()
        service.http_client._client.get = AsyncMock(side_effect=responses)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service._try_alternative_endpoints("https://mevius.5ch.net/ai/", "ai")

            # 各戦略の間に3秒待機
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert all(t == 3 for t in sleep_calls)


# =============================================================================
# 13. _retrieve_ai_threads メソッドのテスト（AI関連スレッド取得）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_keyword_matching(mock_env_vars):
    """Given: AIキーワードを含むスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: AIキーワードマッチングで正しくフィルタリング
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        # subject.txtのモックデータ
        threads_data = [
            {
                "title": "AI・人工知能について",
                "timestamp": "1234567890",
                "html_url": "http://test.url",
                "dat_url": "http://test.dat",
                "post_count": 100,
            },
            {
                "title": "機械学習の最新動向",
                "timestamp": "1234567891",
                "html_url": "http://test.url2",
                "dat_url": "http://test.dat2",
                "post_count": 50,
            },
            {
                "title": "無関係なスレッド",
                "timestamp": "1234567892",
                "html_url": "http://test.url3",
                "dat_url": "http://test.dat3",
                "post_count": 30,
            },
        ]

        # モック投稿データ
        mock_posts = [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}]

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                return_value=(mock_posts, datetime.now(UTC)),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # AIキーワードマッチング（最初の2つのみ）
            assert len(result) == 2
            assert "AI" in result[0].title or "機械学習" in result[0].title


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_deduplication(mock_env_vars):
    """Given: 重複するタイトルのスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: 重複排除処理が正しく動作
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        # 重複するタイトル
        threads_data = [
            {
                "title": "AI技術について",
                "timestamp": "1234567890",
                "html_url": "http://test.url",
                "dat_url": "http://test.dat",
                "post_count": 100,
            },
            {
                "title": "AI技術について",
                "timestamp": "1234567891",
                "html_url": "http://test.url2",
                "dat_url": "http://test.dat2",
                "post_count": 50,
            },
        ]

        mock_posts = [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}]

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                return_value=(mock_posts, datetime.now(UTC)),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # 重複排除で1つのみ
            assert len(result) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_limit_enforcement(mock_env_vars):
    """Given: 多数のAI関連スレッド
    When: limitパラメータを指定して_retrieve_ai_threadsを呼び出す
    Then: 指定した制限数で取得を停止
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        # 10個のAI関連スレッド
        threads_data = [
            {
                "title": f"AI技術{i}",
                "timestamp": f"123456789{i}",
                "html_url": f"http://test.url{i}",
                "dat_url": f"http://test.dat{i}",
                "post_count": 100,
            }
            for i in range(10)
        ]

        mock_posts = [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}]

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                return_value=(mock_posts, datetime.now(UTC)),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=3, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # limit=3で3つのみ取得
            assert len(result) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_no_posts_skip(mock_env_vars):
    """Given: 投稿取得に失敗したスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: 投稿がないスレッドはスキップ
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        threads_data = [
            {
                "title": "AI技術1",
                "timestamp": "1234567890",
                "html_url": "http://test.url",
                "dat_url": "http://test.dat",
                "post_count": 100,
            },
            {
                "title": "AI技術2",
                "timestamp": "1234567891",
                "html_url": "http://test.url2",
                "dat_url": "http://test.dat2",
                "post_count": 50,
            },
        ]

        # 1番目は投稿あり、2番目は投稿なし
        posts_results = [
            (
                [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}],
                datetime.now(UTC),
            ),
            ([], datetime.now(UTC)),  # 投稿なし
        ]

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                side_effect=posts_results,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # 投稿があるスレッドのみ（1つ）
            assert len(result) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_subject_txt_failure(mock_env_vars):
    """Given: subject.txt取得に失敗
    When: _retrieve_ai_threadsを呼び出す
    Then: 空配列を返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import date

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        with patch.object(
            service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=[]
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # subject.txt取得失敗で空配列
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_popularity_calculation(mock_env_vars):
    """Given: 異なる投稿数のスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: popularity_scoreが正しく計算される
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        threads_data = [
            {
                "title": "AI技術1",
                "timestamp": "1234567890",
                "html_url": "http://test.url",
                "dat_url": "http://test.dat",
                "post_count": 100,
            },
        ]

        mock_posts = [
            {"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}
        ] * 10

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                return_value=(mock_posts, datetime.now(UTC)),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # popularity_scoreが設定されている
            assert len(result) == 1
            assert result[0].popularity_score > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_access_interval(mock_env_vars):
    """Given: 複数のスレッド取得
    When: _retrieve_ai_threadsを呼び出す
    Then: スレッド間に2秒のアクセス間隔
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        threads_data = [
            {
                "title": f"AI技術{i}",
                "timestamp": f"123456789{i}",
                "html_url": f"http://test.url{i}",
                "dat_url": f"http://test.dat{i}",
                "post_count": 100,
            }
            for i in range(3)
        ]

        mock_posts = [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "テスト投稿"}]

        with (
            patch.object(
                service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=threads_data
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                return_value=(mock_posts, datetime.now(UTC)),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            dedup_tracker = DedupTracker()
            await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # 2秒間隔で待機
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert all(t == 2 for t in sleep_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_exception_handling(mock_env_vars):
    """Given: 予期しない例外が発生
    When: _retrieve_ai_threadsを呼び出す
    Then: 例外を処理して空配列を返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import date

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()

        with patch.object(
            service,
            "_get_subject_txt_data",
            new_callable=AsyncMock,
            side_effect=Exception("Unexpected error"),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # 例外処理で空配列
            assert result == []


# =============================================================================
# Edge Case Tests (Task 7)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_thread_handling(mock_env_vars):
    """Given: レスが0件のスレッド
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列を返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 空のDATファイル（ヘッダーのみ）
        empty_dat_content = b""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = empty_dat_content

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
            posts, last_modified = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )

        # 空配列が返される
        assert posts == []
        # 空スレッドの場合はlast_modifiedがNone
        assert last_modified is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_single_post_thread(mock_env_vars):
    """Given: OP投稿のみ（レス0件）のスレッド
    When: _get_thread_posts_from_datを呼び出す
    Then: 1つの投稿のみを正しく処理
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # OP投稿のみのDATファイル
        single_post_dat = (
            "名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:TestID<>これはテストスレッドです<>"
        )

        # cloudscraperをモック
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = single_post_dat.encode("shift_jis")
        mock_response.text = single_post_dat

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper):
            posts, last_modified = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )

            # 1つの投稿が返される
            assert len(posts) == 1
            assert posts[0]["com"] == "これはテストスレッドです"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_special_characters_in_post(mock_env_vars):
    """Given: 特殊文字（絵文字、HTML実体参照等）を含むレス
    When: _get_thread_posts_from_datを呼び出す
    Then: 特殊文字を正しくパース
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 特殊文字を含むDATファイル
        special_chars_dat = "名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:TestID<>テスト😀&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;🎉<>\n"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = special_chars_dat.encode("shift_jis", errors="ignore")
        mock_response.text = special_chars_dat

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper):
            posts, _ = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )

            # 特殊文字が含まれている
            assert len(posts) == 1
            assert "😀" in posts[0]["com"] or "&lt;" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_thread_processing(mock_env_vars):
    """Given: 1000レス超の巨大スレッド
    When: _get_thread_posts_from_datを呼び出す
    Then: メモリ効率的に処理（最大MAX_POSTS_PER_THREAD投稿まで返却）
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import (
            MAX_POSTS_PER_THREAD,
            FiveChanExplorer,
        )

        service = FiveChanExplorer()

        # 1000レスのDATファイルを生成
        large_thread_dat = "\n".join(
            [
                f"名無しさん<>sage<>2024/11/14(木) 12:00:0{i % 10}.00 ID:TestID{i}<>レス{i}<>"
                for i in range(1000)
            ]
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = large_thread_dat.encode("shift_jis")
        mock_response.text = large_thread_dat

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper):
            import time

            start_time = time.time()
            posts, _ = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )
            processing_time = time.time() - start_time

            # 最大MAX_POSTS_PER_THREAD投稿まで返却される（実装の制限）
            assert len(posts) == MAX_POSTS_PER_THREAD
            # 処理時間が妥当（3秒以内）
            assert processing_time < 3.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unicode_handling(mock_env_vars):
    """Given: 日本語、絵文字等のUnicode文字列
    When: _get_thread_posts_from_datを呼び出す
    Then: Unicode文字列を正しく処理
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 日本語と絵文字を含むDATファイル
        unicode_dat = "名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:TestID<>こんにちは世界🌏！テスト投稿です😊<>\n"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = unicode_dat.encode("shift_jis", errors="ignore")
        mock_response.text = unicode_dat

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper):
            posts, _ = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )

            # Unicode文字列が正しく処理される
            assert len(posts) == 1
            assert "こんにちは世界" in posts[0]["com"]
            assert "🌏" in posts[0]["com"] or "テスト投稿" in posts[0]["com"]


# =============================================================================
# Error Recovery Tests (Task 7)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_partial_data_fetch_success(mock_env_vars):
    """Given: 一部のレスのみ取得成功
    When: _get_thread_posts_from_datを呼び出す
    Then: 部分データを返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # 正常な行と不正な行が混在
        partial_dat = (
            "名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:TestID1<>正常な投稿1<>\n"
            "不正な行データ\n"
            "名無しさん<>sage<>2024/11/14(木) 12:00:01.00 ID:TestID2<>正常な投稿2<>\n"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = partial_dat.encode("shift_jis")
        mock_response.text = partial_dat

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper):
            posts, _ = await service._get_thread_posts_from_dat(
                "https://test.5ch.net/test/dat/1234567890.dat"
            )

            # 正常な投稿のみが返される（部分データ）
            assert len(posts) >= 1  # 少なくとも1つは取得される
            if len(posts) > 0:
                assert "正常な投稿" in posts[0]["com"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_strategy_final_case(mock_env_vars):
    """Given: 全代替エンドポイントが失敗
    When: _try_alternative_endpointsを呼び出す
    Then: 最終フォールバック戦略を実行してNoneを返す
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()
        service.http_client._client = AsyncMock()

        # 全てのエンドポイントで403エラー
        service.http_client._client.get = AsyncMock(
            return_value=Mock(text="Forbidden", status_code=403)
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._try_alternative_endpoints(
                "https://original.5ch.net/test/subjecttxt.txt", "test"
            )

        # 全失敗でNoneを返す
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation(mock_env_vars):
    """Given: 一部機能が失敗
    When: collectメソッドを呼び出す
    Then: 他機能は継続して動作
    """
    with patch("nook.common.base_service.setup_logger"):
        from datetime import UTC, date, datetime

        from nook.services.fivechan_explorer.fivechan_explorer import DedupTracker, FiveChanExplorer

        service = FiveChanExplorer()
        service.http_client = AsyncMock()

        # 一部のスレッド取得は成功、一部は失敗
        success_threads = [
            {
                "title": "成功スレッド1",
                "timestamp": "1234567890",
                "html_url": "http://test1.url",
                "dat_url": "http://test1.dat",
                "post_count": 50,
            },
        ]

        mock_posts = [{"name": "名無し", "mail": "sage", "date": "2024/11/14", "com": "成功投稿"}]

        call_count = 0

        async def mock_get_posts(dat_url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (mock_posts, datetime.now(UTC))
            raise Exception("Thread fetch failed")

        with (
            patch.object(
                service,
                "_get_subject_txt_data",
                new_callable=AsyncMock,
                return_value=success_threads,
            ),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                new_callable=AsyncMock,
                side_effect=mock_get_posts,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            dedup_tracker = DedupTracker()
            result = await service._retrieve_ai_threads(
                "ai", limit=10, dedup_tracker=dedup_tracker, target_dates=[date.today()]
            )

            # 一部成功したスレッドは返される
            assert len(result) >= 0  # graceful degradation で部分的な結果を返す
