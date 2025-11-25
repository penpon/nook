"""Helpers for splitting records by day and persisting daily snapshots."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from datetime import date, datetime, time
from logging import Logger
from typing import Any

from nook.common.daily_merge import merge_records
from nook.common.date_utils import normalize_datetime_to_local

Record = dict[str, Any]


def _parse_record_date(value: object) -> date | None:
    """Attempt to parse a record's published date component."""
    if isinstance(value, datetime):
        local_dt = normalize_datetime_to_local(value)
        return local_dt.date() if local_dt else None

    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        local_dt = normalize_datetime_to_local(parsed)
        return local_dt.date() if local_dt else None

    return None


def group_records_by_date(
    records: Iterable[Record], *, default_date: date
) -> Mapping[date, list[Record]]:
    """Group serialized article records by their published date."""
    grouped: dict[date, list[Record]] = defaultdict(list)

    for record in records:
        published = record.get("published_at")
        record_date = _parse_record_date(published) or default_date
        grouped[record_date].append(record)

    return grouped


async def store_daily_snapshots(
    records_by_date: Mapping[date, Sequence[Record]],
    *,
    load_existing: Callable[[datetime], Awaitable[Sequence[Record]]],
    save_json: Callable[[list[Record], str], Awaitable[object]],
    save_markdown: Callable[[str, str], Awaitable[object]],
    render_markdown: Callable[[list[Record], datetime], str],
    key: Callable[[Record], object],
    sort_key: Callable[[Record], object] | None,
    limit: int | None,
    reverse: bool = True,
    logger: Logger | None = None,
) -> list[tuple[str, str]]:
    """Persist grouped records into per-day JSON and Markdown snapshots.

    Returns
    -------
    list[tuple[str, str]]
        保存されたファイルパスのリスト [(json_path, md_path), ...]

    """
    saved_files: list[tuple[str, str]] = []

    for record_date, records in sorted(records_by_date.items()):
        snapshot_datetime = datetime.combine(record_date, time.min)
        date_str = snapshot_datetime.strftime("%Y-%m-%d")

        if logger:
            logger.info(f"\n📰 [{date_str}] の記事を処理中...")
            logger.info(f"   🔍 候補記事: {len(records)}件")

        existing = await load_existing(snapshot_datetime)

        merged = merge_records(
            existing,
            records,
            key=key,
            sort_key=sort_key,
            limit=limit,
            reverse=reverse,
        )

        filename_json = f"{date_str}.json"
        filename_md = f"{date_str}.md"

        json_path = await save_json(merged, filename_json)
        markdown = render_markdown(merged, snapshot_datetime)
        md_path = await save_markdown(markdown, filename_md)

        saved_files.append((str(json_path), str(md_path)))

    return saved_files
