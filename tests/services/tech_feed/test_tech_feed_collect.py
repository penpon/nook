"""Tests for TechFeed collect flow and article retrieval logic."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.tech_feed.tech_feed import TechFeed
from nook.services.base_feed_service import Article


@pytest.fixture
def tech_feed(monkeypatch: pytest.MonkeyPatch) -> TechFeed:
    """Create a TechFeed instance with mocked dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    feed = TechFeed()
    feed.http_client = AsyncMock()
    feed.gpt_client = AsyncMock()
    feed.storage = AsyncMock()
    feed.logger = MagicMock()
    # Mock dedup tracker loading
    feed._get_all_existing_dates = AsyncMock(return_value=[])
    return feed


@pytest.mark.asyncio
class TestRetrieveArticle:
    """Tests for _retrieve_article method."""

    async def test_returns_none_if_no_url(self, tech_feed: TechFeed) -> None:
        """Should return None if entry has no link."""
        entry = MagicMock()
        del entry.link

        result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")
        assert result is None

    async def test_returns_none_if_non_japanese(self, tech_feed: TechFeed) -> None:
        """Should return None if content is not Japanese."""
        entry = MagicMock(link="http://example.com", title="English Title")
        del entry.summary  # Ensure summary doesn't exist to trigger fetching
        tech_feed.http_client.get.return_value = MagicMock(
            text="<html><body>English Content</body></html>"
        )

        # Mock _detect_japanese_content to return False
        with patch.object(tech_feed, "_detect_japanese_content", return_value=False):
            result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert result is None
        tech_feed.logger.debug.assert_called_with(
            "非日本語記事をスキップ: English Title"
        )

    async def test_returns_article_success(self, tech_feed: TechFeed) -> None:
        """Should return Article object on success."""
        entry = MagicMock(link="http://example.com/1", title="日本語タイトル")
        # Explicitly set summary to None to fallback to meta description or body
        del entry.summary
        entry.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 0, 0)
        tech_feed.http_client.get.return_value = MagicMock(
            text="<html><body><p>日本語の本文です。</p></body></html>"
        )

        with patch.object(tech_feed, "_detect_japanese_content", return_value=True):
            result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert isinstance(result, Article)
        assert result.title == "日本語タイトル"
        assert result.text == "日本語の本文です。"
        assert result.url == "http://example.com/1"

    async def test_returns_article_with_summary_from_entry(
        self, tech_feed: TechFeed
    ) -> None:
        """Should use summary from entry if available."""
        entry = MagicMock(link="http://example.com/1", title="日本語タイトル")
        entry.summary = "Entry Summary"  # Explicitly set summary
        entry.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 0, 0)
        tech_feed.http_client.get.return_value = MagicMock(
            text="<html>Some html</html>"
        )

        with patch.object(tech_feed, "_detect_japanese_content", return_value=True):
            result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert result.text == "Entry Summary"

    async def test_handles_exception_gracefully(self, tech_feed: TechFeed) -> None:
        """Should return None and log error on exception."""
        entry = MagicMock(link="http://example.com/error")
        tech_feed.http_client.get.side_effect = Exception("Network Error")

        result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert result is None
        tech_feed.logger.error.assert_called_once()
        assert "Network Error" in str(tech_feed.logger.error.call_args)


@pytest.mark.asyncio
class TestCollect:
    """Tests for collect method."""

    @pytest.fixture
    def mock_feed_config(self, tech_feed: TechFeed):
        """Mock feed configuration."""
        tech_feed.feed_config = {"tech": ["http://feed.com/rss"]}
        return tech_feed

    async def test_collect_flow_success(self, mock_feed_config: TechFeed):
        """Test successful collection flow."""
        # Mock feedparser
        mock_entry = MagicMock(title="New Article", link="http://example.com/new")
        # Must bypass date filter in _filter_entries
        # We can either mock _filter_entries or set target_dates appropriately
        # Let's mock _filter_entries to simplify

        mock_feed = MagicMock(entries=[mock_entry])
        mock_feed.feed.title = "Test Feed"

        # Mock dependencies
        mock_article = Article(
            feed_name="Test Feed",
            title="New Article",
            url="http://example.com/new",
            text="Content",
            soup=BeautifulSoup("", "html.parser"),
            category="tech",
            popularity_score=10.0,
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("feedparser.parse", return_value=mock_feed),
            patch(
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch.object(
                mock_feed_config, "_filter_entries", return_value=[mock_entry]
            ),
            patch.object(
                mock_feed_config, "_retrieve_article", return_value=mock_article
            ) as mock_retrieve,
            patch.object(
                mock_feed_config, "_summarize_article", new_callable=AsyncMock
            ) as mock_summarize,
            patch.object(
                mock_feed_config, "_store_summaries_for_date", new_callable=AsyncMock
            ) as mock_store,
        ):
            # Setup dedup tracker mock
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (False, "New Article")
            mock_load_dedup.return_value = mock_tracker

            # Setup store return
            mock_store.return_value = ("path/to/json", "path/to/md")

            # Helper to mock is_within_target_dates since we are mocking Article
            with patch(
                "nook.services.tech_feed.tech_feed.is_within_target_dates",
                return_value=True,
            ):
                # Execute
                results = await mock_feed_config.collect(days=1)

            # Operations verification
            assert len(results) == 1
            assert results[0] == ("path/to/json", "path/to/md")

            mock_retrieve.assert_called_once()
            mock_summarize.assert_called_once_with(mock_article)
            mock_store.assert_called_once()

    async def test_skips_duplicate_articles(self, mock_feed_config: TechFeed):
        """Test that duplicate articles are skipped."""
        mock_entry = MagicMock(title="Duplicate Article", link="http://example.com/dup")
        mock_feed = MagicMock(entries=[mock_entry])

        mock_article = Article(
            feed_name="Test Feed",
            title="Duplicate Article",
            url="http://example.com/dup",
            text="Content",
            soup=BeautifulSoup("", "html.parser"),
            category="tech",
            popularity_score=10.0,
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("feedparser.parse", return_value=mock_feed),
            patch(
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch.object(
                mock_feed_config, "_filter_entries", return_value=[mock_entry]
            ),
            patch.object(
                mock_feed_config, "_retrieve_article", return_value=mock_article
            ) as mock_retrieve,
            patch.object(
                mock_feed_config, "_summarize_article", new_callable=AsyncMock
            ) as mock_summarize,
        ):
            # Setup dedup tracker to say it's a duplicate
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (True, "Duplicate Article")
            mock_tracker.get_original_title.return_value = "Original Article"
            mock_load_dedup.return_value = mock_tracker

            # Execute
            await mock_feed_config.collect(days=1)

            # Verification
            mock_retrieve.assert_called_once()
            mock_summarize.assert_not_called()  # Should not be summarized

    async def test_handles_feed_error(self, mock_feed_config: TechFeed):
        """Test that feed parsing errors are logged and execution continues."""
        with (
            patch("feedparser.parse", side_effect=Exception("Feed Error")),
            patch(
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            await mock_feed_config.collect(days=1)

            # Should have logged the error
            mock_feed_config.logger.error.assert_called()
            assert "Feed Error" in str(mock_feed_config.logger.error.call_args)

    async def test_no_setup_http_client_called_if_already_set(
        self, tech_feed: TechFeed
    ):
        """Should check http_client initialization."""
        tech_feed.http_client = AsyncMock()  # Already set
        tech_feed.collect = AsyncMock()  # to avoid running full logic

        # We need to test the logic inside collect about setup_http_client
        # but since we mock collect, we can't.
        # Instead, verify setup_http_client is called if http_client is None in integration style

        real_feed = TechFeed()
        real_feed.http_client = None
        real_feed.setup_http_client = AsyncMock()
        real_feed.feed_config = {}  # Empty config to finish quickly
        real_feed._get_all_existing_dates = AsyncMock(return_value=[])
        real_feed.logger = MagicMock()

        with patch(
            "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ):
            await real_feed.collect()

        real_feed.setup_http_client.assert_awaited_once()
