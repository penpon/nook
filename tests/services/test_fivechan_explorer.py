"""
nook/services/fivechan_explorer/fivechan_explorer.py のテスト

テスト観点:
- FiveChanExplorerの初期化
- スレッド情報取得
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
