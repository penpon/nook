"""Tests for arxiv_summarizer helper functions.

This module tests the pure logic helper functions in arxiv_summarizer.py:
- remove_tex_backticks
- remove_outer_markdown_markers
- remove_outer_singlequotes
- _is_valid_body_line
"""

import pytest

from nook.services.arxiv_summarizer.arxiv_summarizer import (
    ArxivSummarizer,
    remove_outer_markdown_markers,
    remove_outer_singlequotes,
    remove_tex_backticks,
)


class TestRemoveTexBackticks:
    """Tests for remove_tex_backticks function."""

    def test_removes_backticks_from_tex_format(self) -> None:
        """
        Given: A string in TeX format with backticks wrapping dollar signs.
        When: remove_tex_backticks is called.
        Then: The outer backticks are removed, keeping the dollar signs.
        """
        text = "`$\\alpha + \\beta$`"
        result = remove_tex_backticks(text)
        assert result == "$\\alpha + \\beta$"

    def test_preserves_non_tex_format(self) -> None:
        """
        Given: A string that is not in TeX format.
        When: remove_tex_backticks is called.
        Then: The string is returned unchanged.
        """
        text = "This is a normal string"
        result = remove_tex_backticks(text)
        assert result == "This is a normal string"

    def test_preserves_backticks_without_dollar_signs(self) -> None:
        """
        Given: A string with backticks but no dollar signs.
        When: remove_tex_backticks is called.
        Then: The string is returned unchanged.
        """
        text = "`code block`"
        result = remove_tex_backticks(text)
        assert result == "`code block`"

    def test_preserves_dollar_signs_without_backticks(self) -> None:
        """
        Given: A string with dollar signs but no outer backticks.
        When: remove_tex_backticks is called.
        Then: The string is returned unchanged.
        """
        text = "$\\alpha + \\beta$"
        result = remove_tex_backticks(text)
        assert result == "$\\alpha + \\beta$"

    def test_handles_empty_string(self) -> None:
        """
        Given: An empty string.
        When: remove_tex_backticks is called.
        Then: An empty string is returned.
        """
        text = ""
        result = remove_tex_backticks(text)
        assert result == ""

    def test_handles_complex_tex_expression(self) -> None:
        """
        Given: A complex TeX expression with backticks.
        When: remove_tex_backticks is called.
        Then: The outer backticks are removed.
        """
        text = "`$\\frac{a}{b} + \\sum_{i=1}^{n} x_i$`"
        result = remove_tex_backticks(text)
        assert result == "$\\frac{a}{b} + \\sum_{i=1}^{n} x_i$"


class TestRemoveOuterMarkdownMarkers:
    """Tests for remove_outer_markdown_markers function."""

    def test_removes_markdown_code_block_markers(self) -> None:
        """
        Given: A string wrapped in markdown code block markers.
        When: remove_outer_markdown_markers is called.
        Then: The markers are removed, keeping the inner content.
        """
        text = "```markdown\n# Heading\n\nSome content\n```"
        result = remove_outer_markdown_markers(text)
        assert result == "\n# Heading\n\nSome content\n"

    def test_preserves_non_markdown_block(self) -> None:
        """
        Given: A string without markdown code block markers.
        When: remove_outer_markdown_markers is called.
        Then: The string is returned unchanged.
        """
        text = "# Heading\n\nSome content"
        result = remove_outer_markdown_markers(text)
        assert result == "# Heading\n\nSome content"

    def test_handles_empty_string(self) -> None:
        """
        Given: An empty string.
        When: remove_outer_markdown_markers is called.
        Then: An empty string is returned.
        """
        text = ""
        result = remove_outer_markdown_markers(text)
        assert result == ""


class TestRemoveOuterSinglequotes:
    """Tests for remove_outer_singlequotes function."""

    def test_removes_triple_singlequotes(self) -> None:
        """
        Given: A string wrapped in triple singlequote markers.
        When: remove_outer_singlequotes is called.
        Then: The markers are removed, keeping the inner content.
        """
        text = "'''Some content here'''"
        result = remove_outer_singlequotes(text)
        assert result == "Some content here"

    def test_preserves_non_quoted_string(self) -> None:
        """
        Given: A string without triple singlequote markers.
        When: remove_outer_singlequotes is called.
        Then: The string is returned unchanged.
        """
        text = "Some content here"
        result = remove_outer_singlequotes(text)
        assert result == "Some content here"

    def test_handles_empty_string(self) -> None:
        """
        Given: An empty string.
        When: remove_outer_singlequotes is called.
        Then: An empty string is returned.
        """
        text = ""
        result = remove_outer_singlequotes(text)
        assert result == ""


class TestIsValidBodyLine:
    """Tests for ArxivSummarizer._is_valid_body_line method."""

    @pytest.fixture
    def summarizer(self, monkeypatch: pytest.MonkeyPatch) -> ArxivSummarizer:
        """
        Create an ArxivSummarizer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: ArxivSummarizer is instantiated.
        Then: A valid summarizer instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ArxivSummarizer()

    def test_rejects_line_with_at_symbol(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: A line containing an @ symbol (likely an email).
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = (
            "Contact: author@university.edu for more information about this research."
        )
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_line_with_university_keyword(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line containing 'university' keyword.
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = (
            "This research was conducted at Stanford University with funding from NSF."
        )
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_short_line(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: A line shorter than the minimum length (default 80).
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "This is a short line."
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_line_without_period(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: A line without a period (not a complete sentence).
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "This is a long line without any punctuation that would indicate it is a complete sentence in the paper"
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_accepts_valid_body_line(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: A valid body line (long enough, has period, no excluded keywords).
        When: _is_valid_body_line is called.
        Then: True is returned.
        """
        line = "In this paper, we propose a novel approach to machine learning that significantly improves performance on benchmark datasets."
        result = summarizer._is_valid_body_line(line)
        assert result is True

    def test_accepts_line_with_custom_min_length(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line that meets a custom minimum length requirement.
        When: _is_valid_body_line is called with custom min_length.
        Then: True is returned if the line meets all criteria.
        """
        line = "This is a moderately long line with a period at the end."
        result = summarizer._is_valid_body_line(line, min_length=40)
        assert result is True

    def test_rejects_line_with_lab_keyword(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: A line containing 'lab' keyword.
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "The experiments were performed at the AI Research Lab using state-of-the-art equipment."
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_line_with_department_keyword(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line containing 'department' keyword.
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "The Department of Computer Science provided resources for this study and analysis."
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_line_with_institute_keyword(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line containing 'institute' keyword.
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "This work was supported by the Institute for Advanced Study and various grants."
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_rejects_line_with_corresponding_author(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line containing 'corresponding author' keyword.
        When: _is_valid_body_line is called.
        Then: False is returned.
        """
        line = "Corresponding author: John Smith. Please contact for any questions about this paper."
        result = summarizer._is_valid_body_line(line)
        assert result is False

    def test_keyword_check_is_case_insensitive(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: A line with uppercase keyword.
        When: _is_valid_body_line is called.
        Then: False is returned (case-insensitive check).
        """
        line = "This research was conducted at STANFORD UNIVERSITY with funding from various sources."
        result = summarizer._is_valid_body_line(line)
        assert result is False
