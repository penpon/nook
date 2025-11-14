# date_utils テスト仕様書

## 概要
`nook/common/date_utils.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- タイムゾーン処理（JST/UTC）を重点的にテスト
- 日付範囲計算の境界値を網羅
- None、負数、0などのエッジケースを考慮

---

## 1. _local_timezone 関数のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | JST（UTC+9）取得 | 正常系 | なし | timezone(timedelta(hours=9))が返される | High | test_local_timezone_returns_jst |

---

## 2. compute_target_dates 関数のテスト

### 2.1 基本的な動作

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 2 | デフォルト動作（引数なし） | 正常系 | days=None, base_date=None | 今日のJSTの日付1つのリスト | High | test_compute_target_dates_default |
| 3 | 1日分の日付 | 正常系 | days=1, base_date=date(2024,1,15) | [date(2024,1,15)] | High | test_compute_target_dates_one_day |
| 4 | 3日分の日付 | 正常系 | days=3, base_date=date(2024,1,15) | [date(2024,1,15), date(2024,1,14), date(2024,1,13)] | High | test_compute_target_dates_three_days |
| 5 | 7日分の日付 | 正常系 | days=7, base_date=date(2024,1,15) | 7日分のリスト（降順） | High | test_compute_target_dates_seven_days |

### 2.2 境界値・エッジケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 6 | days=0 | 境界値 | days=0, base_date=date(2024,1,15) | [date(2024,1,15)]（1日分） | High | test_compute_target_dates_zero_days |
| 7 | days=負数 | 境界値 | days=-5, base_date=date(2024,1,15) | [date(2024,1,15)]（1日分） | High | test_compute_target_dates_negative_days |
| 8 | days=None | 境界値 | days=None, base_date=date(2024,1,15) | [date(2024,1,15)]（1日分） | High | test_compute_target_dates_none_days |
| 9 | base_date=None | 正常系 | days=1, base_date=None | 今日のJST日付 | High | test_compute_target_dates_none_base_date |
| 10 | 月をまたぐ日付範囲 | 正常系 | days=5, base_date=date(2024,1,3) | [2024-01-03, 01-02, 01-01, 2023-12-31, 12-30] | High | test_compute_target_dates_cross_month |
| 11 | 年をまたぐ日付範囲 | 正常系 | days=5, base_date=date(2024,1,2) | [2024-01-02, 01-01, 2023-12-31, 12-30, 12-29] | High | test_compute_target_dates_cross_year |
| 12 | うるう年の境界 | 境界値 | days=2, base_date=date(2024,3,1) | [2024-03-01, 02-29]（うるう日含む） | Medium | test_compute_target_dates_leap_year |
| 13 | 大きなdays値 | 境界値 | days=365, base_date=date(2024,12,31) | 365日分のリスト | Medium | test_compute_target_dates_large_days |

### 2.3 降順ソート確認

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 14 | リストの順序確認 | 正常系 | days=5, base_date=date(2024,1,15) | リストが降順（新しい順） | High | test_compute_target_dates_descending_order |

---

## 3. target_dates_set 関数のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 15 | set型で返される | 正常系 | days=3, base_date=date(2024,1,15) | set型で3要素 | High | test_target_dates_set_returns_set |
| 16 | compute_target_datesと同じ内容 | 正常系 | days=5, base_date=date(2024,1,15) | compute_target_datesの結果と一致 | High | test_target_dates_set_matches_compute |
| 17 | 重複がないことを確認 | 正常系 | days=3, base_date=date(2024,1,15) | set要素数=3 | Medium | test_target_dates_set_no_duplicates |

---

## 4. normalize_datetime_to_local 関数のテスト

### 4.1 タイムゾーン変換

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 18 | UTC→JST変換 | 正常系 | datetime(2024,1,15,10,30, tzinfo=UTC) | datetime(2024,1,15,19,30, tzinfo=JST) | High | test_normalize_datetime_utc_to_jst |
| 19 | JST→JST（変換なし） | 正常系 | datetime(2024,1,15,10,30, tzinfo=JST) | datetime(2024,1,15,10,30, tzinfo=JST) | High | test_normalize_datetime_jst_to_jst |
| 20 | naiveなdatetime | 正常系 | datetime(2024,1,15,10,30)（tzinfo=None） | datetime(2024,1,15,10,30, tzinfo=JST) | High | test_normalize_datetime_naive |
| 21 | マイナスタイムゾーン | 正常系 | datetime(2024,1,15,10,30, tzinfo=UTC-5) | JSTに変換される | High | test_normalize_datetime_negative_timezone |

### 4.2 境界値・エッジケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 22 | None入力 | 境界値 | dt=None | Noneが返される | High | test_normalize_datetime_none_input |
| 23 | UTC深夜0時 | 境界値 | datetime(2024,1,15,0,0,0, tzinfo=UTC) | datetime(2024,1,15,9,0,0, tzinfo=JST) | High | test_normalize_datetime_utc_midnight |
| 24 | JST深夜0時 | 境界値 | datetime(2024,1,15,0,0,0, tzinfo=JST) | datetime(2024,1,15,0,0,0, tzinfo=JST) | High | test_normalize_datetime_jst_midnight |
| 25 | 日付境界（UTC 23:59:59） | 境界値 | datetime(2024,1,15,23,59,59, tzinfo=UTC) | datetime(2024,1,16,8,59,59, tzinfo=JST) | High | test_normalize_datetime_date_boundary |
| 26 | 日をまたぐ変換 | 正常系 | datetime(2024,1,15,20,0,0, tzinfo=UTC) | datetime(2024,1,16,5,0,0, tzinfo=JST) | High | test_normalize_datetime_cross_day |

---

## 5. is_within_target_dates 関数のテスト

### 5.1 基本的な動作

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 27 | 範囲内の日付 | 正常系 | dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates={date(2024,1,15)} | True | High | test_is_within_target_dates_in_range |
| 28 | 範囲外の日付 | 正常系 | dt=datetime(2024,1,16,10,0, tzinfo=JST), target_dates={date(2024,1,15)} | False | High | test_is_within_target_dates_out_of_range |
| 29 | 複数target_dates内 | 正常系 | dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates={date(2024,1,14), date(2024,1,15), date(2024,1,16)} | True | High | test_is_within_target_dates_multiple_dates |
| 30 | UTC時刻の判定 | 正常系 | dt=datetime(2024,1,15,10,0, tzinfo=UTC), target_dates={date(2024,1,15)} | JST変換後に判定される | High | test_is_within_target_dates_utc_datetime |

### 5.2 境界値・エッジケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 31 | None datetime | 境界値 | dt=None, target_dates={date(2024,1,15)} | False | High | test_is_within_target_dates_none_datetime |
| 32 | 空のtarget_dates | 境界値 | dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates=set() | False | High | test_is_within_target_dates_empty_target_dates |
| 33 | 空リストのtarget_dates | 境界値 | dt=datetime(2024,1,15,10,0, tzinfo=JST), target_dates=[] | False | High | test_is_within_target_dates_empty_list |
| 34 | naive datetime | 正常系 | dt=datetime(2024,1,15,10,0)（tzinfo=None）, target_dates={date(2024,1,15)} | JST扱いでTrue | High | test_is_within_target_dates_naive_datetime |

### 5.3 日付境界のエッジケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 35 | JST深夜0時ちょうど | 境界値 | dt=datetime(2024,1,15,0,0,0, tzinfo=JST), target_dates={date(2024,1,15)} | True | High | test_is_within_target_dates_jst_midnight_start |
| 36 | JST深夜23:59:59 | 境界値 | dt=datetime(2024,1,15,23,59,59, tzinfo=JST), target_dates={date(2024,1,15)} | True | High | test_is_within_target_dates_jst_midnight_end |
| 37 | UTC時刻が日をまたぐケース | 境界値 | dt=datetime(2024,1,14,20,0,0, tzinfo=UTC)（JST 01/15 05:00）, target_dates={date(2024,1,15)} | True | High | test_is_within_target_dates_utc_crosses_day |
| 38 | UTC時刻が前日になるケース | 境界値 | dt=datetime(2024,1,15,2,0,0, tzinfo=UTC)（JST 01/15 11:00）, target_dates={date(2024,1,14)} | False | High | test_is_within_target_dates_utc_different_day |

### 5.4 複雑なケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 39 | タイムゾーンが異なる複数日付 | 正常系 | UTCとJSTの時刻、複数target_dates | 正しく判定される | Medium | test_is_within_target_dates_multiple_timezones |
| 40 | うるう日の判定 | 正常系 | dt=datetime(2024,2,29,10,0, tzinfo=JST), target_dates={date(2024,2,29)} | True | Medium | test_is_within_target_dates_leap_day |
| 41 | 年末年始の境界 | 境界値 | dt=datetime(2024,12,31,23,59,59, tzinfo=JST), target_dates={date(2024,12,31)} | True | Medium | test_is_within_target_dates_year_boundary |

---

## カバレッジ目標

- **行カバレッジ**: 95%以上
- **分岐カバレッジ**: 95%以上
- **関数カバレッジ**: 100%

## テストデータ例

```python
from datetime import date, datetime, timedelta, timezone

# タイムゾーン定義
UTC = timezone.utc
JST = timezone(timedelta(hours=9))

# 日付範囲テスト用
test_dates = [
    date(2024, 1, 15),
    date(2024, 1, 14),
    date(2024, 1, 13),
]

# datetime変換テスト用
test_datetimes = [
    datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    datetime(2024, 1, 15, 10, 30, 0, tzinfo=JST),
    datetime(2024, 1, 15, 10, 30, 0),  # naive
]

# 境界値テスト用
boundary_cases = [
    datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST),  # 深夜0時
    datetime(2024, 1, 15, 23, 59, 59, tzinfo=JST),  # 23:59:59
    datetime(2024, 1, 14, 15, 0, 0, tzinfo=UTC),  # UTC→JST翌日
]
```

## 注意事項

- すべてのタイムゾーン処理はJST（UTC+9）基準
- naive datetimeはJST扱い
- days < 1 の場合は1として扱う
- target_datesが空の場合はFalseを返す
- 日付の降順ソート（新しい順）を確認
