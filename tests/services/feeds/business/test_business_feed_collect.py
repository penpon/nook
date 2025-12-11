"""Tests for BusinessFeed collect flow and article retrieval logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.base.base_feed_service import Article
from nook.services.feeds.business.business_feed import BusinessFeed


@pytest.fixture
def business_feed(monkeypatch: pytest.MonkeyPatch) -> BusinessFeed:
    """Create a BusinessFeed instance with mocked dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    feed = BusinessFeed()
    feed.http_client = AsyncMock()
    feed.gpt_client = AsyncMock()
    feed.storage = AsyncMock()
    feed.logger = MagicMock()
    # 重複排除トラッカーの読み込みをモック化
    feed._get_all_existing_dates = AsyncMock(return_value=[])
    return feed


@pytest.mark.asyncio
class TestRetrieveArticle:
    """Tests for _retrieve_article method."""

    async def test_returns_none_if_no_url(self, business_feed: BusinessFeed) -> None:
        """Should return None if entry has no link."""
        entry = MagicMock()
        del entry.link

        result = await business_feed._retrieve_article(entry, "Test Feed", "business")
        assert result is None

    async def test_returns_none_if_non_japanese(
        self, business_feed: BusinessFeed
    ) -> None:
        """Should return None if content is not Japanese."""
        entry = MagicMock(link="http://example.com/en", title="English Business News")
        del entry.summary
        business_feed.http_client.get.return_value = MagicMock(
            text="<html><body>English Content</body></html>"
        )

        # _detect_japanese_contentがFalseを返すようにモック化
        with patch.object(
            business_feed, "_detect_japanese_content", return_value=False
        ):
            result = await business_feed._retrieve_article(
                entry, "Test Feed", "business"
            )

        assert result is None
        business_feed.logger.debug.assert_called_with(
            "非日本語記事をスキップ: English Business News"
        )

    async def test_returns_article_success(self, business_feed: BusinessFeed) -> None:
        """Should return Article object on success."""
        entry = MagicMock(link="http://example.com/jp", title="ビジネスニュース")
        del entry.summary
        entry.published_parsed = (2024, 1, 1, 9, 0, 0, 0, 0, 0)
        business_feed.http_client.get.return_value = MagicMock(
            text="<html><body><p>株価が上昇しました。</p></body></html>"
        )

        with patch.object(business_feed, "_detect_japanese_content", return_value=True):
            result = await business_feed._retrieve_article(
                entry, "Test Feed", "business"
            )

        assert isinstance(result, Article)
        assert result.title == "ビジネスニュース"
        assert result.text == "株価が上昇しました。"
        assert result.url == "http://example.com/jp"
        assert result.category == "business"

    async def test_handles_exception_gracefully(
        self, business_feed: BusinessFeed
    ) -> None:
        """Should return None and log error on exception."""
        entry = MagicMock(link="http://example.com/error")
        business_feed.http_client.get.side_effect = Exception("Connection Failed")

        result = await business_feed._retrieve_article(entry, "Test Feed", "business")

        assert result is None
        business_feed.logger.error.assert_called_once()
        assert "Connection Failed" in str(business_feed.logger.error.call_args)


@pytest.mark.asyncio
class TestCollect:
    """Tests for collect method."""

    @pytest.fixture
    def mock_feed_config(self, business_feed: BusinessFeed):
        """Mock feed configuration."""
        business_feed.feed_config = {"business": ["http://business-feed.com/rss"]}
        return business_feed

    async def test_collect_flow_success(self, mock_feed_config: BusinessFeed):
        """Test successful collection flow."""
        mock_entry = MagicMock(
            title="New Business Article", link="http://example.com/biz"
        )
        mock_feed = MagicMock(entries=[mock_entry])
        mock_feed.feed.title = "Business Feed"

        mock_article = Article(
            feed_name="Business Feed",
            title="New Business Article",
            url="http://example.com/biz",
            text="Market update",
            soup=BeautifulSoup("", "html.parser"),
            category="business",
            popularity_score=20.0,
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("feedparser.parse", return_value=mock_feed),
            patch(
                "nook.services.feeds.business.business_feed.load_existing_titles_from_storage",
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
            patch(
                "nook.services.feeds.business.business_feed.is_within_target_dates",
                return_value=True,
            ),
        ):
            # 重複排除トラッカーをセットアップ
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (False, "New Business Article")
            mock_load_dedup.return_value = mock_tracker

            # storeの戻り値をセットアップ
            mock_store.return_value = ("var/data/business.json", "var/data/business.md")

            # 実行
            results = await mock_feed_config.collect(days=1)

            # 検証
            assert len(results) == 1
            assert results[0] == ("var/data/business.json", "var/data/business.md")

            mock_retrieve.assert_called_once()
            mock_summarize.assert_called_once_with(mock_article)
            mock_store.assert_called_once()

    async def test_skips_duplicate_articles(self, mock_feed_config: BusinessFeed):
        """Test that duplicate articles are skipped."""
        mock_entry = MagicMock(
            title="Duplicate Biz News", link="http://example.com/dup"
        )
        mock_feed = MagicMock(entries=[mock_entry])

        mock_article = Article(
            feed_name="Business Feed",
            title="Duplicate Biz News",
            url="http://example.com/dup",
            text="Old news",
            soup=BeautifulSoup("", "html.parser"),
            category="business",
            popularity_score=5.0,
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("feedparser.parse", return_value=mock_feed),
            patch(
                "nook.services.feeds.business.business_feed.load_existing_titles_from_storage",
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
            # 重複排除トラッカーをセットアップ
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (True, "Duplicate Biz News")
            mock_tracker.get_original_title.return_value = "Original Biz News"
            mock_load_dedup.return_value = mock_tracker

            # 実行
            await mock_feed_config.collect(days=1)

            # 検証
            mock_retrieve.assert_called_once()
            mock_summarize.assert_not_called()

    async def test_handles_feed_error(self, mock_feed_config: BusinessFeed):
        """Test that feed parsing errors are logged."""
        with (
            patch("feedparser.parse", side_effect=Exception("RSS Error")),
            patch(
                "nook.services.feeds.business.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            await mock_feed_config.collect(days=1)

            mock_feed_config.logger.error.assert_called()
            assert "RSS Error" in str(mock_feed_config.logger.error.call_args)
