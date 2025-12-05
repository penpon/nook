"""Tests for note_explorer service domain logic.

This module tests the pure logic helper functions in note_explorer.py:
- _extract_popularity (note likes/suki count extraction)
- _get_markdown_header
"""

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from nook.services.note_explorer.note_explorer import NoteExplorer


class TestExtractPopularity:
    """Tests for NoteExplorer._extract_popularity method."""

    @pytest.fixture
    def note_explorer(self, monkeypatch: pytest.MonkeyPatch) -> NoteExplorer:
        """
        Create a NoteExplorer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: NoteExplorer is instantiated.
        Then: A valid note_explorer instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return NoteExplorer()

    def test_extracts_popularity_from_twitter_data1_meta(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with meta tag containing twitter:data1.
        When: _extract_popularity is called.
        Then: The suki count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta name="twitter:data1" content="100">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 100.0

    def test_extracts_popularity_from_note_likes_meta(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with meta tag containing note:likes.
        When: _extract_popularity is called.
        Then: The likes count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta name="note:likes" content="250">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 250.0

    def test_extracts_popularity_from_data_like_count(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with element containing data-like-count attribute.
        When: _extract_popularity is called.
        Then: The like count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <span data-like-count="85">スキ</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 85.0

    def test_extracts_popularity_from_data_suki_count(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with element containing data-suki-count attribute.
        When: _extract_popularity is called.
        Then: The suki count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button data-suki-count="42">スキ</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 42.0

    def test_extracts_popularity_from_button_with_suki_text(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with button containing 'スキ' keyword and a number.
        When: _extract_popularity is called.
        Then: The number is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button>スキ 33</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 33.0

    def test_extracts_popularity_from_entry_likes_attribute(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: Entry object with likes attribute.
        When: _extract_popularity is called with empty HTML.
        Then: The likes value from entry is returned.
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = 300
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 300.0

    def test_returns_zero_when_no_popularity_found(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: HTML with no popularity indicators.
        When: _extract_popularity is called.
        Then: 0.0 is returned.
        """
        html = "<html><body><p>No suki here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 0.0

    def test_ignores_non_numeric_meta_content(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: Non-numeric metadata content.
        When: _extract_popularity parses the value.
        Then: It is ignored and 0.0 is returned.
        """
        html = """
        <html>
            <head>
                <meta name="twitter:data1" content="not-a-number">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.likes = None
        entry.likes_count = None

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 0.0

    def test_handles_missing_entry_attributes_gracefully(
        self, note_explorer: NoteExplorer
    ) -> None:
        """
        Given: Entry object without likes-related attributes.
        When: _extract_popularity checks feed fields.
        Then: It falls back to 0.0 without raising errors.
        """
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        entry = MagicMock(spec=[])

        result = note_explorer._extract_popularity(entry, soup)

        assert result == 0.0


class TestGetMarkdownHeader:
    """Tests for NoteExplorer._get_markdown_header method."""

    @pytest.fixture
    def note_explorer(self, monkeypatch: pytest.MonkeyPatch) -> NoteExplorer:
        """Create a NoteExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return NoteExplorer()

    def test_returns_note_header(self, note_explorer: NoteExplorer) -> None:
        """
        Given: A NoteExplorer instance.
        When: _get_markdown_header is called.
        Then: The header text for note articles is returned.
        """
        result = note_explorer._get_markdown_header()

        assert result == "note記事"


class TestGetSummarySystemInstruction:
    """Tests for NoteExplorer._get_summary_system_instruction method."""

    @pytest.fixture
    def note_explorer(self, monkeypatch: pytest.MonkeyPatch) -> NoteExplorer:
        """Create a NoteExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return NoteExplorer()

    def test_returns_japanese_instruction(self, note_explorer: NoteExplorer) -> None:
        """
        Given: A NoteExplorer instance.
        When: _get_summary_system_instruction is called.
        Then: The instruction contains Japanese response requirement.
        """
        result = note_explorer._get_summary_system_instruction()

        assert "日本語" in result
        assert "note" in result or "要約" in result


class TestConstants:
    """Tests for NoteExplorer constants."""

    @pytest.fixture
    def note_explorer(self, monkeypatch: pytest.MonkeyPatch) -> NoteExplorer:
        """Create a NoteExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return NoteExplorer()

    def test_summary_limit_is_reasonable(self, note_explorer: NoteExplorer) -> None:
        """
        Given: A NoteExplorer instance.
        When: Checking SUMMARY_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert note_explorer.SUMMARY_LIMIT == 15
