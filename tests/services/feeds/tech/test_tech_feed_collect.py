"""Tests for TechFeed collect flow and article retrieval logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.base.base_feed_service import Article
from nook.services.feeds.tech.tech_feed import TechFeed


@pytest.fixture
def tech_feed(monkeypatch: pytest.MonkeyPatch) -> TechFeed:
    """Create a TechFeed instance with mocked dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    feed = TechFeed()
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

    async def test_returns_none_if_no_url(self, tech_feed: TechFeed) -> None:
        """Should return None if entry has no link."""
        entry = MagicMock()
        del entry.link

        result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")
        assert result is None

    async def test_returns_none_if_non_japanese(self, tech_feed: TechFeed) -> None:
        """Should return None if content is not Japanese."""
        entry = MagicMock(link="http://example.com", title="English Title")
        del entry.summary  # summaryが存在しない場合のフェッチをトリガー
        tech_feed.http_client.get.return_value = MagicMock(text="<html><body>English Content</body></html>")

        # _detect_japanese_contentがFalseを返すようにモック化
        with patch.object(tech_feed, "_detect_japanese_content", return_value=False):
            result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert result is None
        tech_feed.logger.debug.assert_called_with("非日本語記事をスキップ: English Title")

    async def test_returns_article_success(self, tech_feed: TechFeed) -> None:
        """Should return Article object on success."""
        entry = MagicMock(link="http://example.com/1", title="日本語タイトル")
        # summaryをNoneに明示的に設定し、メタディスクリプションまたは本文へのフォールバックを確認
        del entry.summary
        entry.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 0, 0)
        tech_feed.http_client.get.return_value = MagicMock(text="<html><body><p>日本語の本文です。</p></body></html>")

        with patch.object(tech_feed, "_detect_japanese_content", return_value=True):
            result = await tech_feed._retrieve_article(entry, "Test Feed", "tech")

        assert isinstance(result, Article)
        assert result.title == "日本語タイトル"
        assert result.text == "日本語の本文です。"
        assert result.url == "http://example.com/1"

    async def test_returns_article_with_summary_from_entry(self, tech_feed: TechFeed) -> None:
        """Should use summary from entry if available."""
        entry = MagicMock(link="http://example.com/1", title="日本語タイトル")
        entry.summary = "Entry Summary"  # summaryを明示的に設定
        entry.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 0, 0)
        tech_feed.http_client.get.return_value = MagicMock(text="<html>Some html</html>")

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
        # エラーメッセージの先頭引数を直接検証
        call_msg = tech_feed.logger.error.call_args[0][0]
        assert "Network Error" in call_msg


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
        # feedparserをモック化
        mock_entry = MagicMock(title="New Article", link="http://example.com/new")
        # _filter_entriesの日付フィルタをバイパスする必要がある
        # _filter_entriesをモック化するか、target_datesを適切に設定する
        # 簡略化のため_filter_entriesをモック化

        mock_feed = MagicMock(entries=[mock_entry])
        mock_feed.feed.title = "Test Feed"

        # 依存関係をモック化
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
                "nook.services.feeds.tech.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch.object(mock_feed_config, "_filter_entries", return_value=[mock_entry]),
            patch.object(
                mock_feed_config,
                "_retrieve_article",
                new_callable=AsyncMock,
            ) as mock_retrieve,
            patch.object(mock_feed_config, "_summarize_article", new_callable=AsyncMock) as mock_summarize,
            patch.object(mock_feed_config, "_store_summaries_for_date", new_callable=AsyncMock) as mock_store,
        ):
            mock_retrieve.return_value = mock_article

            # 重複排除トラッカーのモックをセットアップ
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (False, "New Article")
            mock_load_dedup.return_value = mock_tracker

            # storeの戻り値をセットアップ
            mock_store.return_value = ("path/to/json", "path/to/md")

            # Articleをモック化しているためis_within_target_datesをモック化
            with patch(
                "nook.services.feeds.tech.tech_feed.is_within_target_dates",
                return_value=True,
            ):
                # 実行
                results = await mock_feed_config.collect(days=1)

            # 検証
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
                "nook.services.feeds.tech.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch.object(mock_feed_config, "_filter_entries", return_value=[mock_entry]),
            patch.object(mock_feed_config, "_retrieve_article", return_value=mock_article) as mock_retrieve,
            patch.object(mock_feed_config, "_summarize_article", new_callable=AsyncMock) as mock_summarize,
        ):
            mock_retrieve.return_value = mock_article

            # duplicateとしてマークされるように重複排除トラッカーをセットアップ
            mock_tracker = MagicMock()
            mock_tracker.is_duplicate.return_value = (True, "Duplicate Article")
            mock_tracker.get_original_title.return_value = "Original Article"
            mock_load_dedup.return_value = mock_tracker

            # 実行
            await mock_feed_config.collect(days=1)

            # 検証
            mock_retrieve.assert_called_once()
            mock_summarize.assert_not_called()  # 要約されるべきではない

    async def test_handles_feed_error(self, mock_feed_config: TechFeed):
        """Test that feed parsing errors are logged and execution continues."""
        with (
            patch("feedparser.parse", side_effect=Exception("Feed Error")),
            patch(
                "nook.services.feeds.tech.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            await mock_feed_config.collect(days=1)

            # エラーがログに記録されているはず
            mock_feed_config.logger.error.assert_called()
            # エラーメッセージの先頭引数を直接検証
            call_msg = mock_feed_config.logger.error.call_args[0][0]
            assert "Feed Error" in call_msg

    async def test_setup_http_client_called_when_none(self, tech_feed: TechFeed) -> None:
        """http_clientがNoneの場合にsetup_http_clientが呼ばれることを確認。"""
        real_feed = TechFeed()
        real_feed.http_client = None
        real_feed.setup_http_client = AsyncMock()
        real_feed.feed_config = {}  # 空の設定ですぐに終了
        real_feed._get_all_existing_dates = AsyncMock(return_value=[])
        real_feed.logger = MagicMock()

        with patch(
            "nook.services.feeds.tech.tech_feed.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ):
            await real_feed.collect()

        real_feed.setup_http_client.assert_awaited_once()
