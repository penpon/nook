from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.zenn.zenn_explorer import ZennExplorer


@pytest.fixture
def mock_feed_config():
    return {
        "tech": ["https://zenn.dev/topics/tech/feed"],
        "idea": ["https://zenn.dev/topics/idea/feed"],
    }


@pytest.fixture
def zenn_explorer(monkeypatch, mock_feed_config):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    explorer = ZennExplorer()
    explorer.feed_config = mock_feed_config
    explorer.http_client = AsyncMock()
    explorer.storage = AsyncMock()
    explorer.storage.base_dir = "var/data/zenn_explorer"
    explorer.logger = MagicMock()
    return explorer


class TestSelectTopArticles:
    def test_select_top_articles_limit(self, zenn_explorer):
        articles = [
            Article(
                title=f"Title {i}",
                url=f"http://example.com/{i}",
                popularity_score=i,
                feed_name="test",
                category="test",
                text="text",
                soup=None,
                published_at=datetime.now(),
            )
            for i in range(10)
        ]
        # sort desc by popularity (9 to 0)

        selected = zenn_explorer._select_top_articles(articles, limit=3)
        assert len(selected) == 3
        assert selected[0].popularity_score == 9
        assert selected[1].popularity_score == 8
        assert selected[2].popularity_score == 7

    def test_select_top_articles_default_limit(self, zenn_explorer):
        articles = [
            Article(
                title=f"Title {i}",
                url=f"http://example.com/{i}",
                popularity_score=i,
                feed_name="test",
                category="test",
                text="text",
                soup=None,
                published_at=datetime.now(),
            )
            for i in range(20)
        ]
        zenn_explorer.SUMMARY_LIMIT = 5
        selected = zenn_explorer._select_top_articles(articles)
        assert len(selected) == 5
        assert selected[0].popularity_score == 19

    def test_select_top_articles_empty(self, zenn_explorer):
        assert zenn_explorer._select_top_articles([]) == []


class TestRetrieveArticle:
    @pytest.mark.asyncio
    async def test_retrieve_article_success(self, zenn_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        entry.summary = "Summary"
        # Setup mock http response
        mock_response = MagicMock()
        mock_response.text = (
            '<html><meta name="description" content="Meta Description"></html>'
        )
        zenn_explorer.http_client.get.return_value = mock_response

        # Mock parse_entry_datetime to return a fixed datetime
        with patch(
            "nook.services.explorers.zenn.zenn_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)

            # Mock _extract_popularity
            zenn_explorer._extract_popularity = MagicMock(return_value=100.0)

            article = await zenn_explorer._retrieve_article(entry, "Test Feed", "tech")

            assert article is not None
            assert article.title == "Test Article"
            assert article.url == "http://example.com/article"
            assert article.text == "Summary"  # favor summary if present
            assert article.popularity_score == 100.0
            assert article.category == "tech"

    @pytest.mark.asyncio
    async def test_retrieve_article_no_summary_falback_meta_description(
        self, zenn_explorer
    ):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary  # ensure no summary

        mock_response = MagicMock()
        mock_response.text = (
            '<html><meta name="description" content="Meta Description"></html>'
        )
        zenn_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.zenn.zenn_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            zenn_explorer._extract_popularity = MagicMock(return_value=10.0)

            article = await zenn_explorer._retrieve_article(entry, "Test Feed", "tech")

            assert article.text == "Meta Description"

    @pytest.mark.asyncio
    async def test_retrieve_article_fallback_paragraphs(self, zenn_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary

        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Para 1</p><p>Para 2</p></body></html>"
        zenn_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.zenn.zenn_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            zenn_explorer._extract_popularity = MagicMock(return_value=10.0)

            article = await zenn_explorer._retrieve_article(entry, "Test Feed", "tech")

            assert "Para 1" in article.text
            assert "Para 2" in article.text

    @pytest.mark.asyncio
    async def test_retrieve_article_network_error(self, zenn_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        zenn_explorer.http_client.get.side_effect = Exception("Network Error")

        article = await zenn_explorer._retrieve_article(entry, "Test Feed", "tech")
        assert article is None


class TestCollect:
    @pytest.mark.asyncio
    async def test_collect_flow(self, zenn_explorer):
        # Mock dependencies
        zenn_explorer.setup_http_client = AsyncMock()
        zenn_explorer.feed_config = {"tech": ["http://url"]}
        zenn_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        # Mock DedupTracker
        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.return_value = (False, "Title")

        with (
            patch(
                "nook.services.explorers.zenn.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch(
                "nook.services.explorers.zenn.zenn_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.zenn.zenn_explorer.is_within_target_dates",
                return_value=True,
            ),
            patch(
                "nook.services.explorers.zenn.zenn_explorer.target_dates_set"
            ) as mock_target_dates_set,
            patch("nook.services.explorers.zenn.zenn_explorer.group_records_by_date"),
        ):  # we might not need this if we rely on _store_summaries logic but wait, group_records_by_date is imported from daily_snapshot module, but zenn_explorer imports it. Patching where it is used.
            mock_load_dedup.return_value = mock_dedup

            # Setup feed entries
            entry = MagicMock()
            entry.title = "Test Title"
            entry.link = "http://example.com"
            mock_feed = MagicMock()
            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            # Setup _retrieve_article
            mock_article = Article(
                title="Test Title",
                url="http://example.com",
                category="tech",
                text="content",
                soup=None,
                published_at=datetime(2023, 1, 1),
                popularity_score=10,
                feed_name="Feed",
            )
            # Setup _filter_entries to pass everything
            zenn_explorer._filter_entries = MagicMock(side_effect=lambda e, *a: list(e))

            # Setup _retrieve_article
            zenn_explorer._retrieve_article = AsyncMock(return_value=mock_article)

            # Setup _summarize_article
            zenn_explorer._summarize_article = AsyncMock()

            # Setup _store_summaries_for_date
            zenn_explorer._store_summaries_for_date = AsyncMock(
                return_value=("path.json", "path.md")
            )

            # Setup storage load to return nothing (no existing files)
            zenn_explorer.storage.load = AsyncMock(return_value=None)

            # Target Dates
            target_date = date(2023, 1, 1)
            mock_target_dates_set.return_value = {target_date}

            # Mock _group_articles_by_date manually since it relies on Article.published_at
            # Actually we can let the real method run if Article is correct, but safer to mock for unit test
            # But the code calls self._group_articles_by_date which is a method of BaseFeedService??
            # Let's check BaseFeedService.. it's likely inherited.
            # Ideally we run the inherited logic or mock it.
            # Let's mock it to control the flow.
            zenn_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": [mock_article]}
            )

            result = await zenn_explorer.collect(days=1)

            assert len(result) == 1
            assert result[0] == ("path.json", "path.md")
            zenn_explorer._group_articles_by_date.assert_called_once_with(
                [mock_article]
            )
            zenn_explorer._summarize_article.assert_awaited()
            zenn_explorer._store_summaries_for_date.assert_awaited()

    @pytest.mark.asyncio
    async def test_collect_feed_exception(self, zenn_explorer):
        # Mock setup
        zenn_explorer.setup_http_client = AsyncMock()
        zenn_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        with (
            patch(
                "nook.services.explorers.zenn.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch(
                "nook.services.explorers.zenn.zenn_explorer.feedparser.parse"
            ) as mock_parse,
        ):
            mock_parse.side_effect = Exception("Feed Error")
            # Should not raise exception, but log error
            await zenn_explorer.collect(days=1)
            # success if no error raised

    @pytest.mark.asyncio
    async def test_collect_skips(self, zenn_explorer):
        # Test dedup skip and date skip and retrieval failure
        zenn_explorer.setup_http_client = AsyncMock()
        zenn_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        mock_dedup = MagicMock()
        # First call: not duplicate (will be skipped by date later?), Second: duplicate, Third: not dup, date valid, but retrieve fail
        # Wait, inside loop order:
        # 1. Retrieve article
        # 2. Dedup check (if article retrieved)
        # 3. Date check

        with (
            patch(
                "nook.services.explorers.zenn.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch(
                "nook.services.explorers.zenn.zenn_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.zenn.zenn_explorer.is_within_target_dates"
            ) as mock_date_check,
            patch(
                "nook.services.explorers.zenn.zenn_explorer.target_dates_set"
            ) as mock_target_dates_set,
        ):
            mock_load.return_value = mock_dedup
            mock_target_dates_set.return_value = {date(2023, 1, 1)}

            entry1 = MagicMock(title="Valid", link="http://1")
            entry2 = MagicMock(title="Dup", link="http://2")
            entry3 = MagicMock(title="Old", link="http://3")

            mock_feed = MagicMock()
            mock_feed.entries = [entry1, entry2, entry3]
            mock_parse.return_value = mock_feed

            # Setup dedup: "Dup" is duplicate
            mock_dedup.is_duplicate.side_effect = (
                lambda t: (True, t) if t == "Dup" else (False, t)
            )
            mock_dedup.get_original_title.return_value = "Original"

            # Setup date check: "Old" is old (False), "Valid" is new (True)
            # is_within_target_dates(published_at, dates)
            # We need to map calls.
            # Logic: retrieve -> dedup -> date

            article1 = Article(
                title="Valid",
                url="http://1",
                text="",
                soup=None,
                published_at=datetime.now(),
                popularity_score=1,
                feed_name="",
                category="",
            )
            article2 = Article(
                title="Dup",
                url="http://2",
                text="",
                soup=None,
                published_at=datetime.now(),
                popularity_score=1,
                feed_name="",
                category="",
            )
            article3 = Article(
                title="Old",
                url="http://3",
                text="",
                soup=None,
                published_at=datetime.now(),
                popularity_score=1,
                feed_name="",
                category="",
            )

            zenn_explorer._retrieve_article = AsyncMock(
                side_effect=[article1, article2, article3]
            )
            zenn_explorer._filter_entries = MagicMock(side_effect=lambda e, *a: list(e))

            # Date check mock
            zenn_explorer.storage.load.return_value = None
            mock_date_check.side_effect = [
                True,
                True,
                False,
            ]  # Valid=True, Dup=(skipped before date check?), Old=False
            # Wait, logic is: retrieve -> dedup check -> date check.
            # So Dup will be skipped at dedup, so date check won't be called for it.
            # First article is Valid (True), second is Invalid (False)
            mock_date_check.side_effect = [True, False]

            # Move mock setup before the call
            zenn_explorer._summarize_article = AsyncMock()
            zenn_explorer._store_summaries_for_date = AsyncMock(return_value=("a", "b"))
            zenn_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": [article1]}
            )

            await zenn_explorer.collect(days=1)

            # Assertion
            zenn_explorer._group_articles_by_date.assert_called_once_with([article1])
            zenn_explorer._summarize_article.assert_awaited()

    @pytest.mark.asyncio
    async def test_collect_existing_files_no_new(self, zenn_explorer):
        zenn_explorer.setup_http_client = AsyncMock()
        zenn_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        with (
            patch(
                "nook.services.explorers.zenn.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch(
                "nook.services.explorers.zenn.zenn_explorer.target_dates_set",
                return_value={date(2023, 1, 1)},
            ),
            patch(
                "nook.services.explorers.zenn.zenn_explorer.feedparser.parse"
            ) as mock_parse,
        ):
            mock_parse.return_value = MagicMock(entries=[])  # No entries
            zenn_explorer._group_articles_by_date = MagicMock(return_value={})

            # Mock storage load success for checking existing
            zenn_explorer.storage.load = AsyncMock(return_value='[{"title": "algo"}]')

            saved = await zenn_explorer.collect(days=1)

            # Should append existing file path
            assert len(saved) == 1
            assert "var/data/zenn_explorer/2023-01-01.json" in saved[0][0]
            zenn_explorer._group_articles_by_date.assert_called_once_with([])


class TestOtherMethods:
    def test_load_existing_titles(self, zenn_explorer):
        zenn_explorer.storage.load_markdown = MagicMock(
            return_value="### [Title 1]\n### [Title 2]"
        )
        tracker = zenn_explorer._load_existing_titles()
        assert tracker.is_duplicate("Title 1")[0] is True
        assert tracker.is_duplicate("Title 2")[0] is True

    @pytest.mark.asyncio
    async def test_store_summaries(self, zenn_explorer):
        # Testing the unused/utility method just for coverage
        articles = [
            Article(
                title="T",
                url="u",
                text="t",
                soup=None,
                published_at=datetime.now(),
                popularity_score=1,
                feed_name="f",
                category="c",
            )
        ]
        target_dates = [date(2023, 1, 1)]

        with patch(
            "nook.services.explorers.zenn.zenn_explorer.store_daily_snapshots",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = [("f.json", "f.md")]
            res = await zenn_explorer._store_summaries(articles, target_dates)
            assert res == [("f.json", "f.md")]
