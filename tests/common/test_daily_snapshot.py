from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots


def test_group_records_by_date_handles_missing_and_parsed_dates():
    reference = datetime(2024, 10, 28, 12, 0, 0)
    records = [
        {"title": "today", "published_at": reference.isoformat()},
        {
            "title": "yesterday",
            "published_at": (reference - timedelta(days=1)).isoformat(),
        },
        {"title": "no-date", "published_at": None},
        {"title": "already-datetime", "published_at": reference},
    ]

    grouped = group_records_by_date(records, default_date=reference.date())

    assert sorted(grouped.keys()) == [
        reference.date() - timedelta(days=1),
        reference.date(),
    ]
    today_records = grouped[reference.date()]
    assert {item["title"] for item in today_records} == {
        "today",
        "no-date",
        "already-datetime",
    }
    yesterday_records = grouped[reference.date() - timedelta(days=1)]
    assert {item["title"] for item in yesterday_records} == {"yesterday"}


@pytest.mark.asyncio
async def test_store_daily_snapshots_merges_and_saves(tmp_path):
    base = datetime(2024, 10, 28, 9, 0, 0)
    grouped = {
        base.date(): [
            {
                "title": "new-top",
                "published_at": base.isoformat(),
                "popularity_score": 10,
            },
            {
                "title": "new-low",
                "published_at": None,
                "popularity_score": 1,
            },
        ],
        (base - timedelta(days=1)).date(): [
            {
                "title": "yesterday-new",
                "published_at": (base - timedelta(days=1)).isoformat(),
                "popularity_score": 3,
            }
        ],
    }

    stored_json: dict[str, list[dict]] = {
        (base - timedelta(days=1)).strftime("%Y-%m-%d"): [
            {
                "title": "yesterday-existing",
                "published_at": (base - timedelta(days=1)).isoformat(),
                "popularity_score": 5,
            }
        ]
    }
    stored_markdown: dict[str, str] = {}

    async def load_existing(snapshot_datetime: datetime):
        key = snapshot_datetime.strftime("%Y-%m-%d")
        return list(stored_json.get(key, []))

    async def save_json(data, filename: str):
        key = filename[:-5]
        stored_json[key] = list(data)
        return tmp_path / filename

    async def save_markdown(content: str, filename: str):
        key = filename[:-3]
        stored_markdown[key] = content
        return tmp_path / filename

    def render_markdown(records, snapshot_datetime: datetime) -> str:
        titles = ", ".join(sorted(item["title"] for item in records))
        return f"{snapshot_datetime.strftime('%Y-%m-%d')}: {titles}"

    await store_daily_snapshots(
        grouped,
        load_existing=load_existing,
        save_json=save_json,
        save_markdown=save_markdown,
        render_markdown=render_markdown,
        key=lambda item: item.get("title"),
        sort_key=lambda item: item.get("popularity_score", 0),
        limit=2,
    )

    today_key = base.strftime("%Y-%m-%d")
    yesterday_key = (base - timedelta(days=1)).strftime("%Y-%m-%d")

    assert [item["title"] for item in stored_json[today_key]] == ["new-top", "new-low"]
    assert [item["title"] for item in stored_json[yesterday_key]] == [
        "yesterday-existing",
        "yesterday-new",
    ]

    assert today_key in stored_markdown
    assert yesterday_key in stored_markdown
    assert "new-top" in stored_markdown[today_key]
    assert "yesterday-existing" in stored_markdown[yesterday_key]


def test_parse_record_date_invalid_iso_string():
    """
    Given: 無効なISO形式文字列
    When: _parse_record_dateを呼び出す（group_records_by_date経由）
    Then: ValueErrorが発生してNoneを返す
    """
    from nook.common.daily_snapshot import _parse_record_date

    # 無効なISO形式文字列
    result = _parse_record_date("invalid-date-string")
    assert result is None

    # 空文字列
    result = _parse_record_date("")
    assert result is None

    # None
    result = _parse_record_date(None)
    assert result is None


@pytest.mark.asyncio
async def test_store_daily_snapshots_with_logger(tmp_path):
    """
    Given: loggerを渡してstore_daily_snapshotsを実行
    When: 処理が実行される
    Then: logger.infoが呼び出される
    """
    from unittest.mock import Mock
    import logging

    base = datetime(2024, 10, 28, 9, 0, 0)
    grouped = {
        base.date(): [
            {
                "title": "test-article",
                "published_at": base.isoformat(),
                "popularity_score": 10,
            }
        ]
    }

    stored_json: dict[str, list[dict]] = {}
    stored_markdown: dict[str, str] = {}

    async def load_existing(snapshot_datetime: datetime):
        return []

    async def save_json(data, filename: str):
        key = filename[:-5]
        stored_json[key] = list(data)
        return tmp_path / filename

    async def save_markdown(content: str, filename: str):
        key = filename[:-3]
        stored_markdown[key] = content
        return tmp_path / filename

    def render_markdown(records, snapshot_datetime: datetime) -> str:
        return f"{snapshot_datetime.strftime('%Y-%m-%d')}"

    # モックロガーを作成
    mock_logger = Mock(spec=logging.Logger)

    await store_daily_snapshots(
        grouped,
        load_existing=load_existing,
        save_json=save_json,
        save_markdown=save_markdown,
        render_markdown=render_markdown,
        key=lambda item: item.get("title"),
        sort_key=lambda item: item.get("popularity_score", 0),
        limit=10,
        logger=mock_logger,
    )

    # logger.infoが呼び出されたことを確認
    assert mock_logger.info.called
    assert mock_logger.info.call_count >= 2  # 日付処理と候補記事の2回以上
