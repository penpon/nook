from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.core.utils import date_utils  # noqa: E402


def test_compute_target_dates_defaults_to_today_and_one_day(monkeypatch):
    fake_today = date(2024, 11, 1)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.combine(fake_today, datetime.min.time(), tzinfo=tz)

    monkeypatch.setattr(date_utils, "datetime", FakeDateTime)

    assert date_utils.compute_target_dates() == [fake_today]


def test_compute_target_dates_with_custom_days_and_base():
    base = date(2024, 10, 10)
    assert date_utils.compute_target_dates(days=3, base_date=base) == [
        base,
        date(2024, 10, 9),
        date(2024, 10, 8),
    ]


def test_target_dates_set_wraps_compute():
    assert date_utils.target_dates_set(days=2, base_date=date(2024, 1, 2)) == {
        date(2024, 1, 2),
        date(2024, 1, 1),
    }


def test_normalize_datetime_to_local_handles_none_and_naive(monkeypatch):
    tz = timezone.utc

    def fake_local_timezone():
        return tz

    monkeypatch.setattr(date_utils, "_local_timezone", fake_local_timezone)

    assert date_utils.normalize_datetime_to_local(None) is None
    naive = datetime(2024, 11, 2, 12, 0, 0)
    normalized = date_utils.normalize_datetime_to_local(naive)
    assert normalized.tzinfo == tz


def test_normalize_datetime_to_local_with_existing_tz(monkeypatch):
    def fake_local_timezone():
        return timezone.utc

    monkeypatch.setattr(date_utils, "_local_timezone", fake_local_timezone)

    aware = datetime(2024, 11, 2, 12, 0, 0, tzinfo=timezone.utc)
    normalized = date_utils.normalize_datetime_to_local(aware)
    assert normalized.tzinfo == timezone.utc


def test_is_within_target_dates_falsey_cases():
    assert date_utils.is_within_target_dates(None, []) is False
    assert date_utils.is_within_target_dates(datetime(2024, 1, 1), []) is False


def test_is_within_target_dates_matches_after_normalization(monkeypatch):
    def fake_local_timezone():
        return timezone.utc

    monkeypatch.setattr(date_utils, "_local_timezone", fake_local_timezone)

    target = [date(2024, 11, 5)]
    dt = datetime(2024, 11, 5, 12, 0, 0)
    assert date_utils.is_within_target_dates(dt, target) is True
