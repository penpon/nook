"""nook/common/date_utils.py のテスト"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.date_utils import (
    _local_timezone,
    compute_target_dates,
    is_within_target_dates,
    normalize_datetime_to_local,
    target_dates_set,
)

# タイムゾーン定義
JST = timezone(timedelta(hours=9))


# ================================================================================
# 1. _local_timezone 関数のテスト
# ================================================================================


@pytest.mark.unit
def test_local_timezone_returns_jst():
    """
    Given: なし
    When: _local_timezoneを呼び出す
    Then: timezone(timedelta(hours=9))が返される
    """
    result = _local_timezone()
    expected = timezone(timedelta(hours=9))
    assert result == expected


# ================================================================================
# 2. compute_target_dates 関数のテスト
# ================================================================================

# 2.1 基本的な動作


@pytest.mark.unit
def test_compute_target_dates_default():
    """
    Given: 引数なし
    When: compute_target_datesを呼び出す
    Then: 今日のJSTの日付1つのリストが返される
    """
    result = compute_target_dates()
    today_jst = datetime.now(_local_timezone()).date()
    assert len(result) == 1
    assert result[0] == today_jst


@pytest.mark.unit
def test_compute_target_dates_one_day():
    """
    Given: days=1, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: [date(2024,1,15)]が返される
    """
    result = compute_target_dates(days=1, base_date=date(2024, 1, 15))
    assert len(result) == 1
    assert result[0] == date(2024, 1, 15)


@pytest.mark.unit
def test_compute_target_dates_three_days():
    """
    Given: days=3, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: [date(2024,1,15), date(2024,1,14), date(2024,1,13)]が返される
    """
    result = compute_target_dates(days=3, base_date=date(2024, 1, 15))
    expected = [date(2024, 1, 15), date(2024, 1, 14), date(2024, 1, 13)]
    assert result == expected


@pytest.mark.unit
def test_compute_target_dates_seven_days():
    """
    Given: days=7, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: 7日分のリスト（降順）が返される
    """
    result = compute_target_dates(days=7, base_date=date(2024, 1, 15))
    assert len(result) == 7
    assert result[0] == date(2024, 1, 15)
    assert result[6] == date(2024, 1, 9)


# 2.2 境界値・エッジケース


@pytest.mark.unit
def test_compute_target_dates_zero_days():
    """
    Given: days=0, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: [date(2024,1,15)]（1日分）が返される
    """
    result = compute_target_dates(days=0, base_date=date(2024, 1, 15))
    assert len(result) == 1
    assert result[0] == date(2024, 1, 15)


@pytest.mark.unit
def test_compute_target_dates_negative_days():
    """
    Given: days=-5, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: [date(2024,1,15)]（1日分）が返される
    """
    result = compute_target_dates(days=-5, base_date=date(2024, 1, 15))
    assert len(result) == 1
    assert result[0] == date(2024, 1, 15)


@pytest.mark.unit
def test_compute_target_dates_none_days():
    """
    Given: days=None, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: [date(2024,1,15)]（1日分）が返される
    """
    result = compute_target_dates(days=None, base_date=date(2024, 1, 15))
    assert len(result) == 1
    assert result[0] == date(2024, 1, 15)


@pytest.mark.unit
def test_compute_target_dates_none_base_date():
    """
    Given: days=1, base_date=None
    When: compute_target_datesを呼び出す
    Then: 今日のJST日付が返される
    """
    result = compute_target_dates(days=1, base_date=None)
    today_jst = datetime.now(_local_timezone()).date()
    assert len(result) == 1
    assert result[0] == today_jst


@pytest.mark.unit
def test_compute_target_dates_cross_month():
    """
    Given: days=5, base_date=date(2024,1,3)
    When: compute_target_datesを呼び出す
    Then: [2024-01-03, 01-02, 01-01, 2023-12-31, 12-30]が返される
    """
    result = compute_target_dates(days=5, base_date=date(2024, 1, 3))
    expected = [
        date(2024, 1, 3),
        date(2024, 1, 2),
        date(2024, 1, 1),
        date(2023, 12, 31),
        date(2023, 12, 30),
    ]
    assert result == expected


@pytest.mark.unit
def test_compute_target_dates_cross_year():
    """
    Given: days=5, base_date=date(2024,1,2)
    When: compute_target_datesを呼び出す
    Then: [2024-01-02, 01-01, 2023-12-31, 12-30, 12-29]が返される
    """
    result = compute_target_dates(days=5, base_date=date(2024, 1, 2))
    expected = [
        date(2024, 1, 2),
        date(2024, 1, 1),
        date(2023, 12, 31),
        date(2023, 12, 30),
        date(2023, 12, 29),
    ]
    assert result == expected


@pytest.mark.unit
def test_compute_target_dates_leap_year():
    """
    Given: days=2, base_date=date(2024,3,1)
    When: compute_target_datesを呼び出す
    Then: [2024-03-01, 02-29]（うるう日含む）が返される
    """
    result = compute_target_dates(days=2, base_date=date(2024, 3, 1))
    expected = [date(2024, 3, 1), date(2024, 2, 29)]
    assert result == expected


@pytest.mark.unit
def test_compute_target_dates_large_days():
    """
    Given: days=365, base_date=date(2024,12,31)
    When: compute_target_datesを呼び出す
    Then: 365日分のリストが返される
    """
    result = compute_target_dates(days=365, base_date=date(2024, 12, 31))
    assert len(result) == 365
    assert result[0] == date(2024, 12, 31)
    assert result[364] == date(2024, 1, 2)  # 2024はうるう年


# 2.3 降順ソート確認


@pytest.mark.unit
def test_compute_target_dates_descending_order():
    """
    Given: days=5, base_date=date(2024,1,15)
    When: compute_target_datesを呼び出す
    Then: リストが降順（新しい順）になっている
    """
    result = compute_target_dates(days=5, base_date=date(2024, 1, 15))
    # 降順確認: 各要素が前の要素より小さい
    for i in range(len(result) - 1):
        assert result[i] > result[i + 1]


# ================================================================================
# 3. target_dates_set 関数のテスト
# ================================================================================


@pytest.mark.unit
def test_target_dates_set_returns_set():
    """
    Given: days=3, base_date=date(2024,1,15)
    When: target_dates_setを呼び出す
    Then: set型で3要素が返される
    """
    result = target_dates_set(days=3, base_date=date(2024, 1, 15))
    assert isinstance(result, set)
    assert len(result) == 3


@pytest.mark.unit
def test_target_dates_set_matches_compute():
    """
    Given: days=5, base_date=date(2024,1,15)
    When: target_dates_setを呼び出す
    Then: compute_target_datesの結果と一致
    """
    result_set = target_dates_set(days=5, base_date=date(2024, 1, 15))
    result_list = compute_target_dates(days=5, base_date=date(2024, 1, 15))
    assert result_set == set(result_list)


@pytest.mark.unit
def test_target_dates_set_no_duplicates():
    """
    Given: days=3, base_date=date(2024,1,15)
    When: target_dates_setを呼び出す
    Then: set要素数=3（重複なし）
    """
    result = target_dates_set(days=3, base_date=date(2024, 1, 15))
    # setは重複を許さない
    assert len(result) == 3


# ================================================================================
# 4. normalize_datetime_to_local 関数のテスト
# ================================================================================

# 4.1 タイムゾーン変換


@pytest.mark.unit
def test_normalize_datetime_utc_to_jst():
    """
    Given: datetime(2024,1,15,10,30, tzinfo=UTC)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,15,19,30, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 15, 19, 30, 0, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_jst_to_jst():
    """
    Given: datetime(2024,1,15,10,30, tzinfo=JST)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,15,10,30, tzinfo=JST)が返される（変換なし）
    """
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=JST)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 15, 10, 30, 0, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_naive():
    """
    Given: datetime(2024,1,15,10,30)（tzinfo=None）
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,15,10,30, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 10, 30, 0)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 15, 10, 30, 0, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_negative_timezone():
    """
    Given: datetime(2024,1,15,10,30, tzinfo=UTC-5)
    When: normalize_datetime_to_localを呼び出す
    Then: JSTに変換される
    """
    est = timezone(timedelta(hours=-5))
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=est)
    result = normalize_datetime_to_local(dt)
    # EST 10:30 -> UTC 15:30 -> JST 00:30 (next day)
    expected = datetime(2024, 1, 16, 0, 30, 0, tzinfo=JST)
    assert result == expected


# 4.2 境界値・エッジケース


@pytest.mark.unit
def test_normalize_datetime_none_input():
    """
    Given: dt=None
    When: normalize_datetime_to_localを呼び出す
    Then: Noneが返される
    """
    result = normalize_datetime_to_local(None)
    assert result is None


@pytest.mark.unit
def test_normalize_datetime_utc_midnight():
    """
    Given: datetime(2024,1,15,0,0,0, tzinfo=UTC)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,15,9,0,0, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 15, 9, 0, 0, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_jst_midnight():
    """
    Given: datetime(2024,1,15,0,0,0, tzinfo=JST)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,15,0,0,0, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_date_boundary():
    """
    Given: datetime(2024,1,15,23,59,59, tzinfo=UTC)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,16,8,59,59, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 23, 59, 59, tzinfo=UTC)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 16, 8, 59, 59, tzinfo=JST)
    assert result == expected


@pytest.mark.unit
def test_normalize_datetime_cross_day():
    """
    Given: datetime(2024,1,15,20,0,0, tzinfo=UTC)
    When: normalize_datetime_to_localを呼び出す
    Then: datetime(2024,1,16,5,0,0, tzinfo=JST)が返される
    """
    dt = datetime(2024, 1, 15, 20, 0, 0, tzinfo=UTC)
    result = normalize_datetime_to_local(dt)
    expected = datetime(2024, 1, 16, 5, 0, 0, tzinfo=JST)
    assert result == expected


# ================================================================================
# 5. is_within_target_dates 関数のテスト
# ================================================================================

# 5.1 基本的な動作


@pytest.mark.unit
def test_is_within_target_dates_in_range():
    """
    Given: dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST)
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_out_of_range():
    """
    Given: dt=datetime(2024,1,16,10,0, tzinfo=JST), target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Falseが返される
    """
    dt = datetime(2024, 1, 16, 10, 0, 0, tzinfo=JST)
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(dt, target_dates)
    assert result is False


@pytest.mark.unit
def test_is_within_target_dates_multiple_dates():
    """
    Given: dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates={date(2024,1,14), date(2024,1,15), date(2024,1,16)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST)
    target_dates = {date(2024, 1, 14), date(2024, 1, 15), date(2024, 1, 16)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_utc_datetime():
    """
    Given: dt=datetime(2024,1,15,10,0, tzinfo=UTC), target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: JST変換後に判定される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
    target_dates = {date(2024, 1, 15)}
    # UTC 10:00 -> JST 19:00 (same day)
    result = is_within_target_dates(dt, target_dates)
    assert result is True


# 5.2 境界値・エッジケース


@pytest.mark.unit
def test_is_within_target_dates_none_datetime():
    """
    Given: dt=None, target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Falseが返される
    """
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(None, target_dates)
    assert result is False


@pytest.mark.unit
def test_is_within_target_dates_empty_target_dates():
    """
    Given: dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates=set()
    When: is_within_target_datesを呼び出す
    Then: Falseが返される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST)
    target_dates = set()
    result = is_within_target_dates(dt, target_dates)
    assert result is False


@pytest.mark.unit
def test_is_within_target_dates_empty_list():
    """
    Given: dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates=[]
    When: is_within_target_datesを呼び出す
    Then: Falseが返される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST)
    target_dates = []
    result = is_within_target_dates(dt, target_dates)
    assert result is False


@pytest.mark.unit
def test_is_within_target_dates_naive_datetime():
    """
    Given: dt=datetime(2024,1,15,10,0)（tzinfo=None）, target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: JST扱いでTrueが返される
    """
    dt = datetime(2024, 1, 15, 10, 0, 0)
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


# 5.3 日付境界のエッジケース


@pytest.mark.unit
def test_is_within_target_dates_jst_midnight_start():
    """
    Given: dt=datetime(2024,1,15,0,0,0, tzinfo=JST), target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_jst_midnight_end():
    """
    Given: dt=datetime(2024,1,15,23,59,59, tzinfo=JST), target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 1, 15, 23, 59, 59, tzinfo=JST)
    target_dates = {date(2024, 1, 15)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_utc_crosses_day():
    """
    Given: dt=datetime(2024,1,14,20,0,0, tzinfo=UTC)（JST 01/15 05:00）, target_dates={date(2024,1,15)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 1, 14, 20, 0, 0, tzinfo=UTC)
    target_dates = {date(2024, 1, 15)}
    # UTC 2024-01-14 20:00 -> JST 2024-01-15 05:00
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_utc_different_day():
    """
    Given: dt=datetime(2024,1,15,2,0,0, tzinfo=UTC)（JST 01/15 11:00）, target_dates={date(2024,1,14)}
    When: is_within_target_datesを呼び出す
    Then: Falseが返される
    """
    dt = datetime(2024, 1, 15, 2, 0, 0, tzinfo=UTC)
    target_dates = {date(2024, 1, 14)}
    # UTC 2024-01-15 02:00 -> JST 2024-01-15 11:00
    result = is_within_target_dates(dt, target_dates)
    assert result is False


# 5.4 複雑なケース


@pytest.mark.unit
def test_is_within_target_dates_multiple_timezones():
    """
    Given: UTCとJSTの時刻、複数target_dates
    When: is_within_target_datesを呼び出す
    Then: 正しく判定される
    """
    dt_utc = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
    target_dates = {date(2024, 1, 14), date(2024, 1, 15), date(2024, 1, 16)}
    # UTC 10:00 -> JST 19:00 (2024-01-15)
    result = is_within_target_dates(dt_utc, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_leap_day():
    """
    Given: dt=datetime(2024,2,29,10,0, tzinfo=JST), target_dates={date(2024,2,29)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 2, 29, 10, 0, 0, tzinfo=JST)
    target_dates = {date(2024, 2, 29)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True


@pytest.mark.unit
def test_is_within_target_dates_year_boundary():
    """
    Given: dt=datetime(2024,12,31,23,59,59, tzinfo=JST), target_dates={date(2024,12,31)}
    When: is_within_target_datesを呼び出す
    Then: Trueが返される
    """
    dt = datetime(2024, 12, 31, 23, 59, 59, tzinfo=JST)
    target_dates = {date(2024, 12, 31)}
    result = is_within_target_dates(dt, target_dates)
    assert result is True
