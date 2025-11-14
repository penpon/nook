# feed_utils テスト仕様書

## 概要
`nook/common/feed_utils.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- 日付パース処理の多様な入力形式をカバー
- エッジケース（None、空文字列、無効な値）を網羅
- struct_time、ISO形式、RFC 2822形式のすべてをテスト

---

## 1. `_get_entry_value` 関数のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | 属性を持つオブジェクトから取得 | 正常系 | hasattr()=True, field="title" | getattr()で値が返される | High | test_get_entry_value_from_object_with_attribute |
| 2 | 辞書から取得 | 正常系 | dict型のentry, field="title" | entry.get("title")の値が返される | High | test_get_entry_value_from_dict |
| 3 | 属性がないオブジェクト | 正常系 | hasattr()=False, field="missing" | Noneが返される | High | test_get_entry_value_object_without_attribute |
| 4 | 辞書にキーがない | 正常系 | dict型のentry, field="missing" | Noneが返される | High | test_get_entry_value_dict_without_key |
| 5 | None値の取得 | 境界値 | entry.field=None | Noneが返される | Medium | test_get_entry_value_none_value |
| 6 | 空文字列の取得 | 境界値 | entry.field="" | ""が返される | Medium | test_get_entry_value_empty_string |

---

## 2. `_parse_iso_datetime` 関数のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 7 | ISO 8601形式（Z付き） | 正常系 | "2024-01-15T10:30:00Z" | UTC→JST変換され、tzinfo=Noneのdatetime | High | test_parse_iso_datetime_with_z_suffix |
| 8 | ISO 8601形式（タイムゾーンオフセット付き） | 正常系 | "2024-01-15T10:30:00+00:00" | UTC→JST変換され、tzinfo=Noneのdatetime | High | test_parse_iso_datetime_with_timezone_offset |
| 9 | ISO 8601形式（タイムゾーンなし） | 正常系 | "2024-01-15T10:30:00" | JST+9時間のdatetime | High | test_parse_iso_datetime_naive |
| 10 | 日付のみ（YYYY-MM-DD） | 境界値 | "2024-01-15" | "2024-01-15T00:00:00"として解釈、JST+9 | High | test_parse_iso_datetime_date_only |
| 11 | 空文字列 | 境界値 | "" | Noneが返される | High | test_parse_iso_datetime_empty_string |
| 12 | 空白のみ | 境界値 | "   " | Noneが返される | High | test_parse_iso_datetime_whitespace_only |
| 13 | 不正なISO形式 | 異常系 | "invalid-date" | Noneが返される（ValueErrorをキャッチ） | High | test_parse_iso_datetime_invalid_format |
| 14 | Noneではなく無効な日付 | 異常系 | "2024-13-40T99:99:99" | Noneが返される | Medium | test_parse_iso_datetime_invalid_date_values |
| 15 | タイムゾーン+09:00（JST） | 正常系 | "2024-01-15T10:30:00+09:00" | UTC変換後+9時間でJST | High | test_parse_iso_datetime_jst_timezone |
| 16 | マイナスタイムゾーン | 正常系 | "2024-01-15T10:30:00-05:00" | UTC変換後+9時間でJST | Medium | test_parse_iso_datetime_negative_timezone |
| 17 | マイクロ秒付きISO形式 | 正常系 | "2024-01-15T10:30:00.123456Z" | 正しく解析される | Medium | test_parse_iso_datetime_with_microseconds |

---

## 3. `parse_entry_datetime` 関数のテスト

### 3.1 struct_time フィールドからのパース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 18 | published_parsedフィールド | 正常系 | entry.published_parsed=struct_time | UTC→JST変換されたdatetime | High | test_parse_entry_datetime_from_published_parsed |
| 19 | updated_parsedフィールド | 正常系 | entry.updated_parsed=struct_time | UTC→JST変換されたdatetime | High | test_parse_entry_datetime_from_updated_parsed |
| 20 | created_parsedフィールド | 正常系 | entry.created_parsed=struct_time | UTC→JST変換されたdatetime | Medium | test_parse_entry_datetime_from_created_parsed |
| 21 | issued_parsedフィールド | 正常系 | entry.issued_parsed=struct_time | UTC→JST変換されたdatetime | Medium | test_parse_entry_datetime_from_issued_parsed |
| 22 | 不正なstruct_time（TypeError） | 異常系 | entry.published_parsed=invalid_value | 次のフィールドにフォールバック | High | test_parse_entry_datetime_struct_time_type_error |
| 23 | 不正なstruct_time（ValueError） | 異常系 | calendar.timegmがValueError | 次のフィールドにフォールバック | High | test_parse_entry_datetime_struct_time_value_error |

### 3.2 文字列フィールドからのパース（RFC 2822形式）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 24 | publishedフィールド（RFC 2822） | 正常系 | entry.published="Mon, 15 Jan 2024 10:30:00 GMT" | parsedate_to_datetimeで解析、JST変換 | High | test_parse_entry_datetime_from_published_rfc2822 |
| 25 | updatedフィールド（RFC 2822） | 正常系 | entry.updated="Mon, 15 Jan 2024 10:30:00 +0000" | parsedate_to_datetimeで解析、JST変換 | High | test_parse_entry_datetime_from_updated_rfc2822 |
| 26 | createdフィールド（RFC 2822） | 正常系 | entry.created="Mon, 15 Jan 2024 10:30:00 GMT" | parsedate_to_datetimeで解析、JST変換 | Medium | test_parse_entry_datetime_from_created_rfc2822 |
| 27 | issuedフィールド（RFC 2822） | 正常系 | entry.issued="Mon, 15 Jan 2024 10:30:00 GMT" | parsedate_to_datetimeで解析、JST変換 | Medium | test_parse_entry_datetime_from_issued_rfc2822 |
| 28 | タイムゾーンなしRFC 2822 | 正常系 | "Mon, 15 Jan 2024 10:30:00" | naive→JST+9時間 | High | test_parse_entry_datetime_rfc2822_naive |
| 29 | RFC 2822パース失敗（TypeError） | 異常系 | parsedate_to_datetimeがTypeError | ISO形式へフォールバック | High | test_parse_entry_datetime_rfc2822_type_error |
| 30 | RFC 2822パース失敗（ValueError） | 異常系 | parsedate_to_datetimeがValueError | ISO形式へフォールバック | High | test_parse_entry_datetime_rfc2822_value_error |

### 3.3 文字列フィールドからのパース（ISO形式フォールバック）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 31 | publishedフィールド（ISO形式） | 正常系 | entry.published="2024-01-15T10:30:00Z" | _parse_iso_datetimeで解析、JST変換 | High | test_parse_entry_datetime_from_published_iso |
| 32 | updatedフィールド（ISO形式） | 正常系 | entry.updated="2024-01-15T10:30:00Z" | _parse_iso_datetimeで解析、JST変換 | High | test_parse_entry_datetime_from_updated_iso |
| 33 | RFC 2822失敗後ISO成功 | 正常系 | parsedate失敗→ISO成功 | ISO形式で正しく解析される | High | test_parse_entry_datetime_fallback_to_iso |

### 3.4 境界値・エッジケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 34 | すべてのフィールドがNone | 境界値 | entry={}（すべてNone） | Noneが返される | High | test_parse_entry_datetime_all_fields_none |
| 35 | すべてのフィールドが空文字列 | 境界値 | entry={field: ""} | Noneが返される | High | test_parse_entry_datetime_all_fields_empty_string |
| 36 | 複数フィールド存在（優先度確認） | 正常系 | published_parsed + updated_parsed両方 | published_parsedが優先される | High | test_parse_entry_datetime_field_priority |
| 37 | 辞書型のentry | 正常系 | dict型、published="..." | 正しく解析される | High | test_parse_entry_datetime_dict_entry |
| 38 | オブジェクト型のentry | 正常系 | object型、hasattr()=True | 正しく解析される | High | test_parse_entry_datetime_object_entry |
| 39 | JST深夜0時のエッジケース | 境界値 | "2024-01-15T00:00:00+09:00" | 正しく変換される | Medium | test_parse_entry_datetime_jst_midnight |
| 40 | UTC深夜0時のエッジケース | 境界値 | "2024-01-15T00:00:00Z" | JST 09:00に変換される | Medium | test_parse_entry_datetime_utc_midnight |
| 41 | 夏時間タイムゾーン | 正常系 | "2024-06-15T10:30:00-04:00" (EDT) | UTC変換後JST | Medium | test_parse_entry_datetime_dst_timezone |
| 42 | 年末年始の境界 | 境界値 | "2024-12-31T23:59:59Z" | 正しく2025-01-01 08:59:59 JST | Medium | test_parse_entry_datetime_year_boundary |

---

## カバレッジ目標

- **行カバレッジ**: 95%以上
- **分岐カバレッジ**: 95%以上
- **関数カバレッジ**: 100%

## テストデータ例

```python
# struct_time例
import time
struct_time_example = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))

# RFC 2822例
rfc2822_examples = [
    "Mon, 15 Jan 2024 10:30:00 GMT",
    "Mon, 15 Jan 2024 10:30:00 +0000",
    "Mon, 15 Jan 2024 10:30:00 +0900",
]

# ISO 8601例
iso_examples = [
    "2024-01-15T10:30:00Z",
    "2024-01-15T10:30:00+00:00",
    "2024-01-15T10:30:00+09:00",
    "2024-01-15",
]
```

## 注意事項

- すべてのdatetime比較はJST（UTC+9）基準
- tzinfo=Noneで返されることを確認
- エラーハンドリング時はNoneが返されることを確認
- 優先順位: struct_time > 文字列フィールド
- 文字列フィールド内の優先順位: published > updated > created > issued
