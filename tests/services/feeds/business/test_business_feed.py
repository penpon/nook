"""Tests for business_feed service domain logic.

This module tests the pure logic helper functions in business_feed.py:
- _extract_popularity
- _select_top_articles
- _get_markdown_header
- _get_summary_system_instruction
- _get_summary_prompt_template
- _needs_japanese_check
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from nook.services.base.base_feed_service import Article
from nook.services.feeds.business.business_feed import BusinessFeed


class TestExtractPopularity:
    """Tests for BusinessFeed._extract_popularity method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """
        Create a BusinessFeed instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: BusinessFeed is instantiated.
        Then: A valid business_feed instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_extracts_popularity_from_meta_tag_article_reaction_count(self, business_feed: BusinessFeed) -> None:
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

        result = business_feed._extract_popularity(entry, soup)

        assert result == 42.0

    def test_extracts_popularity_from_og_reaction_count(self, business_feed: BusinessFeed) -> None:
        """
        Given: HTML with meta tag containing og:reaction_count property.
        When: _extract_popularity is called.
        Then: The reaction count is extracted as popularity score.
        """
        html = """
        <html>
            <head>
                <meta property="og:reaction_count" content="88">
            </head>
            <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = business_feed._extract_popularity(entry, soup)

        assert result == 88.0

    def test_extracts_popularity_from_data_attribute(self, business_feed: BusinessFeed) -> None:
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

        result = business_feed._extract_popularity(entry, soup)

        assert result == 25.0

    def test_extracts_popularity_from_span_text_with_like_keyword(self, business_feed: BusinessFeed) -> None:
        """
        Given: HTML with span containing 'Like' keyword and a number.
        When: _extract_popularity is called.
        Then: The number is extracted as popularity score.
        """
        html = """
        <html>
            <body>
                <span>Like 77</span>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        entry = MagicMock()

        result = business_feed._extract_popularity(entry, soup)

        assert result == 77.0

    def test_returns_zero_when_no_popularity_found(self, business_feed: BusinessFeed) -> None:
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

        result = business_feed._extract_popularity(entry, soup)

        assert result == 0.0


class TestSelectTopArticles:
    """Tests for BusinessFeed._select_top_articles method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """
        Create a BusinessFeed instance for testing.

        Given: Environment variable OPENAI_API_KEY is set to a dummy value.
        When: BusinessFeed is instantiated.
        Then: A valid business_feed instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

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

    def test_returns_empty_list_when_no_articles(self, business_feed: BusinessFeed) -> None:
        """
        Given: An empty list of articles.
        When: _select_top_articles is called.
        Then: An empty list is returned.
        """
        result = business_feed._select_top_articles([])

        assert result == []

    def test_sorts_articles_by_popularity_descending(self, business_feed: BusinessFeed) -> None:
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

        result = business_feed._select_top_articles(articles, limit=3)

        assert result[0].title == "High"
        assert result[1].title == "Medium"
        assert result[2].title == "Low"

    def test_limits_to_specified_count(self, business_feed: BusinessFeed) -> None:
        """
        Given: A list of 5 articles.
        When: _select_top_articles is called with limit=2.
        Then: Only 2 articles are returned.
        """
        articles = [self._create_article(f"Article {i}", float(i * 10)) for i in range(5)]

        result = business_feed._select_top_articles(articles, limit=2)

        assert len(result) == 2


class TestGetMarkdownHeader:
    """Tests for BusinessFeed._get_markdown_header method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """Create a BusinessFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_returns_business_news_header(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance.
        When: _get_markdown_header is called.
        Then: The header text for business news is returned.
        """
        result = business_feed._get_markdown_header()

        assert result == "ビジネスニュース記事"


class TestNeedsJapaneseCheck:
    """Tests for BusinessFeed._needs_japanese_check method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """Create a BusinessFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_returns_true_for_business_feed(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance.
        When: _needs_japanese_check is called.
        Then: True is returned (business_feed requires Japanese content check).
        """
        result = business_feed._needs_japanese_check()

        assert result is True

    def test_returns_true_for_japanese_content_check(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance with Japanese content requirement.
        When: _needs_japanese_check is called multiple times.
        Then: Consistently returns True for Japanese content validation.
        """
        # 複数回呼び出しても同じ結果が返るべき
        for _ in range(3):
            result = business_feed._needs_japanese_check()
            assert result is True

    def test_returns_true_for_mixed_language_content(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance that handles mixed language content.
        When: _needs_japanese_check is called.
        Then: True is returned indicating Japanese check is required.
        """
        # 混合コンテンツであっても、日本語チェックは必須であるべき
        result = business_feed._needs_japanese_check()
        assert result is True


class TestGetSummarySystemInstruction:
    """Tests for BusinessFeed._get_summary_system_instruction method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """Create a BusinessFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_returns_japanese_instruction(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance.
        When: _get_summary_system_instruction is called.
        Then: The instruction contains Japanese response requirement.
        """
        result = business_feed._get_summary_system_instruction()

        assert "日本語" in result
        assert "要約" in result or "ビジネス" in result


class TestGetSummaryPromptTemplate:
    """Tests for BusinessFeed._get_summary_prompt_template method."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """Create a BusinessFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_includes_article_title_and_text(self, business_feed: BusinessFeed) -> None:
        """
        Given: An Article with title and text.
        When: _get_summary_prompt_template is called.
        Then: The template includes the article's title and text.
        """
        article = Article(
            feed_name="Test Feed",
            title="Business Article Title",
            url="https://example.com",
            text="Business news content for testing.",
            soup=BeautifulSoup("<html></html>", "html.parser"),
            category="test",
            popularity_score=0.0,
            published_at=datetime.now(timezone.utc),
        )

        result = business_feed._get_summary_prompt_template(article)

        assert "Business Article Title" in result
        assert "Business news content" in result


class TestConstants:
    """Tests for BusinessFeed constants."""

    @pytest.fixture
    def business_feed(self, monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
        """Create a BusinessFeed instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return BusinessFeed()

    def test_summary_limit_is_reasonable(self, business_feed: BusinessFeed) -> None:
        """
        Given: A BusinessFeed instance.
        When: Checking SUMMARY_LIMIT.
        Then: It should be a reasonable value (15).
        """
        assert business_feed.SUMMARY_LIMIT == 15
