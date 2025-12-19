"""Tests for tech_feed service domain logic.

This module tests the pure logic helper functions in tech_feed.py:
- _extract_popularity
- _select_top_articles
- _get_markdown_header
- _get_summary_system_instruction
- _needs_japanese_check
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from nook.services.base.base_feed_service import Article
from nook.services.feeds.tech.tech_feed import TechFeed


class TestExtractPopularity:
    """Tests for TechFeed._extract_popularity method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """
        Create a TechFeed instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: TechFeed is instantiated.
        Then: A valid tech_feed instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_extracts_popularity_from_meta_tag_article_reaction_count(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with meta tag containing article:reaction_count property.
        When: _extract_popularity is called.
        Then: The reaction count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta property="article:reaction_count" content="42">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 42.0

    def test_extracts_popularity_from_meta_tag_reaction_count(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with meta tag containing reaction-count name.
        When: _extract_popularity is called.
        Then: The reaction count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta name="reaction-count" content="100">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 100.0

    def test_extracts_popularity_from_data_attribute(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with element containing data-reaction-count attribute.
        When: _extract_popularity is called.
        Then: The reaction count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button data-reaction-count="25">Like</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 25.0

    def test_extracts_popularity_from_like_count_attribute(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with element containing data-like-count attribute.
        When: _extract_popularity is called.
        Then: The like count is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <span data-like-count="50">50 likes</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 50.0

    def test_extracts_popularity_from_button_text_with_keyword(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with button containing 'いいね' keyword and a number.
        When: _extract_popularity is called.
        Then: The number is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <button>いいね 15</button>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 15.0

    def test_returns_max_when_multiple_candidates(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with multiple elements containing popularity counts.
        When: _extract_popularity is called.
        Then: The maximum count is returned.
        """
        html = """
        <html>
            <body>
                <button data-reaction-count="10">Reaction</button>
                <span data-like-count="30">Like</span>
                <div>いいね 20</div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 30.0

    def test_returns_zero_when_no_popularity_found(self, tech_feed: TechFeed) -> None:
        """
        Given: HTML with no popularity indicators.
        When: _extract_popularity is called.
        Then: 0.0 is returned.
        """
        html = """
        <html>
            <body>
                <p>Just a regular paragraph</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = tech_feed._extract_popularity(entry, soup)

        assert result == 0.0


class TestSelectTopArticles:
    """Tests for TechFeed._select_top_articles method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """
        Create a TechFeed instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: TechFeed is instantiated.
        Then: A valid tech_feed instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def _create_article(self, title: str, popularity_score: float) -> Article:
        """Helper to create Article instances for testing."""
        return Article(
            feed_name="Test Feed",
            title=title,
            url="https://example.com/article",
            text="Test article text",
            soup=BeautifulSoup("<html></html>", "html.parser"),
            category="test",
            popularity_score=popularity_score,
            published_at=datetime.now(timezone.utc),
        )

    def test_returns_empty_list_when_no_articles(self, tech_feed: TechFeed) -> None:
        """
        Given: An empty list of articles.
        When: _select_top_articles is called.
        Then: An empty list is returned.
        """
        result = tech_feed._select_top_articles([])

        assert result == []

    def test_sorts_articles_by_popularity_descending(self, tech_feed: TechFeed) -> None:
        """
        Given: A list of articles with various popularity scores.
        When: _select_top_articles is called.
        Then: Articles are sorted by popularity in descending order.
        """
        articles = [
            self._create_article("Low", 10.0),
            self._create_article("High", 100.0),
            self._create_article("Medium", 50.0),
        ]

        result = tech_feed._select_top_articles(articles, limit=3)

        assert result[0].title == "High"
        assert result[1].title == "Medium"
        assert result[2].title == "Low"

    def test_limits_to_specified_count(self, tech_feed: TechFeed) -> None:
        """
        Given: A list of 5 articles.
        When: _select_top_articles is called with limit=2.
        Then: Only 2 articles are returned.
        """
        articles = [self._create_article(f"Article {i}", float(i * 10)) for i in range(5)]

        result = tech_feed._select_top_articles(articles, limit=2)

        assert len(result) == 2

    def test_uses_summary_limit_when_no_limit_specified(self, tech_feed: TechFeed) -> None:
        """
        Given: A list of 20 articles.
        When: _select_top_articles is called without limit.
        Then: SUMMARY_LIMIT (15) articles are returned.
        """
        articles = [self._create_article(f"Article {i}", float(i)) for i in range(20)]

        result = tech_feed._select_top_articles(articles)

        assert len(result) == tech_feed.SUMMARY_LIMIT


class TestGetMarkdownHeader:
    """Tests for TechFeed._get_markdown_header method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """Create a TechFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_returns_tech_news_header(self, tech_feed: TechFeed) -> None:
        """
        Given: A TechFeed instance.
        When: _get_markdown_header is called.
        Then: The header text for tech news is returned.
        """
        result = tech_feed._get_markdown_header()

        assert result == "技術ニュース記事"


class TestNeedsJapaneseCheck:
    """Tests for TechFeed._needs_japanese_check method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """Create a TechFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_returns_true_for_tech_feed(self, tech_feed: TechFeed) -> None:
        """
        Given: A TechFeed instance.
        When: _needs_japanese_check is called.
        Then: True is returned (tech_feed requires Japanese content check).
        """
        result = tech_feed._needs_japanese_check()

        assert result is True


class TestGetSummarySystemInstruction:
    """Tests for TechFeed._get_summary_system_instruction method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """Create a TechFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_returns_japanese_instruction(self, tech_feed: TechFeed) -> None:
        """
        Given: A TechFeed instance.
        When: _get_summary_system_instruction is called.
        Then: The instruction contains Japanese response requirement.
        """
        result = tech_feed._get_summary_system_instruction()

        assert "日本語" in result
        assert "要約" in result or "技術" in result


class TestGetSummaryPromptTemplate:
    """Tests for TechFeed._get_summary_prompt_template method."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """Create a TechFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_includes_article_title_and_text(self, tech_feed: TechFeed) -> None:
        """
        Given: An Article with title and text.
        When: _get_summary_prompt_template is called.
        Then: The template includes the article's title and text.
        """
        article = Article(
            feed_name="Test Feed",
            title="Test Article Title",
            url="https://example.com",
            text="This is the article text content for testing.",
            soup=BeautifulSoup("<html></html>", "html.parser"),
            category="test",
            popularity_score=0.0,
            published_at=datetime.now(timezone.utc),
        )

        result = tech_feed._get_summary_prompt_template(article)

        assert "Test Article Title" in result
        assert "This is the article text content" in result

    def test_truncates_long_text(self, tech_feed: TechFeed) -> None:
        """
        Given: An Article with very long text.
        When: _get_summary_prompt_template is called.
        Then: The text is truncated in the template.
        """
        long_text = "A" * 5000
        article = Article(
            feed_name="Test Feed",
            title="Test",
            url="https://example.com",
            text=long_text,
            soup=BeautifulSoup("<html></html>", "html.parser"),
            category="test",
            popularity_score=0.0,
            published_at=datetime.now(timezone.utc),
        )

        result = tech_feed._get_summary_prompt_template(article)

        # テキストは2000文字に切り詰められるべき
        assert len(result) < len(long_text)


class TestConstants:
    """Tests for TechFeed constants."""

    @pytest.fixture
    def tech_feed(self, monkeypatch: pytest.MonkeyPatch) -> TechFeed:
        """Create a TechFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return TechFeed()

    def test_summary_limit_is_reasonable(self, tech_feed: TechFeed) -> None:
        """
        Given: A TechFeed instance.
        When: Checking SUMMARY_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert tech_feed.SUMMARY_LIMIT == 15

    def test_total_limit_is_reasonable(self, tech_feed: TechFeed) -> None:
        """
        Given: A TechFeed instance.
        When: Checking TOTAL_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert tech_feed.TOTAL_LIMIT == 15
