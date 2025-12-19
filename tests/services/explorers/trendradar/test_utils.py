"""TrendRadar共通ユーティリティのテスト.

このモジュールは、utils.py で提供されるユーティリティ関数のテストを行います。
"""

from datetime import datetime, timezone
from unittest.mock import patch

from bs4 import BeautifulSoup

from nook.services.explorers.trendradar.utils import (
    create_empty_soup,
    escape_markdown_text,
    escape_markdown_url,
    parse_popularity_score,
    parse_published_at,
    sanitize_prompt_input,
)


class TestCreateEmptySoup:
    """create_empty_soup関数のテスト。"""

    def test_returns_beautifulsoup_instance(self) -> None:
        """
        Given: 引数なし。
        When: create_empty_soup が呼ばれたとき。
        Then: BeautifulSoupインスタンスを返す。
        """
        result = create_empty_soup()
        assert isinstance(result, BeautifulSoup)

    def test_returns_empty_soup(self) -> None:
        """
        Given: 引数なし。
        When: create_empty_soup が呼ばれたとき。
        Then: 空のBeautifulSoupを返す。
        """
        result = create_empty_soup()
        assert str(result) == ""

    def test_returns_new_instance_each_time(self) -> None:
        """
        Given: 複数回の呼び出し。
        When: create_empty_soup が複数回呼ばれたとき。
        Then: 毎回新しいインスタンスを返す（副作用防止）。
        """
        soup1 = create_empty_soup()
        soup2 = create_empty_soup()
        assert soup1 is not soup2


class TestParsePopularityScore:
    """parse_popularity_score関数のテスト。"""

    def test_parses_int(self) -> None:
        """整数値を正しくパースする。"""
        assert parse_popularity_score(1000) == 1000.0

    def test_parses_float(self) -> None:
        """浮動小数点数を正しくパースする。"""
        assert parse_popularity_score(1234.56) == 1234.56

    def test_parses_string_number(self) -> None:
        """文字列の数値を正しくパースする。"""
        assert parse_popularity_score("5000") == 5000.0

    def test_parses_string_with_comma(self) -> None:
        """カンマ区切りの文字列を正しくパースする。"""
        assert parse_popularity_score("1,234,567") == 1234567.0

    def test_parses_string_with_plus_prefix(self) -> None:
        """プラス記号付きの文字列を正しくパースする。"""
        assert parse_popularity_score("+500") == 500.0

    def test_returns_zero_for_none(self) -> None:
        """Noneに対して0.0を返す。"""
        assert parse_popularity_score(None) == 0.0

    def test_returns_zero_for_invalid_string(self) -> None:
        """パース不可能な文字列に対して0.0を返す。"""
        assert parse_popularity_score("N/A") == 0.0
        assert parse_popularity_score("invalid") == 0.0

    def test_returns_zero_for_nan(self) -> None:
        """NaNに対して0.0を返す。"""
        assert parse_popularity_score(float("nan")) == 0.0

    def test_returns_zero_for_infinity(self) -> None:
        """Infinityに対して0.0を返す。"""
        assert parse_popularity_score(float("inf")) == 0.0
        assert parse_popularity_score(float("-inf")) == 0.0

    def test_handles_whitespace(self) -> None:
        """前後の空白を含む文字列を正しくパースする。"""
        assert parse_popularity_score("  1000  ") == 1000.0


class TestSanitizePromptInput:
    """sanitize_prompt_input関数のテスト。"""

    def test_returns_empty_for_empty_string(self) -> None:
        """空文字列に対して空文字列を返す。"""
        assert sanitize_prompt_input("") == ""

    def test_returns_empty_for_none_like(self) -> None:
        """Falsyな値に対して空文字列を返す。"""
        assert sanitize_prompt_input("") == ""

    def test_preserves_normal_text(self) -> None:
        """通常のテキストを保持する。"""
        text = "これはテストです"
        assert sanitize_prompt_input(text) == text

    def test_preserves_newlines_and_tabs(self) -> None:
        """改行とタブを保持する。"""
        text = "Line1\nLine2\tTabbed"
        assert "\n" in sanitize_prompt_input(text)
        assert "\t" in sanitize_prompt_input(text)

    def test_removes_control_characters(self) -> None:
        """制御文字を除去する。"""
        text = "Normal\x00Text\x1fWith\x7fControls"
        result = sanitize_prompt_input(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        # Note: \x7f (DEL) はCc制御文字なので除去される
        assert "NormalTextWithControls" in result

    def test_normalizes_excessive_newlines(self) -> None:
        """過度な改行を正規化する。"""
        text = "Line1\n\n\n\n\nLine2"
        result = sanitize_prompt_input(text)
        assert "\n\n\n" not in result
        assert "Line1\n\nLine2" == result

    def test_truncates_to_max_length(self) -> None:
        """最大長を超えた場合に切り捨てる。"""
        text = "a" * 600
        result = sanitize_prompt_input(text, max_length=500)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")

    def test_custom_max_length(self) -> None:
        """カスタム最大長が正しく動作する。"""
        text = "Test text for truncation"
        result = sanitize_prompt_input(text, max_length=10)
        assert len(result) == 13  # 10 + "..."
        assert result == "Test text ..."

    def test_strips_whitespace(self) -> None:
        """前後の空白を除去する。"""
        text = "  Text with spaces  "
        result = sanitize_prompt_input(text)
        assert result == "Text with spaces"


class TestEscapeMarkdownText:
    """escape_markdown_text関数のテスト。"""

    def test_escapes_html_special_chars(self) -> None:
        """HTML特殊文字をエスケープする。"""
        text = "<script>alert('xss')</script>"
        result = escape_markdown_text(text)
        assert "<" not in result
        assert ">" not in result
        assert "&lt;script&gt;" in result

    def test_escapes_ampersand(self) -> None:
        """アンパサンドをエスケープする。"""
        text = "A & B"
        result = escape_markdown_text(text)
        assert "&amp;" in result

    def test_escapes_brackets(self) -> None:
        """角括弧をエスケープする。"""
        text = "[Important] Notice"
        result = escape_markdown_text(text)
        assert "\\[" in result
        assert "\\]" in result

    def test_preserves_normal_text(self) -> None:
        """通常のテキストを保持する。"""
        text = "Normal text without special chars"
        result = escape_markdown_text(text)
        assert result == text


class TestEscapeMarkdownUrl:
    """escape_markdown_url関数のテスト。"""

    def test_escapes_parentheses(self) -> None:
        """括弧をエスケープする。"""
        url = "https://example.com/path(with)parens"
        result = escape_markdown_url(url)
        assert "\\(" in result
        assert "\\)" in result

    def test_escapes_brackets(self) -> None:
        """角括弧をエスケープする。"""
        url = "https://example.com/path[with]brackets"
        result = escape_markdown_url(url)
        assert "\\[" in result
        assert "\\]" in result

    def test_preserves_normal_url(self) -> None:
        """通常のURLを保持する。"""
        url = "https://example.com/normal/path?query=value"
        result = escape_markdown_url(url)
        assert result == url


class TestParsePublishedAt:
    """parse_published_at関数のテスト。"""

    def test_parses_iso_format(self) -> None:
        """ISO形式の日時文字列を正しくパースする。"""
        item = {"published_at": "2024-01-15T10:30:00Z"}
        result = parse_published_at(item)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.tzinfo is not None

    def test_parses_epoch_timestamp(self) -> None:
        """エポックタイムスタンプを正しくパースする。"""
        # 2024-01-01 00:00:00 UTC
        item = {"timestamp": 1704067200}
        result = parse_published_at(item)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_parses_millisecond_epoch(self) -> None:
        """ミリ秒エポックタイムスタンプを正しくパースする。"""
        # 2024-01-01 00:00:00 UTC (in milliseconds)
        item = {"timestamp": 1704067200000}
        result = parse_published_at(item)
        assert result.year == 2024
        assert result.month == 1

    def test_parses_epoch_zero(self) -> None:
        """エポック0を正しくパースする。"""
        item = {"timestamp": 0}
        result = parse_published_at(item)
        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1

    def test_field_priority_order(self) -> None:
        """フィールドの優先順位を正しく処理する。"""
        # time が最優先
        item = {
            "time": "2024-06-15T10:00:00Z",
            "published_at": "2024-01-01T00:00:00Z",
            "timestamp": 1672531200,
        }
        result = parse_published_at(item)
        assert result.month == 6

        # published_at が2番目
        item2 = {
            "published_at": "2024-03-15T10:00:00Z",
            "timestamp": 1672531200,
        }
        result2 = parse_published_at(item2)
        assert result2.month == 3

    def test_fallback_to_current_time_for_empty_item(self) -> None:
        """空のアイテムに対して現在時刻にフォールバックする。"""
        fixed_now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("nook.services.explorers.trendradar.utils.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.fromtimestamp = datetime.fromtimestamp

            result = parse_published_at({})

        assert result.year == 2024
        assert result.month == 6

    def test_fallback_for_invalid_date_string(self) -> None:
        """パース不可能な文字列に対してフォールバックする。"""
        fixed_now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("nook.services.explorers.trendradar.utils.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.fromtimestamp = datetime.fromtimestamp

            result = parse_published_at({"published_at": "not-a-date"})

        assert result.year == 2024

    def test_adds_utc_timezone_if_missing(self) -> None:
        """タイムゾーンがない場合UTCを追加する。"""
        item = {"published_at": "2024-01-15T10:30:00"}
        result = parse_published_at(item)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_handles_very_large_epoch(self) -> None:
        """非常に大きなエポック値にフォールバックする。"""
        item = {
            "timestamp": 9999999999999999,  # Far future
            "pub_date": "2024-05-01T00:00:00Z",
        }
        result = parse_published_at(item)
        # Should fall back to pub_date
        assert result.year == 2024
        assert result.month == 5
