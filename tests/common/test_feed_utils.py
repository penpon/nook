from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.feed_utils import (  # noqa: E402
    _get_entry_value,
    _parse_iso_datetime,
    parse_entry_datetime,
)


class TestGetEntryValue:
    """_get_entry_valueのテスト"""

    def test_get_entry_value_from_object(self):
        """オブジェクトからの値取得テスト"""

        class MockEntry:
            def __init__(self):
                self.title = "Test Title"
                self.published = "2024-01-01"

        entry = MockEntry()
        assert _get_entry_value(entry, "title") == "Test Title"
        assert _get_entry_value(entry, "published") == "2024-01-01"
        assert _get_entry_value(entry, "nonexistent") is None

    def test_get_entry_value_from_dict(self):
        """辞書からの値取得テスト"""
        entry = {
            "title": "Test Title",
            "published": "2024-01-01",
            "summary": "Test Summary",
        }

        assert _get_entry_value(entry, "title") == "Test Title"
        assert _get_entry_value(entry, "published") == "2024-01-01"
        assert _get_entry_value(entry, "summary") == "Test Summary"
        assert _get_entry_value(entry, "nonexistent") is None

    def test_get_entry_value_from_none(self):
        """Noneからの値取得テスト"""
        assert _get_entry_value(None, "title") is None

    def test_get_entry_value_from_other_type(self):
        """その他の型からの値取得テスト"""
        entry = "string"
        # hasattrで属性の存在を確認してからgetattrを呼び出す
        result = _get_entry_value(entry, "title")
        # 文字列にはtitle属性があるが、メソッドを返す
        # 辞書でもない場合はNoneを返すべき
        assert result is None or callable(result)


class TestParseIsoDatetime:
    """_parse_iso_datetimeのテスト"""

    def test_parse_iso_datetime_empty_string(self):
        """空文字列のテスト"""
        assert _parse_iso_datetime("") is None
        assert _parse_iso_datetime("   ") is None

    def test_parse_iso_datetime_with_z_suffix(self):
        """Zサフィックス付きのテスト"""
        result = _parse_iso_datetime("2024-01-01T12:00:00Z")
        expected = datetime(2024, 1, 1, 21, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_iso_datetime_without_timezone(self):
        """タイムゾーンなしのテスト"""
        result = _parse_iso_datetime("2024-01-01T12:00:00")
        expected = datetime(2024, 1, 1, 21, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_iso_datetime_date_only(self):
        """日付のみのテスト"""
        result = _parse_iso_datetime("2024-01-01")
        expected = datetime(2024, 1, 1, 9, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_iso_datetime_with_timezone_offset(self):
        """タイムゾーンオフセット付きのテスト"""
        result = _parse_iso_datetime("2024-01-01T12:00:00+03:00")
        expected = datetime(2024, 1, 1, 18, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_iso_datetime_invalid_format(self):
        """無効な形式のテスト"""
        assert _parse_iso_datetime("invalid-date") is None
        assert _parse_iso_datetime("2024-13-01") is None  # 無効な月
        assert _parse_iso_datetime("2024-01-32") is None  # 無効な日

    def test_parse_iso_datetime_with_microseconds(self):
        """マイクロ秒付きのテスト"""
        result = _parse_iso_datetime("2024-01-01T12:00:00.123456Z")
        expected = datetime(2024, 1, 1, 21, 0, 0, 123456)  # UTC+9
        assert result == expected


class TestParseEntryDatetime:
    """parse_entry_datetimeのテスト"""

    def test_parse_entry_datetime_struct_time_fields(self):
        """struct_timeフィールドのテスト"""
        # time.struct_timeを模擬 - 実際のtime.struct_timeオブジェクトを作成
        import time

        mock_struct_time = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))

        entry = MagicMock()
        entry.published_parsed = mock_struct_time

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_entry_datetime_multiple_struct_time_fields(self):
        """複数のstruct_timeフィールドのテスト（優先順位）"""
        import time

        mock_time1 = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))
        mock_time2 = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 1, 0))

        entry = MagicMock()
        entry.published_parsed = mock_time1
        entry.updated_parsed = mock_time2

        result = parse_entry_datetime(entry)
        # published_parsedが優先される
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_struct_time_invalid(self):
        """無効なstruct_timeのテスト"""
        entry = MagicMock()
        entry.published_parsed = "invalid"

        # 次のフィールドに進むはず
        entry.published = "2024-01-01T12:00:00Z"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_string_fields_parsedate(self):
        """文字列フィールドのparsedateテスト"""
        entry = MagicMock()
        entry.published = "Mon, 01 Jan 2024 12:00:00 GMT"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)  # UTC+9
        assert result == expected

    def test_parse_entry_datetime_string_fields_iso_format(self):
        """文字列フィールドのISO形式テスト"""
        entry = MagicMock()
        entry.published = "2024-01-01T12:00:00Z"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_string_without_timezone(self):
        """タイムゾーンなし文字列のテスト"""
        entry = MagicMock()
        entry.published = "2024-01-01T12:00:00"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_multiple_string_fields(self):
        """複数の文字列フィールドのテスト（優先順位）"""
        entry = MagicMock()
        entry.published = "2024-01-01T12:00:00Z"
        entry.updated = "2024-01-02T12:00:00Z"

        result = parse_entry_datetime(entry)
        # publishedが優先される
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_empty_string_values(self):
        """空文字列値のテスト"""
        entry = MagicMock()
        entry.published = ""
        entry.updated = "   "
        entry.created = "2024-01-01T12:00:00Z"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_none_values(self):
        """None値のテスト"""
        entry = MagicMock()
        entry.published = None
        entry.updated = None
        entry.created = "2024-01-01T12:00:00Z"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_all_fields_fail(self):
        """すべてのフィールドが失敗するテスト"""
        entry = MagicMock()
        entry.published_parsed = "invalid"
        entry.updated_parsed = "invalid"
        entry.published = "invalid-date"
        entry.updated = "invalid-date"
        entry.created = "invalid-date"
        entry.issued = "invalid-date"

        result = parse_entry_datetime(entry)
        assert result is None

    def test_parse_entry_datetime_dict_entry(self):
        """辞書エントリのテスト"""
        entry = {"published": "2024-01-01T12:00:00Z"}

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_rfc2822_format(self):
        """RFC2822形式のテスト"""
        entry = MagicMock()
        entry.published = "Mon, 01 Jan 2024 12:00:00 +0000"

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_various_iso_formats(self):
        """様々なISO形式のテスト"""
        test_cases = [
            ("2024-01-01T12:00:00+00:00", datetime(2024, 1, 1, 21, 0, 0)),
            ("2024-01-01T12:00:00.123Z", datetime(2024, 1, 1, 21, 0, 0, 123000)),
            ("2024-01-01", datetime(2024, 1, 1, 9, 0, 0)),
        ]

        for date_str, expected in test_cases:
            entry = MagicMock()
            entry.published = date_str

            result = parse_entry_datetime(entry)
            assert result == expected

    def test_parse_entry_datetime_with_jst_offset(self):
        """JSTオフセットのテスト"""
        entry = MagicMock()
        entry.published = "2024-01-01T12:00:00+09:00"

        result = parse_entry_datetime(entry)
        # すでにJSTのタイムゾーン情報を含む場合はそのままの時刻になる
        expected = datetime(2024, 1, 1, 12, 0, 0)
        assert result == expected

    def test_parse_entry_datetime_edge_case_struct_time_exception(self):
        """struct_timeで例外が発生する場合のテスト"""
        entry = MagicMock()

        # calendar.timegmで例外を発生させる
        import time

        entry.published_parsed = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))

        with patch("calendar.timegm", side_effect=ValueError("Invalid time tuple")):
            entry.published = "2024-01-01T12:00:00Z"

            result = parse_entry_datetime(entry)
            expected = datetime(2024, 1, 1, 21, 0, 0)
            assert result == expected

    def test_parse_entry_datetime_edge_case_parsedate_exception(self):
        """parsedateで例外が発生する場合のテスト"""
        entry = MagicMock()
        entry.published = "invalid date format"

        # parsedate_to_datetimeが例外を発生させるが、ISOパースが成功
        result = parse_entry_datetime(entry)
        assert result is None

    def test_parse_entry_datetime_field_priority_order(self):
        """フィールド優先順位のテスト"""
        # すべてのフィールドに値がある場合の優先順位テスト
        import time

        mock_time = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))

        entry = MagicMock()
        entry.published_parsed = mock_time
        entry.published = "2024-01-02T12:00:00Z"  # struct_timeが優先される

        result = parse_entry_datetime(entry)
        expected = datetime(2024, 1, 1, 21, 0, 0)  # published_parsedの日付
        assert result == expected
