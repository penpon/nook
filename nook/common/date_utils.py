"""Utilities for computing target date ranges for service collectors."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Set


def _local_timezone() -> timezone:
    """Return the current local timezone."""

    return datetime.now().astimezone().tzinfo or timezone.utc


def compute_target_dates(
    days: int | None = None, *, base_date: date | None = None
) -> list[date]:
    """Return a list of target dates (descending from base date) for the given window.

    Parameters
    ----------
    days:
        Number of days to include. ``None`` or values < 1 default to 1.
    base_date:
        The most recent date (typically "today") to include. Defaults to the
        current local date.
    """

    normalized_days = max(1, days or 1)
    start = base_date or datetime.now().astimezone().date()

    return [start - timedelta(days=offset) for offset in range(normalized_days)]


def target_dates_set(
    days: int | None = None, *, base_date: date | None = None
) -> Set[date]:
    """Convenience wrapper that returns the target dates as a ``set``."""

    return set(compute_target_dates(days, base_date=base_date))


def normalize_datetime_to_local(dt: datetime | None) -> datetime | None:
    """Convert ``dt`` to the local timezone, assuming UTC for naive values."""

    if dt is None:
        return None

    local_tz = _local_timezone()
    tz = dt.tzinfo or local_tz
    return dt.replace(tzinfo=tz).astimezone(local_tz)


def is_within_target_dates(dt: datetime | None, target_dates: Iterable[date]) -> bool:
    """Return ``True`` when ``dt`` falls on one of ``target_dates`` in local time."""

    normalized = normalize_datetime_to_local(dt)
    if normalized is None:
        return False

    target_set = set(target_dates)
    if not target_set:
        return False

    return normalized.date() in target_set
