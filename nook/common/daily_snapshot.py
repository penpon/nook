"""Helpers for splitting records by day and persisting daily snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence

from nook.common.daily_merge import merge_records


Record = dict[str, Any]


def _parse_record_date(value: object) -> date | None:
    """Attempt to parse a record's published date component."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.date()

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
    save_json: Callable[[Sequence[Record], str], Awaitable[object]],
    save_markdown: Callable[[str, str], Awaitable[object]],
    render_markdown: Callable[[Sequence[Record], datetime], str],
    key: Callable[[Record], object],
    sort_key: Callable[[Record], object] | None,
    limit: int | None,
    reverse: bool = True,
) -> None:
    """Persist grouped records into per-day JSON and Markdown snapshots."""

    for record_date, records in sorted(records_by_date.items()):
        snapshot_datetime = datetime.combine(record_date, time.min)
        existing = await load_existing(snapshot_datetime)

        merged = merge_records(
            existing,
            records,
            key=key,
            sort_key=sort_key,
            limit=limit,
            reverse=reverse,
        )

        date_str = snapshot_datetime.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        filename_md = f"{date_str}.md"

        await save_json(merged, filename_json)
        markdown = render_markdown(merged, snapshot_datetime)
        await save_markdown(markdown, filename_md)
