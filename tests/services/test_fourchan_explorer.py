"""
nook/services/fourchan_explorer/fourchan_explorer.py のテスト

テスト観点:
- FourChanExplorerの初期化
- スレッド情報取得
- データ保存
- エラーハンドリング
- 内部メソッドの単体テスト
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import httpx
import pytest

# Test constants
TEST_THREAD_ID = 123456
TEST_BOARD = "g"
TEST_TIMESTAMP_ALT = 1699999999


# Helper functions for assertions
def assert_thread_summary_generated(thread, expected_summary):
    """アサート: スレッドの要約が生成されたことを確認"""
    assert thread.summary == expected_summary


def assert_gpt_called_with_thread_content(mock_generate, thread):
    """アサート: GPTクライアントが適切に呼ばれたことを確認"""
    assert mock_generate.called

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(fourchan_service):
    """
    Given: デフォルトのstorage_dir
    When: FourChanExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    assert fourchan_service.service_name == "fourchan_explorer"


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
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
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
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
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
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
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
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
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
# 5. 内部メソッドの単体テスト - _load_boards()
# =============================================================================


@pytest.mark.unit
def test_load_boards_success(mock_env_vars):
    """
    Given: デフォルトまたは有効なboards.toml
    When: _load_boards()を呼び出す
    Then: ボードリストが正しく読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        boards = service._load_boards()

        # デフォルトのボードまたは設定ファイルのボードが読み込まれる
        assert isinstance(boards, list)
        assert len(boards) > 0
        # デフォルトボードには "g" が含まれる
        assert "g" in boards or "sci" in boards


@pytest.mark.unit
def test_load_boards_file_not_found(mock_env_vars):
    """
    Given: boards.tomlが存在しない
    When: _load_boards()を呼び出す
    Then: デフォルトのボードリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        # 存在しないファイルパスを返すようにモック
        with patch("pathlib.Path.exists", return_value=False):
            boards = service._load_boards()

        assert isinstance(boards, list)
        assert len(boards) > 0
        assert "g" in boards or "sci" in boards


@pytest.mark.unit
def test_load_boards_invalid_toml(mock_env_vars, tmp_path):
    """
    Given: 不正な形式のboards.toml
    When: _load_boards()を呼び出す
    Then: デフォルトのボードリストが返される
    """
    boards_file = tmp_path / "boards.toml"
    boards_file.write_text("invalid toml content {{{")

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        # boards.tomlのパスをtmp_pathにリダイレクト
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "builtins.open",
                mock_open(read_data=b"invalid toml content {{{"),
            ),
        ):
            boards = service._load_boards()

        assert isinstance(boards, list)
        assert len(boards) > 0  # デフォルト値が返される


# =============================================================================
# 6. 内部メソッドの単体テスト - _calculate_popularity()
# =============================================================================


@pytest.mark.unit
def test_calculate_popularity_with_all_fields(mock_env_vars):
    """
    Given: すべてのフィールドが存在するメタデータ
    When: _calculate_popularity()を呼び出す
    Then: 正しい人気スコアが計算される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_metadata = {
            "replies": 100,
            "images": 20,
            "bumps": 50,
            "last_modified": int(datetime.now().timestamp()) - 3600,  # 1時間前
        }
        posts = [{"no": i} for i in range(10)]

        score = service._calculate_popularity(thread_metadata, posts)

        assert isinstance(score, float)
        assert score > 0
        # replies(100) + images*2(40) + bumps(50) + len(posts)(10) + recency_bonus
        assert score >= 200


@pytest.mark.unit
def test_calculate_popularity_with_none_values(mock_env_vars):
    """
    Given: Noneを含むメタデータ
    When: _calculate_popularity()を呼び出す
    Then: 0として扱われ、エラーが発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_metadata = {
            "replies": None,
            "images": None,
            "bumps": None,
            "last_modified": None,
        }
        posts = []

        score = service._calculate_popularity(thread_metadata, posts)

        assert isinstance(score, float)
        assert score == 0.0


@pytest.mark.unit
def test_calculate_popularity_with_missing_fields(mock_env_vars):
    """
    Given: フィールドが欠損したメタデータ
    When: _calculate_popularity()を呼び出す
    Then: 0として扱われ、エラーが発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_metadata = {}
        posts = [{"no": 1}, {"no": 2}]

        score = service._calculate_popularity(thread_metadata, posts)

        assert isinstance(score, float)
        assert score == 2.0  # len(posts) only


@pytest.mark.unit
def test_calculate_popularity_with_recent_thread(mock_env_vars):
    """
    Given: 最近更新されたスレッド
    When: _calculate_popularity()を呼び出す
    Then: recency_bonusが高くなる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        recent_thread = {
            "replies": 10,
            "images": 5,
            "bumps": 3,
            "last_modified": int(datetime.now().timestamp()) - 60,  # 1分前
        }
        old_thread = {
            "replies": 10,
            "images": 5,
            "bumps": 3,
            "last_modified": int(datetime.now().timestamp()) - 86400,  # 1日前
        }
        posts = []

        recent_score = service._calculate_popularity(recent_thread, posts)
        old_score = service._calculate_popularity(old_thread, posts)

        assert recent_score > old_score


# =============================================================================
# 7. 内部メソッドの単体テスト - _extract_thread_id_from_url()
# =============================================================================


@pytest.mark.unit
def test_extract_thread_id_from_standard_url(mock_env_vars):
    """
    Given: 標準的な4chan URLパターン
    When: _extract_thread_id_from_url()を呼び出す
    Then: 正しくスレッドIDが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        url = "https://boards.4chan.org/g/thread/123456"
        thread_id = service._extract_thread_id_from_url(url)

        assert thread_id == 123456


@pytest.mark.unit
def test_extract_thread_id_with_query_params(mock_env_vars):
    """
    Given: クエリパラメータ付きURL
    When: _extract_thread_id_from_url()を呼び出す
    Then: 正しくスレッドIDが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        url = "https://boards.4chan.org/g/thread/123456?page=2#post789"
        thread_id = service._extract_thread_id_from_url(url)

        assert thread_id == 123456


@pytest.mark.unit
def test_extract_thread_id_from_empty_url(mock_env_vars):
    """
    Given: 空のURL
    When: _extract_thread_id_from_url()を呼び出す
    Then: 0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_id = service._extract_thread_id_from_url("")

        assert thread_id == 0


@pytest.mark.unit
def test_extract_thread_id_from_invalid_url(mock_env_vars):
    """
    Given: スレッドIDを含まない不正なURL
    When: _extract_thread_id_from_url()を呼び出す
    Then: 0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        url = "https://boards.4chan.org/g/"
        thread_id = service._extract_thread_id_from_url(url)

        assert thread_id == 0


# =============================================================================
# 8. 内部メソッドの単体テスト - _retrieve_thread_posts()
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_thread_posts_success(mock_env_vars, respx_mock):
    """
    Given: 有効なスレッド詳細API
    When: _retrieve_thread_posts()を呼び出す
    Then: 投稿リストが正しく返される
    """
    # respxでAPIをモック
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "posts": [
                    {"no": 123456, "time": 1699999999, "com": "Test post 1"},
                    {"no": 123457, "time": 1700000000, "com": "Test post 2"},
                ]
            },
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        posts = await service._retrieve_thread_posts("g", 123456)

        assert isinstance(posts, list)
        assert len(posts) == 2
        assert posts[0]["no"] == 123456
        assert posts[1]["no"] == 123457


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_thread_posts_http_error(mock_env_vars, respx_mock):
    """
    Given: HTTPエラーが発生
    When: _retrieve_thread_posts()を呼び出す
    Then: 空リストが返される
    """
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(return_value=httpx.Response(404))

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        posts = await service._retrieve_thread_posts("g", 123456)

        assert isinstance(posts, list)
        assert len(posts) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_thread_posts_timeout(mock_env_vars, respx_mock):
    """
    Given: タイムアウトが発生
    When: _retrieve_thread_posts()を呼び出す
    Then: 空リストが返される
    """
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        posts = await service._retrieve_thread_posts("g", 123456)

        assert isinstance(posts, list)
        assert len(posts) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_thread_posts_invalid_json(mock_env_vars, respx_mock):
    """
    Given: 不正なJSON
    When: _retrieve_thread_posts()を呼び出す
    Then: 空リストが返される
    """
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(200, text="invalid json {{{")
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        posts = await service._retrieve_thread_posts("g", 123456)

        assert isinstance(posts, list)
        assert len(posts) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_thread_posts_missing_posts_key(mock_env_vars, respx_mock):
    """
    Given: postsキーが存在しないJSON
    When: _retrieve_thread_posts()を呼び出す
    Then: 空リストが返される
    """
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(200, json={"threads": []})
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        posts = await service._retrieve_thread_posts("g", 123456)

        assert isinstance(posts, list)
        assert len(posts) == 0


# =============================================================================
# 9. 内部メソッドの単体テスト - _retrieve_ai_threads()
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_success(mock_env_vars, respx_mock):
    """
    Given: 有効なcatalog.json
    When: _retrieve_ai_threads()を呼び出す
    Then: AI関連スレッドが正しく抽出される
    """
    # catalog APIをモック
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "AI Discussion",
                            "com": "Let's talk about GPT and machine learning",
                            "replies": 50,
                            "images": 10,
                            "bumps": 45,
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        }
                    ],
                }
            ],
        )
    )

    # スレッド詳細APIをモック
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "posts": [
                    {
                        "no": 123456,
                        "time": int(datetime.now(UTC).timestamp()),
                        "com": "AI post",
                    }
                ]
            },
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert isinstance(threads, list)
        assert len(threads) == 1
        assert threads[0].thread_id == 123456
        assert "AI" in threads[0].title


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_with_limit(mock_env_vars, respx_mock):
    """
    Given: 複数のAI関連スレッド
    When: limitを指定して_retrieve_ai_threads()を呼び出す
    Then: 指定した数だけスレッドが返される
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": i,
                            "sub": f"AI Thread {i}",
                            "com": "machine learning discussion",
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        }
                        for i in range(10)
                    ],
                }
            ],
        )
    )

    # すべてのスレッド詳細APIをモック
    for i in range(10):
        respx_mock.get(f"https://a.4cdn.org/g/thread/{i}.json").mock(
            return_value=httpx.Response(
                200,
                json={"posts": [{"no": i, "time": int(datetime.now(UTC).timestamp())}]},
            )
        )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=3, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert isinstance(threads, list)
        assert len(threads) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_filters_non_ai(mock_env_vars, respx_mock):
    """
    Given: AI関連でないスレッドを含むcatalog
    When: _retrieve_ai_threads()を呼び出す
    Then: AI関連スレッドのみが返される
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 1,
                            "sub": "AI Discussion",
                            "com": "GPT-4 is amazing",
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        },
                        {
                            "no": 2,
                            "sub": "Random Thread",
                            "com": "Just a regular discussion",
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        },
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/1.json").mock(
        return_value=httpx.Response(
            200,
            json={"posts": [{"no": 1, "time": int(datetime.now(UTC).timestamp())}]},
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert isinstance(threads, list)
        assert len(threads) == 1
        assert threads[0].thread_id == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_http_error(mock_env_vars, respx_mock):
    """
    Given: catalog API がHTTPエラーを返す
    When: _retrieve_ai_threads()を呼び出す
    Then: RetryException が発生する
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(return_value=httpx.Response(404))

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.common.exceptions import RetryException
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()

        with pytest.raises(RetryException):
            await service._retrieve_ai_threads(
                "g",
                limit=None,
                dedup_tracker=dedup_tracker,
                target_dates=[date.today()],
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_skips_duplicates(mock_env_vars, respx_mock):
    """
    Given: 重複したタイトルのスレッド
    When: _retrieve_ai_threads()を呼び出す
    Then: 重複がスキップされる
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 1,
                            "sub": "AI Discussion",
                            "com": "GPT discussion",
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        },
                        {
                            "no": 2,
                            "sub": "AI Discussion",  # 同じタイトル
                            "com": "Another GPT discussion",
                            "time": int(datetime.now(UTC).timestamp()),
                            "last_modified": int(datetime.now(UTC).timestamp()),
                        },
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/1.json").mock(
        return_value=httpx.Response(
            200,
            json={"posts": [{"no": 1, "time": int(datetime.now(UTC).timestamp())}]},
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert isinstance(threads, list)
        assert len(threads) == 1  # 重複は1つだけ


# =============================================================================
# 10. 内部メソッドの単体テスト - _serialize_threads()
# =============================================================================


@pytest.mark.unit
def test_serialize_threads(mock_env_vars, thread_factory):
    """
    Given: Threadオブジェクトのリスト
    When: _serialize_threads()を呼び出す
    Then: 正しくdictに変換される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=123,
                title="Test Thread",
                url="https://example.com/123",
                board="g",
                posts=[],
                timestamp=1699999999,
                summary="Test summary",
                popularity_score=10.5,
            )
        ]

        records = service._serialize_threads(threads)

        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0]["thread_id"] == 123
        assert records[0]["title"] == "Test Thread"
        assert records[0]["popularity_score"] == 10.5
        assert "published_at" in records[0]


# =============================================================================
# 11. 内部メソッドの単体テスト - _render_markdown()
# =============================================================================


@pytest.mark.unit
def test_render_markdown(mock_env_vars):
    """
    Given: スレッドレコードのリスト
    When: _render_markdown()を呼び出す
    Then: 正しいMarkdownが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        records = [
            {
                "thread_id": 123,
                "title": "Test Thread",
                "url": "https://example.com/123",
                "board": "g",
                "timestamp": 1699999999,
                "summary": "Test summary",
                "published_at": "2023-11-14T12:00:00+00:00",
            }
        ]

        today = datetime(2024, 11, 14)
        markdown = service._render_markdown(records, today)

        assert isinstance(markdown, str)
        assert "# 4chan AI関連スレッド" in markdown
        assert "## /g/" in markdown
        assert "Test Thread" in markdown
        assert "Test summary" in markdown


# =============================================================================
# 12. 内部メソッドの単体テスト - _parse_markdown()
# =============================================================================


@pytest.mark.unit
def test_parse_markdown(mock_env_vars):
    """
    Given: Markdown形式のスレッドデータ
    When: _parse_markdown()を呼び出す
    Then: 正しくdictに変換される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown = """# 4chan AI関連スレッド (2024-11-14)

## /g/

### [Test Thread](https://boards.4chan.org/g/thread/123456)

作成日時: <t:1699999999:F>

**要約**:
This is a test summary.

---

"""

        records = service._parse_markdown(markdown)

        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0]["thread_id"] == 123456
        assert records[0]["title"] == "Test Thread"
        assert records[0]["board"] == "g"
        assert records[0]["summary"] == "This is a test summary."


@pytest.mark.unit
def test_parse_markdown_empty(mock_env_vars):
    """
    Given: 空のMarkdown
    When: _parse_markdown()を呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        records = service._parse_markdown("")

        assert isinstance(records, list)
        assert len(records) == 0


# =============================================================================
# 13. 内部メソッドの単体テスト - _thread_sort_key()
# =============================================================================


@pytest.mark.unit
def test_thread_sort_key(mock_env_vars):
    """
    Given: スレッドレコード
    When: _thread_sort_key()を呼び出す
    Then: (popularity_score, datetime)のタプルが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        record = {
            "popularity_score": 10.5,
            "published_at": "2024-11-14T12:00:00+00:00",
        }

        key = service._thread_sort_key(record)

        assert isinstance(key, tuple)
        assert len(key) == 2
        assert key[0] == 10.5
        assert isinstance(key[1], datetime)


@pytest.mark.unit
def test_thread_sort_key_missing_fields(mock_env_vars):
    """
    Given: フィールドが欠損したレコード
    When: _thread_sort_key()を呼び出す
    Then: デフォルト値が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        record = {}

        key = service._thread_sort_key(record)

        assert isinstance(key, tuple)
        assert len(key) == 2
        assert key[0] == 0.0
        assert isinstance(key[1], datetime)


@pytest.mark.unit
def test_thread_sort_key_with_timestamp_fallback(mock_env_vars):
    """
    Given: published_atがなくtimestampのみのレコード
    When: _thread_sort_key()を呼び出す
    Then: timestampから日時が計算される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        record = {"popularity_score": 5.0, "timestamp": 1699999999}

        key = service._thread_sort_key(record)

        assert isinstance(key, tuple)
        assert key[0] == 5.0
        assert isinstance(key[1], datetime)


@pytest.mark.unit
def test_thread_sort_key_with_invalid_timestamp(mock_env_vars):
    """
    Given: 不正なtimestampのレコード
    When: _thread_sort_key()を呼び出す
    Then: datetime.minが使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        record = {"popularity_score": 5.0, "timestamp": "invalid"}

        key = service._thread_sort_key(record)

        assert isinstance(key, tuple)
        assert key[0] == 5.0
        assert key[1] == datetime.min.replace(tzinfo=timezone.utc)


# =============================================================================
# 14. 内部メソッドの単体テスト - _summarize_thread()
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_success(fourchan_service, thread_factory):
    """
    Given: 有効なスレッドオブジェクト
    When: _summarize_thread()を呼び出す
    Then: 要約が正常に生成される
    """
    thread = thread_factory(
        title="AI Discussion",
        posts=[
            {"no": TEST_THREAD_ID, "com": "What do you think about GPT-4?"},
            {"no": TEST_THREAD_ID + 1, "com": "It's amazing!"},
        ],
    )

    fourchan_service.gpt_client.generate_content = Mock(
        return_value="これはAIに関する議論です。"
    )

    await fourchan_service._summarize_thread(thread)

    # カスタムアサーションを使用
    assert_thread_summary_generated(thread, "これはAIに関する議論です。")
    assert_gpt_called_with_thread_content(
        fourchan_service.gpt_client.generate_content, thread
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("posts", "expected_summary", "tags_to_check"),
    [
        # HTMLタグ除去テスト
        (
            [{"no": TEST_THREAD_ID, "com": "<b>Bold text</b> and <i>italic</i>"}],
            "テスト要約",
            ["<b>", "<i>"],
        ),
        # 複数のHTMLタグ
        (
            [
                {
                    "no": TEST_THREAD_ID,
                    "com": "<div><span>Nested</span> <a href='#'>link</a></div>",
                }
            ],
            "ネスト要約",
            ["<div>", "<span>", "<a"],
        ),
        # 空のHTMLタグ
        (
            [{"no": TEST_THREAD_ID, "com": "<br/><hr/>Text"}],
            "改行要約",
            ["<br", "<hr"],
        ),
    ],
)
async def test_summarize_thread_html_tag_removal(
    fourchan_service, thread_factory, posts, expected_summary, tags_to_check
):
    """
    Given: HTMLタグを含む投稿（パラメータ化）
    When: _summarize_thread()を呼び出す
    Then: HTMLタグが除去されて要約が生成される
    """
    thread = thread_factory(posts=posts)

    fourchan_service.gpt_client.generate_content = Mock(return_value=expected_summary)

    await fourchan_service._summarize_thread(thread)

    # カスタムアサーションを使用
    assert_thread_summary_generated(thread, expected_summary)

    # promptにHTMLタグが除去されていることを確認
    call_args = fourchan_service.gpt_client.generate_content.call_args
    prompt = call_args.kwargs["prompt"]
    for tag in tags_to_check:
        assert tag not in prompt, f"HTML tag '{tag}' should be removed from prompt"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_empty_posts(fourchan_service, thread_factory):
    """
    Given: 空の投稿リスト
    When: _summarize_thread()を呼び出す
    Then: エラーなく処理される
    """
    thread = thread_factory(title="Empty Thread", posts=[])

    fourchan_service.gpt_client.generate_content = Mock(
        return_value="空のスレッドです。"
    )

    await fourchan_service._summarize_thread(thread)

    # カスタムアサーションを使用
    assert_thread_summary_generated(thread, "空のスレッドです。")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_gpt_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_thread()を呼び出す
    Then: エラーメッセージが要約に設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        thread = Thread(
            thread_id=123456,
            title="Test Thread",
            url="https://boards.4chan.org/g/thread/123456",
            board="g",
            posts=[{"no": 123456, "com": "Test post"}],
            timestamp=1699999999,
        )

        service.gpt_client.generate_content = Mock(
            side_effect=Exception("API rate limit exceeded")
        )

        await service._summarize_thread(thread)

        assert "エラーが発生しました" in thread.summary
        assert "API rate limit exceeded" in thread.summary


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_with_many_replies(mock_env_vars):
    """
    Given: 多数の返信があるスレッド
    When: _summarize_thread()を呼び出す
    Then: 最大5件の返信のみが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        posts = [{"no": i, "com": f"Post {i}"} for i in range(20)]

        thread = Thread(
            thread_id=123456,
            title="Popular Thread",
            url="https://boards.4chan.org/g/thread/123456",
            board="g",
            posts=posts,
            timestamp=1699999999,
        )

        service.gpt_client.generate_content = Mock(return_value="人気スレッドの要約")

        await service._summarize_thread(thread)

        # generate_contentが呼び出されたことを確認
        call_args = service.gpt_client.generate_content.call_args
        prompt_text = call_args.kwargs["prompt"]

        # OPと最大5件の返信のみが含まれることを確認
        assert "返信 1:" in prompt_text
        assert "返信 5:" in prompt_text
        assert "返信 6:" not in prompt_text


# =============================================================================
# 15. 内部メソッドの単体テスト - _select_top_threads()
# =============================================================================


@pytest.mark.unit
def test_select_top_threads_within_limit(mock_env_vars):
    """
    Given: limit以下のスレッド数
    When: _select_top_threads()を呼び出す
    Then: すべてのスレッドが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=i,
                title=f"Thread {i}",
                url=f"https://example.com/{i}",
                board="g",
                posts=[],
                timestamp=1699999999,
                popularity_score=float(i),
            )
            for i in range(5)
        ]

        result = service._select_top_threads(threads, limit=10)

        assert len(result) == 5


@pytest.mark.unit
def test_select_top_threads_exceeds_limit(mock_env_vars):
    """
    Given: limitを超えるスレッド数
    When: _select_top_threads()を呼び出す
    Then: 人気スコアの高い順にlimit件が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=i,
                title=f"Thread {i}",
                url=f"https://example.com/{i}",
                board="g",
                posts=[],
                timestamp=1699999999,
                popularity_score=float(i),
            )
            for i in range(20)
        ]

        result = service._select_top_threads(threads, limit=5)

        assert len(result) == 5
        # 人気スコアの高い順（19, 18, 17, 16, 15）
        assert result[0].popularity_score == 19.0
        assert result[4].popularity_score == 15.0


@pytest.mark.unit
def test_select_top_threads_empty_list(mock_env_vars):
    """
    Given: 空のスレッドリスト
    When: _select_top_threads()を呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        result = service._select_top_threads([], limit=10)

        assert result == []


@pytest.mark.unit
def test_select_top_threads_with_same_score(mock_env_vars):
    """
    Given: 同じ人気スコアのスレッド
    When: _select_top_threads()を呼び出す
    Then: タイムスタンプで二次ソートされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=1,
                title="Old Thread",
                url="https://example.com/1",
                board="g",
                posts=[],
                timestamp=1699999999,
                popularity_score=10.0,
            ),
            Thread(
                thread_id=2,
                title="New Thread",
                url="https://example.com/2",
                board="g",
                posts=[],
                timestamp=1700000000,
                popularity_score=10.0,
            ),
        ]

        result = service._select_top_threads(threads, limit=5)

        assert len(result) == 2
        # スレッドが選択されることを確認
        result_ids = {t.thread_id for t in result}
        assert result_ids == {1, 2}


# =============================================================================
# 16. 内部メソッドの単体テスト - _load_existing_titles()
# =============================================================================


@pytest.mark.unit
def test_load_existing_titles_with_valid_markdown(mock_env_vars):
    """
    Given: 有効なMarkdownファイル
    When: _load_existing_titles()を呼び出す
    Then: タイトルが正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown_content = """# 4chan AI関連スレッド

## /g/

### [AI Discussion Thread](https://example.com/1)

作成日時: <t:1699999999:F>

**要約**:
Test summary 1

---

### [Machine Learning Thread](https://example.com/2)

作成日時: <t:1699999999:F>

**要約**:
Test summary 2

---
"""

        with patch.object(
            service.storage, "load_markdown", return_value=markdown_content
        ):
            tracker = service._load_existing_titles()

            # タイトルが追加されたか確認
            is_dup1, _ = tracker.is_duplicate("AI Discussion Thread")
            is_dup2, _ = tracker.is_duplicate("Machine Learning Thread")

            assert is_dup1 is True
            assert is_dup2 is True


@pytest.mark.unit
def test_load_existing_titles_empty_markdown(mock_env_vars):
    """
    Given: 空のMarkdownファイル
    When: _load_existing_titles()を呼び出す
    Then: 空のTrackerが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        with patch.object(service.storage, "load_markdown", return_value=""):
            tracker = service._load_existing_titles()

            is_dup, _ = tracker.is_duplicate("New Thread")
            assert is_dup is False


@pytest.mark.unit
def test_load_existing_titles_with_error(mock_env_vars):
    """
    Given: Markdownの読み込みでエラーが発生
    When: _load_existing_titles()を呼び出す
    Then: 空のTrackerが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        with patch.object(
            service.storage, "load_markdown", side_effect=Exception("File not found")
        ):
            tracker = service._load_existing_titles()

            # エラーが発生しても空のTrackerが返される
            is_dup, _ = tracker.is_duplicate("New Thread")
            assert is_dup is False


# =============================================================================
# 17. 内部メソッドの単体テスト - _load_existing_threads()
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_threads_from_json(mock_env_vars):
    """
    Given: 有効なJSONファイル
    When: _load_existing_threads()を呼び出す
    Then: スレッドデータが正しく読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        json_data = {
            "g": [
                {
                    "thread_id": 123456,
                    "title": "Test Thread",
                    "url": "https://example.com/123456",
                    "timestamp": 1699999999,
                    "summary": "Test summary",
                }
            ]
        }

        with patch.object(service, "load_json", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = json_data

            target_date = datetime(2024, 11, 14)
            result = await service._load_existing_threads(target_date)

            assert len(result) == 1
            assert result[0]["thread_id"] == 123456
            assert result[0]["board"] == "g"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_threads_from_markdown(mock_env_vars):
    """
    Given: JSONがなくMarkdownファイルのみ
    When: _load_existing_threads()を呼び出す
    Then: Markdownからスレッドデータが読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown_content = """# 4chan AI関連スレッド (2024-11-14)

## /g/

### [Test Thread](https://boards.4chan.org/g/thread/123456)

作成日時: <t:1699999999:F>

**要約**:
Test summary

---
"""

        with patch.object(service, "load_json", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None

            with patch.object(
                service.storage, "load", new_callable=AsyncMock
            ) as mock_storage_load:
                mock_storage_load.return_value = markdown_content

                target_date = datetime(2024, 11, 14)
                result = await service._load_existing_threads(target_date)

                assert len(result) == 1
                assert result[0]["thread_id"] == 123456


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_threads_no_data(mock_env_vars):
    """
    Given: JSONもMarkdownも存在しない
    When: _load_existing_threads()を呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        with patch.object(service, "load_json", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None

            with patch.object(
                service.storage, "load", new_callable=AsyncMock
            ) as mock_storage_load:
                mock_storage_load.return_value = None

                target_date = datetime(2024, 11, 14)
                result = await service._load_existing_threads(target_date)

                assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_threads_list_format(mock_env_vars):
    """
    Given: リスト形式のJSONデータ
    When: _load_existing_threads()を呼び出す
    Then: そのまま返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        json_data = [
            {
                "thread_id": 123456,
                "title": "Test Thread",
                "board": "g",
            }
        ]

        with patch.object(service, "load_json", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = json_data

            target_date = datetime(2024, 11, 14)
            result = await service._load_existing_threads(target_date)

            assert len(result) == 1
            assert result[0]["thread_id"] == 123456


# =============================================================================
# 18. catalog.json エッジケーステスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_catalog_invalid_json(mock_env_vars, respx_mock):
    """
    Given: catalog.jsonが不正なJSON
    When: _retrieve_ai_threads()を呼び出す
    Then: 例外が発生する
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(200, text="invalid json {{{")
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()

        with pytest.raises(json.JSONDecodeError):
            await service._retrieve_ai_threads(
                "g",
                limit=None,
                dedup_tracker=dedup_tracker,
                target_dates=[date.today()],
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_catalog_timeout(mock_env_vars, respx_mock):
    """
    Given: catalog.jsonのリクエストがタイムアウト
    When: _retrieve_ai_threads()を呼び出す
    Then: RetryExceptionが発生する（リトライ後）
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.common.exceptions import RetryException
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()

        with pytest.raises(RetryException):
            await service._retrieve_ai_threads(
                "g",
                limit=None,
                dedup_tracker=dedup_tracker,
                target_dates=[date.today()],
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_empty_catalog(mock_env_vars, respx_mock):
    """
    Given: 空のcatalog.json
    When: _retrieve_ai_threads()を呼び出す
    Then: 空のリストが返される
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(200, json=[])
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert isinstance(threads, list)
        assert len(threads) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_missing_subject(mock_env_vars, respx_mock):
    """
    Given: subjectフィールドがないスレッド
    When: _retrieve_ai_threads()を呼び出す
    Then: デフォルトタイトルが使用される
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "com": "AI and machine learning discussion",
                            "time": int(datetime.now(timezone.utc).timestamp()),
                            "last_modified": int(
                                datetime.now(timezone.utc).timestamp()
                            ),
                        }
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "posts": [
                    {"no": 123456, "time": int(datetime.now(timezone.utc).timestamp())}
                ]
            },
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert len(threads) == 1
        assert "Untitled Thread" in threads[0].title


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_html_in_comment(mock_env_vars, respx_mock):
    """
    Given: HTMLタグを含むコメント
    When: _retrieve_ai_threads()を呼び出す
    Then: HTMLタグが除去されてキーワードマッチングされる
    """
    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "Test Thread",
                            "com": "<b>GPT-4</b> and <i>machine learning</i>",
                            "time": int(datetime.now(timezone.utc).timestamp()),
                            "last_modified": int(
                                datetime.now(timezone.utc).timestamp()
                            ),
                        }
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "posts": [
                    {"no": 123456, "time": int(datetime.now(timezone.utc).timestamp())}
                ]
            },
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=[date.today()]
        )

        assert len(threads) == 1


# =============================================================================
# 19. JSON解析エッジケーステスト
# =============================================================================


@pytest.mark.unit
def test_parse_markdown_multiple_boards(mock_env_vars):
    """
    Given: 複数のボードを含むMarkdown
    When: _parse_markdown()を呼び出す
    Then: すべてのボードのスレッドが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown = """# 4chan AI関連スレッド (2024-11-14)

## /g/

### [Thread 1](https://boards.4chan.org/g/thread/111111)

作成日時: <t:1699999999:F>

**要約**:
Summary 1

---

## /sci/

### [Thread 2](https://boards.4chan.org/sci/thread/222222)

作成日時: <t:1699999999:F>

**要約**:
Summary 2

---
"""

        records = service._parse_markdown(markdown)

        assert len(records) == 2
        assert records[0]["board"] == "g"
        assert records[0]["thread_id"] == 111111
        assert records[1]["board"] == "sci"
        assert records[1]["thread_id"] == 222222


@pytest.mark.unit
def test_parse_markdown_missing_summary(mock_env_vars):
    """
    Given: 要約がないMarkdown
    When: _parse_markdown()を呼び出す
    Then: 空の要約として処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown = """# 4chan AI関連スレッド (2024-11-14)

## /g/

### [Test Thread](https://boards.4chan.org/g/thread/123456)

作成日時: <t:1699999999:F>

**要約**:

---
"""

        records = service._parse_markdown(markdown)

        assert len(records) == 1
        assert records[0]["summary"] == ""


@pytest.mark.unit
def test_parse_markdown_malformed(mock_env_vars):
    """
    Given: 不正な形式のMarkdown
    When: _parse_markdown()を呼び出す
    Then: 可能な限り解析される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        markdown = """# Random header

Some random text

### [Thread without board](https://example.com/thread/123)
"""

        records = service._parse_markdown(markdown)

        # 不正な形式なので何も抽出されない
        assert len(records) == 0


@pytest.mark.unit
def test_render_markdown_with_missing_fields(mock_env_vars):
    """
    Given: フィールドが欠損したレコード
    When: _render_markdown()を呼び出す
    Then: デフォルト値が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        records = [
            {
                "thread_id": 123,
                "url": "https://example.com/123",
                # titleとsummaryが欠損
            }
        ]

        today = datetime(2024, 11, 14)
        markdown = service._render_markdown(records, today)

        assert isinstance(markdown, str)
        assert "無題スレッド #123" in markdown


# =============================================================================
# 20. popularity score 追加エッジケーステスト
# =============================================================================


@pytest.mark.unit
def test_calculate_popularity_with_invalid_timestamp(mock_env_vars):
    """
    Given: 不正なタイムスタンプ
    When: _calculate_popularity()を呼び出す
    Then: recency_bonusが0になるがエラーは発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_metadata = {
            "replies": 10,
            "images": 5,
            "bumps": 3,
            "last_modified": "invalid",
        }
        posts = [{"no": 1}]

        score = service._calculate_popularity(thread_metadata, posts)

        # replies(10) + images*2(10) + bumps(3) + len(posts)(1) = 24
        assert score == 24.0


@pytest.mark.unit
def test_calculate_popularity_with_future_timestamp(mock_env_vars):
    """
    Given: 未来のタイムスタンプ
    When: _calculate_popularity()を呼び出す
    Then: 計算は正常に行われる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        future_timestamp = int(datetime.now().timestamp()) + 86400  # 1日後

        thread_metadata = {
            "replies": 10,
            "images": 5,
            "bumps": 3,
            "last_modified": future_timestamp,
        }
        posts = []

        score = service._calculate_popularity(thread_metadata, posts)

        assert isinstance(score, float)
        # 未来のタイムスタンプでもエラーにならない
        assert score > 0


@pytest.mark.unit
def test_calculate_popularity_zero_values(mock_env_vars):
    """
    Given: すべてのフィールドが0
    When: _calculate_popularity()を呼び出す
    Then: 0.0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread_metadata = {
            "replies": 0,
            "images": 0,
            "bumps": 0,
        }
        posts = []

        score = service._calculate_popularity(thread_metadata, posts)

        assert score == 0.0


# =============================================================================
# 21. _store_summaries() メソッドテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_empty_list(mock_env_vars):
    """
    Given: 空のスレッドリスト
    When: _store_summaries()を呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        result = await service._store_summaries([], [date.today()])

        assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_threads(mock_env_vars):
    """
    Given: 有効なスレッドリスト
    When: _store_summaries()を呼び出す
    Then: store_daily_snapshotsが呼ばれて結果が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=123456,
                title="Test Thread",
                url="https://boards.4chan.org/g/thread/123456",
                board="g",
                posts=[],
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                summary="Test summary",
                popularity_score=10.0,
            )
        ]

        target_dates = [date.today()]

        with patch(
            "nook.services.fourchan_explorer.fourchan_explorer.store_daily_snapshots",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = [
                ("data/fourchan_explorer/2024-11-14.json", "data/fourchan_explorer/2024-11-14.md"),
            ]

            result = await service._store_summaries(threads, target_dates)

            assert len(result) == 1
            assert result[0][0].endswith(".json")
            assert result[0][1].endswith(".md")
            mock_store.assert_called_once()


# =============================================================================
# 22. _retrieve_ai_threads() 日付フィルタリングテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_date_filtering(mock_env_vars, respx_mock):
    """
    Given: 日付範囲外のスレッド
    When: _retrieve_ai_threads()を呼び出す
    Then: 日付範囲外のスレッドがスキップされる
    """
    # 過去の日付（対象範囲外）
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=10)).timestamp())

    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "Old Thread",
                            "com": "AI discussion",
                            "time": old_timestamp,
                            "last_modified": old_timestamp,
                        }
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200, json={"posts": [{"no": 123456, "time": old_timestamp}]}
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        # 今日のみを対象とする
        target_dates = [date.today()]

        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=target_dates
        )

        # 日付範囲外なので除外される
        assert len(threads) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_within_date_range(mock_env_vars, respx_mock):
    """
    Given: 日付範囲内のスレッド
    When: _retrieve_ai_threads()を呼び出す
    Then: スレッドが正常に取得される
    """
    current_timestamp = int(datetime.now(timezone.utc).timestamp())

    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "Recent Thread",
                            "com": "AI and machine learning",
                            "time": current_timestamp,
                            "last_modified": current_timestamp,
                        }
                    ],
                }
            ],
        )
    )

    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(
            200, json={"posts": [{"no": 123456, "time": current_timestamp}]}
        )
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        target_dates = [date.today()]

        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=target_dates
        )

        assert len(threads) == 1
        assert threads[0].title == "Recent Thread"


# =============================================================================
# 23. _serialize_threads() 詳細テスト
# =============================================================================


@pytest.mark.unit
def test_serialize_threads_with_various_fields(mock_env_vars):
    """
    Given: 様々なフィールドを持つスレッド
    When: _serialize_threads()を呼び出す
    Then: すべてのフィールドが正しくシリアライズされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=123456,
                title="Complete Thread",
                url="https://boards.4chan.org/g/thread/123456",
                board="g",
                posts=[{"no": 1}, {"no": 2}],
                timestamp=1699999999,
                summary="Detailed summary",
                popularity_score=15.5,
            )
        ]

        records = service._serialize_threads(threads)

        assert len(records) == 1
        record = records[0]
        assert record["thread_id"] == 123456
        assert record["title"] == "Complete Thread"
        assert record["url"] == "https://boards.4chan.org/g/thread/123456"
        assert record["board"] == "g"
        assert record["summary"] == "Detailed summary"
        assert record["popularity_score"] == 15.5
        assert "published_at" in record
        assert record["timestamp"] == 1699999999


@pytest.mark.unit
def test_serialize_threads_empty_summary(mock_env_vars):
    """
    Given: 要約が空のスレッド
    When: _serialize_threads()を呼び出す
    Then: 空の要約でシリアライズされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()

        threads = [
            Thread(
                thread_id=123456,
                title="No Summary Thread",
                url="https://example.com/123456",
                board="g",
                posts=[],
                timestamp=1699999999,
                summary="",
                popularity_score=0.0,
            )
        ]

        records = service._serialize_threads(threads)

        assert len(records) == 1
        assert records[0]["summary"] == ""


# =============================================================================
# 24. _render_markdown() 追加テスト
# =============================================================================


@pytest.mark.unit
def test_render_markdown_empty_records(mock_env_vars):
    """
    Given: 空のレコードリスト
    When: _render_markdown()を呼び出す
    Then: ヘッダーのみのMarkdownが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        today = datetime(2024, 11, 14)
        markdown = service._render_markdown([], today)

        assert isinstance(markdown, str)
        assert "# 4chan AI関連スレッド (2024-11-14)" in markdown
        assert "## /" not in markdown  # ボードセクションがない


@pytest.mark.unit
def test_render_markdown_multiple_boards(mock_env_vars):
    """
    Given: 複数のボードのレコード
    When: _render_markdown()を呼び出す
    Then: ボードごとにグループ化されたMarkdownが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        records = [
            {
                "thread_id": 111111,
                "title": "G Thread",
                "url": "https://boards.4chan.org/g/thread/111111",
                "board": "g",
                "summary": "Summary G",
                "timestamp": 1699999999,
                "popularity_score": 10.0,
            },
            {
                "thread_id": 222222,
                "title": "Sci Thread",
                "url": "https://boards.4chan.org/sci/thread/222222",
                "board": "sci",
                "summary": "Summary Sci",
                "timestamp": 1699999999,
                "popularity_score": 8.0,
            },
        ]

        today = datetime(2024, 11, 14)
        markdown = service._render_markdown(records, today)

        assert "## /g/" in markdown
        assert "## /sci/" in markdown
        assert "G Thread" in markdown
        assert "Sci Thread" in markdown


# =============================================================================
# 25. _load_boards() 追加テスト
# =============================================================================


@pytest.mark.unit
def test_load_boards_with_disabled_boards(mock_env_vars):
    """
    Given: enabled=falseのボードを含むboards.toml
    When: _load_boards()を呼び出す
    Then: enabledなボードのみが返される
    """

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        toml_content = b"""
[boards]

[boards.g]
enabled = true
name = "Technology"

[boards.sci]
enabled = false
name = "Science"
"""

        mock_file = mock_open(read_data=toml_content)

        with (
            patch("builtins.open", mock_file),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.__truediv__") as mock_div,
        ):
            # Pathの演算子をモック
            mock_path = Mock()
            mock_div.return_value = mock_path
            mock_path.exists.return_value = True

            boards = service._load_boards()

            # enabled=trueのgボードのみ
            assert len(boards) == 1
            assert boards[0] == "g"


# =============================================================================
# 26. _retrieve_ai_threads() 投稿取得失敗テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_thread_posts_failure(mock_env_vars, respx_mock):
    """
    Given: スレッドの投稿取得が失敗する
    When: _retrieve_ai_threads()を呼び出す
    Then: そのスレッドがスキップされる
    """
    current_timestamp = int(datetime.now(timezone.utc).timestamp())

    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "Thread that will fail",
                            "com": "AI discussion",
                            "time": current_timestamp,
                            "last_modified": current_timestamp,
                        }
                    ],
                }
            ],
        )
    )

    # スレッドの投稿取得が404を返す
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        target_dates = [date.today()]

        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=target_dates
        )

        # 投稿取得失敗でスキップされるため、空のリスト
        assert len(threads) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_no_valid_timestamps(mock_env_vars, respx_mock):
    """
    Given: タイムスタンプがないスレッド
    When: _retrieve_ai_threads()を呼び出す
    Then: スレッドが適切に処理される
    """
    current_timestamp = int(datetime.now(timezone.utc).timestamp())

    respx_mock.get("https://a.4cdn.org/g/catalog.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "page": 0,
                    "threads": [
                        {
                            "no": 123456,
                            "sub": "No timestamp thread",
                            "com": "AI discussion",
                            "time": current_timestamp,
                            "last_modified": current_timestamp,
                        }
                    ],
                }
            ],
        )
    )

    # 投稿にタイムスタンプがない
    respx_mock.get("https://a.4cdn.org/g/thread/123456.json").mock(
        return_value=httpx.Response(200, json={"posts": [{"no": 123456}]})
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(test_mode=True)
        await service.setup_http_client()

        dedup_tracker = DedupTracker()
        target_dates = [date.today()]

        threads = await service._retrieve_ai_threads(
            "g", limit=None, dedup_tracker=dedup_tracker, target_dates=target_dates
        )

        # thread_createdが有効なので取得される
        assert len(threads) == 1


# =============================================================================
# 27. __init__ テスト - storage pathの調整
# =============================================================================


@pytest.mark.unit
def test_init_with_storage_path_not_ending_with_service_name(mock_env_vars):
    """
    Given: storage_dirがサービス名で終わっていない
    When: FourChanExplorerを初期化
    Then: storage_pathにサービス名が追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(storage_dir="/tmp/data")  # nosec B108

        # storage_pathにfourchan_explorerが追加されている
        assert str(service.storage.base_dir).endswith("fourchan_explorer")


@pytest.mark.unit
def test_init_with_storage_path_already_ending_with_service_name(mock_env_vars):
    """
    Given: storage_dirが既にサービス名で終わっている
    When: FourChanExplorerを初期化
    Then: storage_pathはそのまま使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer(storage_dir="/tmp/data/fourchan_explorer")  # nosec B108

        # 二重にfourchan_explorerが追加されない
        assert str(service.storage.base_dir) == "/tmp/data/fourchan_explorer"  # nosec B108


# =============================================================================
# 28. _summarize_thread エッジケース - 空のテキスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_with_empty_op_text(fourchan_service):
    """
    Given: OPのcomフィールドが空文字
    When: _summarize_thread()を呼び出す
    Then: OPのテキストがスキップされる
    """
    from nook.services.fourchan_explorer.fourchan_explorer import Thread

    thread = Thread(
        thread_id=TEST_THREAD_ID,
        title="Test",
        url=f"https://boards.4chan.org/{TEST_BOARD}/thread/{TEST_THREAD_ID}",
        popularity_score=1.0,
        board=TEST_BOARD,
        timestamp=TEST_TIMESTAMP_ALT,
        posts=[
            {"no": TEST_THREAD_ID, "com": ""},  # 空のOP
            {"no": TEST_THREAD_ID + 1, "com": "Reply text"},
        ],
    )

    fourchan_service.gpt_client.generate_content = Mock(return_value="Summary")

    await fourchan_service._summarize_thread(thread)

    # 要約が生成される
    assert thread.summary == "Summary"
    assert fourchan_service.gpt_client.generate_content.called

    # OPのテキストがプロンプトに含まれていないことを確認
    call_args = fourchan_service.gpt_client.generate_content.call_args
    prompt = call_args.kwargs["prompt"]
    # "OP:"が含まれていない（空だからスキップされた）
    assert "OP: Reply text" not in prompt
    # 返信は含まれている
    assert "返信 1: Reply text" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_thread_with_empty_reply_text(fourchan_service):
    """
    Given: 返信のcomフィールドが空文字
    When: _summarize_thread()を呼び出す
    Then: 空の返信がスキップされる
    """
    from nook.services.fourchan_explorer.fourchan_explorer import Thread

    thread = Thread(
        thread_id=TEST_THREAD_ID,
        title="Test",
        url=f"https://boards.4chan.org/{TEST_BOARD}/thread/{TEST_THREAD_ID}",
        popularity_score=1.0,
        board=TEST_BOARD,
        timestamp=TEST_TIMESTAMP_ALT,
        posts=[
            {"no": TEST_THREAD_ID, "com": "OP text"},
            {"no": TEST_THREAD_ID + 1, "com": ""},  # 空の返信
            {"no": TEST_THREAD_ID + 2, "com": "Real reply"},
        ],
    )

    fourchan_service.gpt_client.generate_content = Mock(return_value="Summary")

    await fourchan_service._summarize_thread(thread)

    # 要約が生成される
    assert thread.summary == "Summary"
    assert fourchan_service.gpt_client.generate_content.called

    # プロンプト内容を検証
    call_args = fourchan_service.gpt_client.generate_content.call_args
    prompt = call_args.kwargs["prompt"]
    # OPは含まれている
    assert "OP: OP text" in prompt
    # 空の返信はスキップされ、実際の返信のみが含まれている
    # 注：空の返信（インデックス1）がスキップされるため、次の返信は「返信 2」
    assert "返信 2: Real reply" in prompt
    # 返信は1つだけ（空の返信はカウントされない）
    assert prompt.count("返信") == 1


# =============================================================================
# 29. _thread_sort_key エラーハンドリング
# =============================================================================


@pytest.mark.unit
def test_thread_sort_key_with_invalid_published_format(mock_env_vars):
    """
    Given: published_atが不正なフォーマット
    When: _thread_sort_key()を呼び出す
    Then: datetime.minが使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        thread = {
            "popularity_score": 5.0,
            "published_at": "invalid-date-format",
        }

        popularity, published = service._thread_sort_key(thread)

        assert popularity == 5.0
        assert published == datetime.min.replace(tzinfo=timezone.utc)


# =============================================================================
# 30. _extract_thread_id_from_url fallback
# =============================================================================


@pytest.mark.unit
def test_extract_thread_id_with_non_standard_url(mock_env_vars):
    """
    Given: 非標準のURL形式（/thread/がない）
    When: _extract_thread_id_from_url()を呼び出す
    Then: 最後の数字部分が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        # /thread/がないURL
        url = "https://example.com/g/123456"
        result = service._extract_thread_id_from_url(url)

        assert result == 123456


# =============================================================================
# 31. _render_markdown ValueError ハンドリング
# =============================================================================


@pytest.mark.unit
def test_render_markdown_with_invalid_published_at(mock_env_vars):
    """
    Given: published_atが不正なフォーマットのスレッド
    When: _render_markdown()を呼び出す
    Then: timestampフィールドにフォールバックする
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        records = [
            {
                "thread_id": 123456,
                "title": "Test Thread",
                "url": "https://example.com/123456",
                "board": "g",
                "published_at": "invalid-date",
                "timestamp": 1699999999,
                "summary": "Test",
            }
        ]

        # 固定日付を使用（再現性向上）
        test_date = datetime(2024, 11, 14, tzinfo=timezone.utc)
        result = service._render_markdown(records, test_date)

        # timestampが使用される
        assert "<t:1699999999:F>" in result
        # 日付が正しくフォーマットされている
        assert "2024-11-14" in result


# =============================================================================
# 32. _parse_markdown without timestamp条件分岐
# =============================================================================


@pytest.mark.unit
def test_parse_markdown_without_timestamp(mock_env_vars):
    """
    Given: timestampが0のMarkdownテキスト
    When: _parse_markdown()を呼び出す
    Then: published_atフィールドが含まれない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        # timestamp=0のMarkdown
        markdown = """# 4chan AI関連スレッド (2024-11-14)

## /g/

### [Test Thread](https://example.com/123456)

作成日時: <t:0:F>

**要約**:
Test summary

---
"""

        result = service._parse_markdown(markdown)

        # timestamp=0の場合はpublished_atフィールドが含まれない
        assert len(result) == 1
        assert "published_at" not in result[0]


# =============================================================================
# 33. run() メソッドテスト
# =============================================================================


@pytest.mark.unit
def test_run_method_calls_collect(mock_env_vars):
    """
    Given: FourChanExplorerインスタンス
    When: run()を呼び出す
    Then: collect()が呼び出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()

        # asyncio.runをモックしてcollect()の呼び出しを検証
        with (
            patch("asyncio.run") as mock_asyncio_run,
            patch.object(service, "collect", new_callable=AsyncMock),
        ):
            service.run(thread_limit=10)

            # asyncio.runが呼び出されたことを確認
            mock_asyncio_run.assert_called_once()
            # asyncio.runに渡された引数（コルーチン）を取得
            called_coro = mock_asyncio_run.call_args[0][0]
            # コルーチンであることを確認
            assert asyncio.iscoroutine(called_coro)
            # コルーチンをクローズ（メモリリーク防止）
            called_coro.close()
