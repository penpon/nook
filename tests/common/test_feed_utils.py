"""nook/common/feed_utils.py のテスト"""

from __future__ import annotations

import calendar
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.feed_utils import (
    _get_entry_value,
    _parse_iso_datetime,
    parse_entry_datetime,
)


# ================================================================================
# 1. _get_entry_value 関数のテスト
# ================================================================================


@pytest.mark.unit
def test_get_entry_value_from_object_with_attribute():
    """
    Given: 属性を持つオブジェクトとフィールド名
    When: _get_entry_valueを呼び出す
    Then: getattr()で値が返される
    """
    entry = Mock()
    entry.title = "Test Title"
    result = _get_entry_value(entry, "title")
    assert result == "Test Title"


@pytest.mark.unit
def test_get_entry_value_from_dict():
    """
    Given: 辞書型のentryとフィールド名
    When: _get_entry_valueを呼び出す
    Then: entry.get()で値が返される
    """
    entry = {"title": "Test Title", "author": "Test Author"}
    result = _get_entry_value(entry, "title")
    assert result == "Test Title"


@pytest.mark.unit
def test_get_entry_value_object_without_attribute():
    """
    Given: 属性を持たないオブジェクトとフィールド名
    When: _get_entry_valueを呼び出す
    Then: Noneが返される
    """
    entry = Mock(spec=[])
    result = _get_entry_value(entry, "missing_field")
    assert result is None


@pytest.mark.unit
def test_get_entry_value_dict_without_key():
    """
    Given: キーを持たない辞書とフィールド名
    When: _get_entry_valueを呼び出す
    Then: Noneが返される
    """
    entry = {"title": "Test"}
    result = _get_entry_value(entry, "missing_key")
    assert result is None


@pytest.mark.unit
def test_get_entry_value_none_value():
    """
    Given: None値を持つフィールド
    When: _get_entry_valueを呼び出す
    Then: Noneが返される
    """
    entry = {"title": None}
    result = _get_entry_value(entry, "title")
    assert result is None


@pytest.mark.unit
def test_get_entry_value_empty_string():
    """
    Given: 空文字列を持つフィールド
    When: _get_entry_valueを呼び出す
    Then: 空文字列が返される
    """
    entry = {"title": ""}
    result = _get_entry_value(entry, "title")
    assert result == ""


# ================================================================================
# 2. _parse_iso_datetime 関数のテスト
# ================================================================================


@pytest.mark.unit
def test_parse_iso_datetime_with_z_suffix():
    """
    Given: ISO 8601形式（Z付き）の日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: UTC→JST変換され、tzinfo=Noneのdatetimeが返される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00Z")
    # UTC 10:30 + 9h = JST 19:30
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_with_timezone_offset():
    """
    Given: ISO 8601形式（タイムゾーンオフセット付き）の日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: UTC→JST変換され、tzinfo=Noneのdatetimeが返される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00+00:00")
    # UTC 10:30 + 9h = JST 19:30
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_naive():
    """
    Given: ISO 8601形式（タイムゾーンなし）の日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: JST+9時間のdatetimeが返される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00")
    # Naive 10:30 + 9h = 19:30
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_date_only():
    """
    Given: 日付のみ（YYYY-MM-DD）の文字列
    When: _parse_iso_datetimeを呼び出す
    Then: 00:00:00として解釈され、JST+9時間が返される
    """
    result = _parse_iso_datetime("2024-01-15")
    # "2024-01-15T00:00:00" + 9h = 09:00:00
    expected = datetime(2024, 1, 15, 9, 0, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_empty_string():
    """
    Given: 空文字列
    When: _parse_iso_datetimeを呼び出す
    Then: Noneが返される
    """
    result = _parse_iso_datetime("")
    assert result is None


@pytest.mark.unit
def test_parse_iso_datetime_whitespace_only():
    """
    Given: 空白のみの文字列
    When: _parse_iso_datetimeを呼び出す
    Then: Noneが返される
    """
    result = _parse_iso_datetime("   ")
    assert result is None


@pytest.mark.unit
def test_parse_iso_datetime_invalid_format():
    """
    Given: 不正なISO形式の文字列
    When: _parse_iso_datetimeを呼び出す
    Then: Noneが返される（ValueErrorをキャッチ）
    """
    result = _parse_iso_datetime("invalid-date-format")
    assert result is None


@pytest.mark.unit
def test_parse_iso_datetime_invalid_date_values():
    """
    Given: 無効な日付値の文字列
    When: _parse_iso_datetimeを呼び出す
    Then: Noneが返される
    """
    result = _parse_iso_datetime("2024-13-40T99:99:99")
    assert result is None


@pytest.mark.unit
def test_parse_iso_datetime_jst_timezone():
    """
    Given: タイムゾーン+09:00（JST）の日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: UTC変換後+9時間でJSTが返される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00+09:00")
    # JST 10:30 -> UTC 01:30 -> JST 10:30 (元に戻る)
    expected = datetime(2024, 1, 15, 10, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_negative_timezone():
    """
    Given: マイナスタイムゾーンの日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: UTC変換後+9時間でJSTが返される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00-05:00")
    # EST 10:30 -> UTC 15:30 -> JST 00:30 (next day)
    expected = datetime(2024, 1, 16, 0, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_iso_datetime_with_microseconds():
    """
    Given: マイクロ秒付きISO形式の日付文字列
    When: _parse_iso_datetimeを呼び出す
    Then: 正しく解析される
    """
    result = _parse_iso_datetime("2024-01-15T10:30:00.123456Z")
    # UTC 10:30:00.123456 + 9h = JST 19:30:00.123456
    expected = datetime(2024, 1, 15, 19, 30, 0, 123456)
    assert result == expected
    assert result.tzinfo is None


# ================================================================================
# 3. parse_entry_datetime 関数のテスト
# ================================================================================

# 3.1 struct_time フィールドからのパース


@pytest.mark.unit
def test_parse_entry_datetime_from_published_parsed():
    """
    Given: published_parsedフィールドを持つentry
    When: parse_entry_datetimeを呼び出す
    Then: UTC→JST変換されたdatetimeが返される
    """
    # 2024-01-15 10:30:00 UTC
    struct_time_value = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
    entry = {"published_parsed": struct_time_value}

    result = parse_entry_datetime(entry)

    # UTC 10:30 + 9h = JST 19:30
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected
    assert result.tzinfo is None


@pytest.mark.unit
def test_parse_entry_datetime_from_updated_parsed():
    """
    Given: updated_parsedフィールドを持つentry
    When: parse_entry_datetimeを呼び出す
    Then: UTC→JST変換されたdatetimeが返される
    """
    struct_time_value = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
    entry = {"updated_parsed": struct_time_value}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_created_parsed():
    """
    Given: created_parsedフィールドを持つentry
    When: parse_entry_datetimeを呼び出す
    Then: UTC→JST変換されたdatetimeが返される
    """
    struct_time_value = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
    entry = {"created_parsed": struct_time_value}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_issued_parsed():
    """
    Given: issued_parsedフィールドを持つentry
    When: parse_entry_datetimeを呼び出す
    Then: UTC→JST変換されたdatetimeが返される
    """
    struct_time_value = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
    entry = {"issued_parsed": struct_time_value}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_struct_time_type_error():
    """
    Given: 不正なstruct_time値（TypeError発生）
    When: parse_entry_datetimeを呼び出す
    Then: 次のフィールドにフォールバック
    """
    entry = {
        "published_parsed": "invalid_struct_time",  # TypeError
        "published": "2024-01-15T10:30:00Z",  # フォールバック先
    }

    result = parse_entry_datetime(entry)

    # フォールバック成功
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_struct_time_value_error():
    """
    Given: 不正なstruct_time値（ValueError発生）
    When: parse_entry_datetimeを呼び出す
    Then: 次のフィールドにフォールバック
    """
    # 不正なstruct_time（月が13）
    invalid_struct_time = time.struct_time((2024, 13, 15, 10, 30, 0, 0, 15, 0))
    entry = {
        "published_parsed": invalid_struct_time,
        "published": "2024-01-15T10:30:00Z",
    }

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


# 3.2 文字列フィールドからのパース（RFC 2822形式）


@pytest.mark.unit
def test_parse_entry_datetime_from_published_rfc2822():
    """
    Given: publishedフィールド（RFC 2822形式）
    When: parse_entry_datetimeを呼び出す
    Then: parsedate_to_datetimeで解析、JST変換される
    """
    entry = {"published": "Mon, 15 Jan 2024 10:30:00 GMT"}

    result = parse_entry_datetime(entry)

    # GMT 10:30 + 9h = JST 19:30
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_updated_rfc2822():
    """
    Given: updatedフィールド（RFC 2822形式）
    When: parse_entry_datetimeを呼び出す
    Then: parsedate_to_datetimeで解析、JST変換される
    """
    entry = {"updated": "Mon, 15 Jan 2024 10:30:00 +0000"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_created_rfc2822():
    """
    Given: createdフィールド（RFC 2822形式）
    When: parse_entry_datetimeを呼び出す
    Then: parsedate_to_datetimeで解析、JST変換される
    """
    entry = {"created": "Mon, 15 Jan 2024 10:30:00 GMT"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_issued_rfc2822():
    """
    Given: issuedフィールド（RFC 2822形式）
    When: parse_entry_datetimeを呼び出す
    Then: parsedate_to_datetimeで解析、JST変換される
    """
    entry = {"issued": "Mon, 15 Jan 2024 10:30:00 GMT"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_rfc2822_naive():
    """
    Given: タイムゾーンなしRFC 2822形式
    When: parse_entry_datetimeを呼び出す
    Then: naive→JST+9時間が返される
    """
    # RFC 2822でタイムゾーンなしはemail.utilsでは解析できないのでISO形式に頼る
    entry = {"published": "2024-01-15T10:30:00"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_rfc2822_type_error():
    """
    Given: parsedate_to_datetimeがTypeError発生
    When: parse_entry_datetimeを呼び出す
    Then: ISO形式へフォールバック
    """
    entry = {"published": None}  # TypeErrorを引き起こす

    result = parse_entry_datetime(entry)

    assert result is None


@pytest.mark.unit
def test_parse_entry_datetime_rfc2822_value_error():
    """
    Given: parsedate_to_datetimeがValueError発生
    When: parse_entry_datetimeを呼び出す
    Then: ISO形式へフォールバック
    """
    # 不正な日付文字列（RFC 2822としてもISOとしても失敗）
    entry = {"published": "invalid date string"}

    result = parse_entry_datetime(entry)

    assert result is None


# 3.3 文字列フィールドからのパース（ISO形式フォールバック）


@pytest.mark.unit
def test_parse_entry_datetime_from_published_iso():
    """
    Given: publishedフィールド（ISO形式）
    When: parse_entry_datetimeを呼び出す
    Then: _parse_iso_datetimeで解析、JST変換される
    """
    entry = {"published": "2024-01-15T10:30:00Z"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_from_updated_iso():
    """
    Given: updatedフィールド（ISO形式）
    When: parse_entry_datetimeを呼び出す
    Then: _parse_iso_datetimeで解析、JST変換される
    """
    entry = {"updated": "2024-01-15T10:30:00Z"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_fallback_to_iso():
    """
    Given: RFC 2822解析失敗後、ISO形式で成功
    When: parse_entry_datetimeを呼び出す
    Then: ISO形式で正しく解析される
    """
    # email.utilsで解析できないがISO形式としては有効
    entry = {"published": "2024-01-15T10:30:00+09:00"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 10, 30, 0)
    assert result == expected


# 3.4 境界値・エッジケース


@pytest.mark.unit
def test_parse_entry_datetime_all_fields_none():
    """
    Given: すべてのフィールドがNone
    When: parse_entry_datetimeを呼び出す
    Then: Noneが返される
    """
    entry = {
        "published_parsed": None,
        "updated_parsed": None,
        "created_parsed": None,
        "issued_parsed": None,
        "published": None,
        "updated": None,
        "created": None,
        "issued": None,
    }

    result = parse_entry_datetime(entry)

    assert result is None


@pytest.mark.unit
def test_parse_entry_datetime_all_fields_empty_string():
    """
    Given: すべてのフィールドが空文字列
    When: parse_entry_datetimeを呼び出す
    Then: Noneが返される
    """
    entry = {
        "published": "",
        "updated": "",
        "created": "",
        "issued": "",
    }

    result = parse_entry_datetime(entry)

    assert result is None


@pytest.mark.unit
def test_parse_entry_datetime_field_priority():
    """
    Given: 複数フィールド存在（優先度確認）
    When: parse_entry_datetimeを呼び出す
    Then: published_parsedが優先される
    """
    struct_time_published = time.struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
    struct_time_updated = time.struct_time((2024, 1, 20, 15, 45, 0, 0, 20, 0))

    entry = {
        "published_parsed": struct_time_published,
        "updated_parsed": struct_time_updated,
    }

    result = parse_entry_datetime(entry)

    # published_parsedが優先される
    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_dict_entry():
    """
    Given: 辞書型のentry
    When: parse_entry_datetimeを呼び出す
    Then: 正しく解析される
    """
    entry = {"published": "2024-01-15T10:30:00Z"}

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_object_entry():
    """
    Given: オブジェクト型のentry
    When: parse_entry_datetimeを呼び出す
    Then: 正しく解析される
    """
    entry = Mock()
    entry.published = "2024-01-15T10:30:00Z"

    result = parse_entry_datetime(entry)

    expected = datetime(2024, 1, 15, 19, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_jst_midnight():
    """
    Given: JST深夜0時のエッジケース
    When: parse_entry_datetimeを呼び出す
    Then: 正しく変換される
    """
    entry = {"published": "2024-01-15T00:00:00+09:00"}

    result = parse_entry_datetime(entry)

    # JST 00:00 -> UTC 15:00 (prev day) -> JST 00:00
    expected = datetime(2024, 1, 15, 0, 0, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_utc_midnight():
    """
    Given: UTC深夜0時のエッジケース
    When: parse_entry_datetimeを呼び出す
    Then: JST 09:00に変換される
    """
    entry = {"published": "2024-01-15T00:00:00Z"}

    result = parse_entry_datetime(entry)

    # UTC 00:00 + 9h = JST 09:00
    expected = datetime(2024, 1, 15, 9, 0, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_dst_timezone():
    """
    Given: 夏時間タイムゾーン
    When: parse_entry_datetimeを呼び出す
    Then: UTC変換後JSTが返される
    """
    entry = {"published": "2024-06-15T10:30:00-04:00"}

    result = parse_entry_datetime(entry)

    # EDT 10:30 -> UTC 14:30 -> JST 23:30
    expected = datetime(2024, 6, 15, 23, 30, 0)
    assert result == expected


@pytest.mark.unit
def test_parse_entry_datetime_year_boundary():
    """
    Given: 年末年始の境界
    When: parse_entry_datetimeを呼び出す
    Then: 正しく2025-01-01 08:59:59 JSTが返される
    """
    entry = {"published": "2024-12-31T23:59:59Z"}

    result = parse_entry_datetime(entry)

    # UTC 23:59:59 + 9h = JST 08:59:59 (next day)
    expected = datetime(2025, 1, 1, 8, 59, 59)
    assert result == expected
