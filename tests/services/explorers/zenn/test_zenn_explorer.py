"""Tests for zenn_explorer service domain logic.

This module tests the pure logic helper functions in zenn_explorer.py:
- _extract_popularity (Zenn likes count extraction)
- _get_markdown_header
"""

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from nook.services.explorers.zenn.zenn_explorer import ZennExplorer


class TestExtractPopularity:
    """Tests for ZennExplorer._extract_popularity method."""

    @pytest.fixture
    def zenn_explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZennExplorer:
        """
        Create a ZennExplorer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: ZennExplorer is instantiated.
        Then: A valid zenn_explorer instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZennExplorer()

    def test_extracts_popularity_from_zenn_meta_tag(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: HTML with meta tag containing zenn:likes_count property.
        When: _extract_popularity is called.
        Then: The likes count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta property="zenn:likes_count" content="150">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 150.0

    def test_extracts_popularity_from_data_like_count(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: HTML with element containing data-like-count attribute.
        When: _extract_popularity is called.
        Then: The like count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <div data-like-count="75">Likes</div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 75.0

    def test_extracts_popularity_from_button_with_iine_text(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: HTML with button containing 'いいね' keyword and a number.
        When: _extract_popularity is called.
        Then: The number is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button>いいね 25</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 25.0

    def test_extracts_popularity_from_entry_likes_attribute(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: Entry object with likes attribute.
        When: _extract_popularity is called with empty HTML.
        Then: The likes value from entry is returned.
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock(spec=["likes", "likes_count"])
        entry.likes = 200
        entry.likes_count = None

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 200.0

    def test_returns_zero_when_no_popularity_found(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: HTML with no popularity indicators.
        When: _extract_popularity is called.
        Then: 0.0 is returned.
        """
        html = "<html><body><p>No likes here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock(spec=["likes", "likes_count"])
        entry.likes = None
        entry.likes_count = None

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 0.0

    def test_prioritizes_likes_over_likes_count_attribute(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: Entry with both likes and likes_count attributes.
        When: _extract_popularity is called.
        Then: likes value is prioritized and returned (actual implementation behavior).
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock(spec=["likes", "likes_count"])
        entry.likes = 100
        entry.likes_count = 250

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 100.0

    def test_falls_back_to_likes_when_likes_count_missing(
        self, zenn_explorer: ZennExplorer
    ) -> None:
        """
        Given: Entry with only likes attribute, likes_count is None.
        When: _extract_popularity is called.
        Then: likes value is returned as fallback.
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock(spec=["likes", "likes_count"])
        entry.likes = 180
        entry.likes_count = None

        result = zenn_explorer._extract_popularity(entry, soup)

        assert result == 180.0


class TestGetMarkdownHeader:
    """Tests for ZennExplorer._get_markdown_header method."""

    @pytest.fixture
    def zenn_explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZennExplorer:
        """Create a ZennExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZennExplorer()

    def test_returns_zenn_header(self, zenn_explorer: ZennExplorer) -> None:
        """
        Given: A ZennExplorer instance.
        When: _get_markdown_header is called.
        Then: The header text for Zenn articles is returned.
        """
        result = zenn_explorer._get_markdown_header()

        assert result == "Zenn記事"


class TestGetSummarySystemInstruction:
    """Tests for ZennExplorer._get_summary_system_instruction method."""

    @pytest.fixture
    def zenn_explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZennExplorer:
        """Create a ZennExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZennExplorer()

    def test_returns_japanese_instruction(self, zenn_explorer: ZennExplorer) -> None:
        """
        Given: A ZennExplorer instance.
        When: _get_summary_system_instruction is called.
        Then: The instruction contains Japanese response requirement.
        """
        result = zenn_explorer._get_summary_system_instruction()

        assert "日本語" in result
        assert "Zenn" in result or "要約" in result


class TestConstants:
    """Tests for ZennExplorer constants."""

    @pytest.fixture
    def zenn_explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZennExplorer:
        """Create a ZennExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZennExplorer()

    def test_summary_limit_is_reasonable(self, zenn_explorer: ZennExplorer) -> None:
        """
        Given: A ZennExplorer instance.
        When: Checking SUMMARY_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert zenn_explorer.SUMMARY_LIMIT == 15
