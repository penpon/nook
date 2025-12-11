"""Tests for qiita_explorer service domain logic.

This module tests the pure logic helper functions in qiita_explorer.py:
- _extract_popularity (Qiita LGTM count extraction)
- _get_markdown_header
"""

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from nook.services.explorers.qiita.qiita_explorer import QiitaExplorer


class TestExtractPopularity:
    """Tests for QiitaExplorer._extract_popularity method."""

    @pytest.fixture
    def qiita_explorer(self, monkeypatch: pytest.MonkeyPatch) -> QiitaExplorer:
        """
        Create a QiitaExplorer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: QiitaExplorer is instantiated.
        Then: A valid qiita_explorer instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return QiitaExplorer()

    def test_extracts_popularity_from_entry_lgtm_count(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: Entry object with lgtm_count attribute.
        When: _extract_popularity is called.
        Then: The LGTM count is returned as popularity score.
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = 88

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 88.0

    def test_extracts_popularity_from_entry_qiita_likes_count(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: Entry object with qiita_likes_count attribute (highest priority).
        When: _extract_popularity is called.
        Then: The qiita_likes_count is returned as popularity score.
        """
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = 120

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 120.0

    def test_extracts_popularity_from_twitter_meta_tag(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: HTML with meta tag containing twitter:data1.
        When: _extract_popularity is called with entry having no LGTM attribute.
        Then: The value from meta tag is extracted.
        """
        html = """
        <html>
            <head>
                <meta name="twitter:data1" content="55">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = None

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 55.0

    def test_extracts_popularity_from_data_lgtm_count(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: HTML with element containing data-lgtm-count attribute.
        When: _extract_popularity is called.
        Then: The LGTM count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button data-lgtm-count="200">LGTM</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = None

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 200.0

    def test_extracts_popularity_from_lgtm_class_element(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: HTML with LGTM keyword in text.
        When: _extract_popularity is called.
        Then: The number with LGTM keyword is extracted.
        """
        html = """
        <html>
            <body>
                <button>LGTM 45</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = None

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 45.0

    def test_returns_zero_when_no_popularity_found(
        self, qiita_explorer: QiitaExplorer
    ) -> None:
        """
        Given: HTML with no popularity indicators.
        When: _extract_popularity is called.
        Then: 0.0 is returned.
        """
        html = "<html><body><p>No LGTM here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = None

        result = qiita_explorer._extract_popularity(entry, soup)

        assert result == 0.0


class TestGetMarkdownHeader:
    """Tests for QiitaExplorer._get_markdown_header method."""

    @pytest.fixture
    def qiita_explorer(self, monkeypatch: pytest.MonkeyPatch) -> QiitaExplorer:
        """Create a QiitaExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return QiitaExplorer()

    def test_returns_qiita_header(self, qiita_explorer: QiitaExplorer) -> None:
        """
        Given: A QiitaExplorer instance.
        When: _get_markdown_header is called.
        Then: The header text for Qiita articles is returned.
        """
        result = qiita_explorer._get_markdown_header()

        assert result == "Qiita記事"


class TestGetSummarySystemInstruction:
    """Tests for QiitaExplorer._get_summary_system_instruction method."""

    @pytest.fixture
    def qiita_explorer(self, monkeypatch: pytest.MonkeyPatch) -> QiitaExplorer:
        """Create a QiitaExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return QiitaExplorer()

    def test_returns_japanese_instruction(self, qiita_explorer: QiitaExplorer) -> None:
        """
        Given: A QiitaExplorer instance.
        When: _get_summary_system_instruction is called.
        Then: The instruction contains Japanese response requirement.
        """
        result = qiita_explorer._get_summary_system_instruction()

        assert "日本語" in result
        assert "Qiita" in result or "要約" in result


class TestConstants:
    """Tests for QiitaExplorer constants."""

    @pytest.fixture
    def qiita_explorer(self, monkeypatch: pytest.MonkeyPatch) -> QiitaExplorer:
        """Create a QiitaExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return QiitaExplorer()

    def test_summary_limit_is_reasonable(self, qiita_explorer: QiitaExplorer) -> None:
        """
        Given: A QiitaExplorer instance.
        When: Checking SUMMARY_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert qiita_explorer.SUMMARY_LIMIT == 15
