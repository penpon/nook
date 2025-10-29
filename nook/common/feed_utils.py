from __future__ import annotations

import calendar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable


__all__ = ["parse_entry_datetime"]


_STRUCT_TIME_FIELDS: Iterable[str] = (
    "published_parsed",
    "updated_parsed",
    "created_parsed",
    "issued_parsed",
)

_STRING_FIELDS: Iterable[str] = (
    "published",
    "updated",
    "created",
    "issued",
)


def _get_entry_value(entry: Any, field: str) -> Any:
    if hasattr(entry, field):
        return getattr(entry, field)
    if isinstance(entry, dict):
        return entry.get(field)
    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None

    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"

    if len(cleaned) == 10:
        cleaned = f"{cleaned}T00:00:00"

    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed

    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def parse_entry_datetime(entry: Any) -> datetime | None:
    for field in _STRUCT_TIME_FIELDS:
        value = _get_entry_value(entry, field)
        if value is None:
            continue

        try:
            timestamp = calendar.timegm(value)
        except (TypeError, ValueError):
            continue

        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)

    for field in _STRING_FIELDS:
        value = _get_entry_value(entry, field)
        if not value:
            continue

        text = str(value)

        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            parsed = None

        if parsed:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=None)
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)

        iso_parsed = _parse_iso_datetime(text)
        if iso_parsed:
            return iso_parsed

    return None
