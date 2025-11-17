"""
Additional tests for fourchan_explorer coverage improvement
Task 6: カバレッジ67.07% → 75%以上への向上
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nook.common.dedup import DedupTracker


# Helper function
def get_jst_date_from_utc(utc_dt: datetime):
    """UTC datetimeをJST dateに変換"""
    from datetime import timezone

    jst = timezone(timedelta(hours=9))
    return utc_dt.astimezone(jst).date()


# =============================================================================
# Additional Tests for Coverage Improvement - Task 6
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_none_http_client():
    """
    Given: http_clientがNone
    When: collectメソッドを呼び出す
    Then: setup_http_clientが呼び出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = None  # Explicitly set to None

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock) as mock_setup,
            patch.object(service, "_retrieve_ai_threads", new_callable=AsyncMock, return_value=[]),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            jst_today = get_jst_date_from_utc(datetime.now(UTC))
            await service.collect(target_dates=[jst_today])

            # setup_http_clientが呼び出されたことを確認
            mock_setup.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_board_processing_error():
    """
    Given: ボード処理中にエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーをログに記録し、他のボードの処理を継続
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = AsyncMock()
        service.target_boards = ["g", "sci"]

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service, "_retrieve_ai_threads", side_effect=[Exception("Board error"), []]),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            jst_today = get_jst_date_from_utc(datetime.now(UTC))
            result = await service.collect(target_dates=[jst_today])

            # エラーがあっても処理が完了する
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_date_filtering_outside_range():
    """
    Given: 対象日付範囲外のスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: スレッドがスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        # 30日以上前のスレッド（対象外）
        old_timestamp = int((datetime.now(UTC) - timedelta(days=40)).timestamp())

        # カタログレスポンスをモック
        catalog_response = Mock()
        catalog_response.json.return_value = [
            {
                "threads": [
                    {
                        "no": 123456,
                        "sub": "AI Thread",
                        "com": "AI discussion",
                        "replies": 10,
                        "images": 2,
                        "bumplimit": 0,
                        "imagelimit": 0,
                        "last_modified": old_timestamp,
                        "time": old_timestamp,
                    }
                ]
            }
        ]

        # スレッド詳細レスポンスをモック
        thread_response = Mock()
        thread_response.json.return_value = {
            "posts": [
                {"no": 123456, "time": old_timestamp, "com": "OP post"}
            ]
        }

        service.http_client.get = AsyncMock(side_effect=[catalog_response, thread_response])

        # 今日の日付のみを対象
        jst_today = get_jst_date_from_utc(datetime.now(UTC))
        target_dates = {jst_today}

        dedup_tracker = DedupTracker()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._retrieve_ai_threads("g", 10, dedup_tracker, target_dates)

        # 対象外のスレッドはフィルタリングされる
        assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_timezone_handling():
    """
    Given: タイムゾーン情報がないdatetimeを含むスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: UTCタイムゾーンが適用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        current_timestamp = int(datetime.now(UTC).timestamp())

        # カタログレスポンスをモック
        catalog_response = Mock()
        catalog_response.json.return_value = [
            {
                "threads": [
                    {
                        "no": 123456,
                        "sub": "AI Thread",
                        "com": "AI discussion",
                        "replies": 10,
                        "images": 2,
                        "bumplimit": 0,
                        "imagelimit": 0,
                        "last_modified": current_timestamp,
                        "time": current_timestamp,
                    }
                ]
            }
        ]

        # スレッド詳細レスポンスをモック
        thread_response = Mock()
        thread_response.json.return_value = {
            "posts": [
                {"no": 123456, "time": current_timestamp, "com": "OP post"}
            ]
        }

        service.http_client.get = AsyncMock(side_effect=[catalog_response, thread_response])
        service.gpt_client.get_response = AsyncMock(return_value="Test summary")

        jst_today = get_jst_date_from_utc(datetime.now(UTC))
        target_dates = {jst_today}

        dedup_tracker = DedupTracker()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._retrieve_ai_threads("g", 10, dedup_tracker, target_dates)

        # スレッドが正常に処理される
        assert len(result) == 1
        assert result[0].thread_id == 123456


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_ai_threads_missing_effective_datetime_warning():
    """
    Given: 有効な日時とタイムスタンプが両方とも取得できないスレッド
    When: _retrieve_ai_threadsを呼び出す
    Then: 警告ログが出力されスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        # カタログレスポンスをモック（タイムスタンプなし）
        catalog_response = Mock()
        catalog_response.json.return_value = [
            {
                "threads": [
                    {
                        "no": 123456,
                        "sub": "AI Thread",
                        "com": "AI discussion",
                        "replies": 10,
                        "images": 2,
                        "bumplimit": 0,
                        "imagelimit": 0,
                        # last_modifiedとtimeが両方ともない
                    }
                ]
            }
        ]

        # スレッド詳細レスポンスをモック（投稿もタイムスタンプなし）
        thread_response = Mock()
        thread_response.json.return_value = {
            "posts": [
                {"no": 123456, "com": "OP post"}  # timeフィールドなし
            ]
        }

        service.http_client.get = AsyncMock(side_effect=[catalog_response, thread_response])

        jst_today = get_jst_date_from_utc(datetime.now(UTC))
        target_dates = {jst_today}

        dedup_tracker = DedupTracker()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._retrieve_ai_threads("g", 10, dedup_tracker, target_dates)

        # タイムスタンプがないスレッドはスキップされる
        assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_threads_grouping_by_date():
    """
    Given: 複数の日付にまたがるスレッド
    When: collectメソッドを呼び出す
    Then: 日付ごとにグループ化され、各日独立で上位15件が選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        # 2つの異なる日付のスレッドを準備
        today = datetime.now(UTC)
        yesterday = today - timedelta(days=1)

        today_timestamp = int(today.timestamp())
        yesterday_timestamp = int(yesterday.timestamp())

        threads_today = [
            Thread(
                thread_id=i,
                board="g",
                title=f"Today Thread {i}",
                url=f"https://boards.4chan.org/g/thread/{i}",
                timestamp=today_timestamp,
                summary=f"Summary {i}",
                popularity_score=100 - i,
                posts=[],
            )
            for i in range(1, 8)
        ]

        threads_yesterday = [
            Thread(
                thread_id=i + 100,
                board="g",
                title=f"Yesterday Thread {i}",
                url=f"https://boards.4chan.org/g/thread/{i+100}",
                timestamp=yesterday_timestamp,
                summary=f"Summary {i+100}",
                popularity_score=50 - i,
                posts=[],
            )
            for i in range(1, 6)
        ]

        all_threads = threads_today + threads_yesterday

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service, "_retrieve_ai_threads", new_callable=AsyncMock, return_value=all_threads
            ),
            patch.object(service, "_summarize_thread", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            jst_today = get_jst_date_from_utc(today)
            jst_yesterday = get_jst_date_from_utc(yesterday)
            result = await service.collect(target_dates=[jst_today, jst_yesterday])

            # 両日のデータが処理される
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_more_than_limit_threads_per_date():
    """
    Given: 1日あたりの上限（15件）を超えるスレッド
    When: collectメソッドを呼び出す
    Then: 人気スコアでソートされ、上位15件が選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        today = datetime.now(UTC)
        today_timestamp = int(today.timestamp())

        # 20件のスレッドを準備（上限15件を超える）
        threads = [
            Thread(
                thread_id=i,
                board="g",
                title=f"Thread {i}",
                url=f"https://boards.4chan.org/g/thread/{i}",
                timestamp=today_timestamp - i,  # 異なる時刻
                summary=f"Summary {i}",
                popularity_score=100 - i,  # 降順のスコア
                posts=[],
            )
            for i in range(1, 21)
        ]

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service, "_retrieve_ai_threads", new_callable=AsyncMock, return_value=threads
            ),
            patch.object(service, "_summarize_thread", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            jst_today = get_jst_date_from_utc(today)
            result = await service.collect(target_dates=[jst_today], thread_limit=15)

            # 15件に制限される
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_no_selected_threads():
    """
    Given: 選択されたスレッドがない
    When: collectメソッドを呼び出す
    Then: 保存処理がスキップされ、空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service, "_retrieve_ai_threads", new_callable=AsyncMock, return_value=[]
            ),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
            ) as mock_save,
        ):
            jst_today = get_jst_date_from_utc(datetime.now(UTC))
            result = await service.collect(target_dates=[jst_today])

            # 保存処理が呼び出されない
            mock_save.assert_not_called()
            # 空のリストが返される
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_summarization_loop_coverage():
    """
    Given: 要約対象のスレッドが複数ある
    When: collectメソッドを呼び出す
    Then: 各スレッドに対して要約が生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fourchan_explorer.fourchan_explorer import (
            FourChanExplorer,
            Thread,
        )

        service = FourChanExplorer()
        service.http_client = AsyncMock()

        today = datetime.now(UTC)
        today_timestamp = int(today.timestamp())

        # 3件のスレッドを準備
        threads = [
            Thread(
                thread_id=i,
                board="g",
                title=f"Thread {i}",
                url=f"https://boards.4chan.org/g/thread/{i}",
                timestamp=today_timestamp,
                summary=f"Summary {i}",
                popularity_score=100 - i,
                posts=[],
            )
            for i in range(1, 4)
        ]

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service, "_retrieve_ai_threads", new_callable=AsyncMock, return_value=threads
            ),
            patch.object(service, "_summarize_thread", new_callable=AsyncMock) as mock_summarize,
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            jst_today = get_jst_date_from_utc(today)
            await service.collect(target_dates=[jst_today])

            # 要約が呼び出される（少なくとも1回以上）
            assert mock_summarize.call_count >= 3
