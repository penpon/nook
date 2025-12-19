"""Tests for hacker_news service domain logic.

This module tests the pure logic helper functions in hacker_news.py:
- Story dataclass
- _is_blocked_domain
- _is_http1_required_domain
- _story_sort_key
- _render_markdown
- _parse_markdown
"""

from datetime import datetime, timezone

import pytest

from nook.services.feeds.hacker_news.hacker_news import (
    MAX_TEXT_LENGTH,
    MIN_TEXT_LENGTH,
    SCORE_THRESHOLD,
    HackerNewsRetriever,
    Story,
)


class TestStoryDataclass:
    """Tests for Story dataclass."""

    def test_story_creation_with_required_fields(self) -> None:
        """
        Given: Required fields for a Story (title, score).
        When: A Story is created.
        Then: The Story instance has correct values and defaults.
        """
        story = Story(title="Test Story", score=100)

        assert story.title == "Test Story"
        assert story.score == 100
        assert story.url is None
        assert story.text is None
        assert story.summary == ""
        assert story.created_at is None

    def test_story_creation_with_all_fields(self) -> None:
        """
        Given: All fields for a Story.
        When: A Story is created.
        Then: The Story instance has all correct values.
        """
        created = datetime.now(timezone.utc)
        story = Story(
            title="Full Story",
            score=200,
            url="https://example.com",
            text="Story content",
            created_at=created,
        )

        assert story.title == "Full Story"
        assert story.score == 200
        assert story.url == "https://example.com"
        assert story.text == "Story content"
        assert story.created_at == created


class TestIsBlockedDomain:
    """Tests for HackerNewsRetriever._is_blocked_domain method."""

    @pytest.fixture
    def hacker_news(self, monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
        """
        Create a HackerNewsRetriever instance for testing.

        Given: Environment variable OPENAI_API_KEY is set.
        When: HackerNewsRetriever is instantiated.
        Then: A valid instance is returned with mock blocked domains.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        retriever = HackerNewsRetriever()
        # Set up mock blocked domains for testing
        retriever.blocked_domains = {
            "blocked_domains": ["example-blocked.com", "spam-site.org"],
            "reasons": {
                "example-blocked.com": "403 - Access denied",
                "spam-site.org": "Spam content",
            },
        }
        return retriever

    def test_returns_true_for_blocked_domain(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A URL from a blocked domain.
        When: _is_blocked_domain is called.
        Then: True is returned.
        """
        url = "https://example-blocked.com/article/123"

        result = hacker_news._is_blocked_domain(url)

        assert result is True

    def test_returns_true_for_blocked_domain_with_www(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A URL with www. prefix from a blocked domain.
        When: _is_blocked_domain is called.
        Then: True is returned (www. is stripped for comparison).
        """
        url = "https://www.example-blocked.com/article/123"

        result = hacker_news._is_blocked_domain(url)

        assert result is True

    def test_returns_false_for_non_blocked_domain(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A URL from a non-blocked domain.
        When: _is_blocked_domain is called.
        Then: False is returned.
        """
        url = "https://github.com/some/repo"

        result = hacker_news._is_blocked_domain(url)

        assert result is False

    def test_returns_false_for_empty_url(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: An empty URL.
        When: _is_blocked_domain is called.
        Then: False is returned.
        """
        result = hacker_news._is_blocked_domain("")

        assert result is False

    def test_returns_false_for_none_url(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A None URL.
        When: _is_blocked_domain is called.
        Then: False is returned.
        """
        result = hacker_news._is_blocked_domain(None)

        assert result is False


class TestIsHttp1RequiredDomain:
    """Tests for HackerNewsRetriever._is_http1_required_domain method."""

    @pytest.fixture
    def hacker_news(self, monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
        """Create a HackerNewsRetriever instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        retriever = HackerNewsRetriever()
        retriever.blocked_domains = {
            "blocked_domains": [],
            "reasons": {},
            "http1_required_domains": ["legacy-site.com", "old-api.org"],
        }
        return retriever

    def test_returns_true_for_http1_required_domain(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A URL from a domain requiring HTTP/1.1.
        When: _is_http1_required_domain is called.
        Then: True is returned.
        """
        url = "https://legacy-site.com/page"

        result = hacker_news._is_http1_required_domain(url)

        assert result is True

    def test_returns_false_for_normal_domain(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A URL from a normal domain.
        When: _is_http1_required_domain is called.
        Then: False is returned.
        """
        url = "https://normal-site.com/page"

        result = hacker_news._is_http1_required_domain(url)

        assert result is False

    def test_returns_false_for_empty_url(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: An empty URL.
        When: _is_http1_required_domain is called.
        Then: False is returned.
        """
        result = hacker_news._is_http1_required_domain("")

        assert result is False


class TestStorySortKey:
    """Tests for HackerNewsRetriever._story_sort_key method."""

    @pytest.fixture
    def hacker_news(self, monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
        """Create a HackerNewsRetriever instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return HackerNewsRetriever()

    def test_sort_key_with_score_and_published_at(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A story record with score and published_at.
        When: _story_sort_key is called.
        Then: A tuple of (score, datetime) is returned.
        """
        record = {
            "score": 100,
            "published_at": "2024-01-15T10:30:00+00:00",
        }

        result = hacker_news._story_sort_key(record)

        assert result[0] == 100
        assert result[1].year == 2024
        assert result[1].month == 1
        assert result[1].day == 15

    def test_sort_key_with_missing_score(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A story record with missing score.
        When: _story_sort_key is called.
        Then: Score defaults to 0.
        """
        record = {
            "published_at": "2024-01-15T10:30:00+00:00",
        }

        result = hacker_news._story_sort_key(record)

        assert result[0] == 0

    def test_sort_key_with_none_score(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A story record with None score.
        When: _story_sort_key is called.
        Then: Score defaults to 0.
        """
        record = {
            "score": None,
            "published_at": "2024-01-15T10:30:00+00:00",
        }

        result = hacker_news._story_sort_key(record)

        assert result[0] == 0

    def test_sort_key_with_missing_published_at(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: A story record with missing published_at.
        When: _story_sort_key is called.
        Then: Published_at defaults to datetime.min.
        """
        record = {"score": 50}

        result = hacker_news._story_sort_key(record)

        assert result[0] == 50
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)


class TestRenderMarkdown:
    """Tests for HackerNewsRetriever._render_markdown method."""

    @pytest.fixture
    def hacker_news(self, monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
        """Create a HackerNewsRetriever instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return HackerNewsRetriever()

    def test_render_markdown_with_url_and_summary(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Story records with URL and summary.
        When: _render_markdown is called.
        Then: Markdown content with linked titles and summaries is generated.
        """
        records = [
            {
                "title": "Test Story",
                "url": "https://example.com/article",
                "score": 100,
                "summary": "This is a test summary.",
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = hacker_news._render_markdown(records, today)

        assert "# Hacker News トップ記事 (2024-01-15)" in result
        assert "[Test Story](https://example.com/article)" in result
        assert "スコア: 100" in result
        assert "**要約**:" in result
        assert "This is a test summary." in result

    def test_render_markdown_without_url(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Story records without URL.
        When: _render_markdown is called.
        Then: Title is rendered without link.
        """
        records = [
            {
                "title": "No URL Story",
                "url": None,
                "score": 50,
                "text": "Some text content",
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = hacker_news._render_markdown(records, today)

        assert "## No URL Story" in result
        assert "[No URL Story]" not in result


class TestParseMarkdown:
    """Tests for HackerNewsRetriever._parse_markdown method."""

    @pytest.fixture
    def hacker_news(self, monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
        """Create a HackerNewsRetriever instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return HackerNewsRetriever()

    def test_parse_markdown_with_linked_title(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Markdown content with linked title.
        When: _parse_markdown is called.
        Then: Story records are extracted with title, URL, and score.
        """
        content = """
## [Test Story](https://example.com/article)

スコア: 100

**要約**:
This is a test summary.

---
"""
        result = hacker_news._parse_markdown(content)

        assert len(result) == 1
        assert result[0]["title"] == "Test Story"
        assert result[0]["url"] == "https://example.com/article"
        assert result[0]["score"] == 100
        assert result[0]["summary"] == "This is a test summary."


class TestConstants:
    """Tests for module-level constants."""

    def test_score_threshold_is_reasonable(self) -> None:
        """
        Given: The SCORE_THRESHOLD constant.
        When: Checking its value.
        Then: It should be a reasonable minimum score.
        """
        assert SCORE_THRESHOLD == 20

    def test_text_length_limits_are_reasonable(self) -> None:
        """
        Given: The text length limit constants.
        When: Checking their values.
        Then: They should define a reasonable range.
        """
        assert MIN_TEXT_LENGTH == 100
        assert MAX_TEXT_LENGTH == 10000
        assert MIN_TEXT_LENGTH < MAX_TEXT_LENGTH
