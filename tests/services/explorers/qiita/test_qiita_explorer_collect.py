from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.qiita.qiita_explorer import QiitaExplorer


@pytest.fixture
def mock_feed_config():
    return {
        "python": ["https://qiita.com/tags/python/feed"],
        "rust": ["https://qiita.com/tags/rust/feed"],
    }


@pytest.fixture
def qiita_explorer(monkeypatch, mock_feed_config):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    explorer = QiitaExplorer()
    explorer.feed_config = mock_feed_config
    explorer.http_client = AsyncMock()
    explorer.storage = AsyncMock()
    explorer.logger = MagicMock()
    return explorer


class TestSelectTopArticles:
    def test_select_top_articles_limit(self, qiita_explorer):
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

        selected = qiita_explorer._select_top_articles(articles, limit=3)
        assert len(selected) == 3
        # Should be sorted by popularity desc
        assert selected[0].popularity_score == 9
        assert selected[1].popularity_score == 8

    def test_select_top_articles_empty(self, qiita_explorer):
        assert qiita_explorer._select_top_articles([]) == []


class TestRetrieveArticle:
    @pytest.mark.asyncio
    async def test_retrieve_article_success(self, qiita_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        entry.summary = "Summary"
        mock_response = MagicMock()
        mock_response.text = (
            '<html><meta name="description" content="Meta Description"></html>'
        )
        qiita_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.qiita.qiita_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            qiita_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await qiita_explorer._retrieve_article(
                entry, "Test Feed", "python"
            )

            assert article is not None
            assert article.title == "Test Article"
            assert article.popularity_score == 123.0
            assert article.category == "python"

    @pytest.mark.asyncio
    async def test_retrieve_article_fallback_meta(self, qiita_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary  # ensure no summary

        mock_response = MagicMock()
        # Mock soup find result
        mock_response.text = (
            '<html><meta name="description" content="Meta Desc"></html>'
        )
        qiita_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.qiita.qiita_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            qiita_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await qiita_explorer._retrieve_article(entry, "Feed", "cat")

            assert article.text == "Meta Desc"

    @pytest.mark.asyncio
    async def test_retrieve_article_fallback_paragraphs(self, qiita_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary

        mock_response = MagicMock()
        mock_response.text = "<html><body><p>P1</p><p>P2</p></body></html>"
        qiita_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.qiita.qiita_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            qiita_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await qiita_explorer._retrieve_article(entry, "Feed", "cat")

            assert "P1" in article.text
            assert "P2" in article.text

    @pytest.mark.asyncio
    async def test_retrieve_article_network_error(self, qiita_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        qiita_explorer.http_client.get.side_effect = Exception("Network Error")

        article = await qiita_explorer._retrieve_article(entry, "Test Feed", "python")
        assert article is None


class TestCollect:
    # ... existing tests ...

    @pytest.mark.asyncio
    async def test_collect_existing_files(self, qiita_explorer):
        qiita_explorer.setup_http_client = AsyncMock()
        qiita_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        with (
            patch(
                "nook.services.explorers.qiita.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch(
                "nook.services.explorers.qiita.qiita_explorer.target_dates_set",
                return_value={date(2023, 1, 1)},
            ),
            patch(
                "nook.services.explorers.qiita.qiita_explorer.feedparser.parse"
            ) as mock_parse,
        ):
            mock_parse.return_value = MagicMock(entries=[])
            qiita_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": []}
            )

            qiita_explorer.storage.load = AsyncMock(return_value='[{"title": "algo"}]')

            saved = await qiita_explorer.collect(days=1)

            # In Qiita, if no selected articles, it does NOT return the file path in saved_files (unlike Zenn?).
            # Let's check logic:
            # if selected: append to saved_files
            # else: log_no_new_articles
            # So saved_files will be empty
            assert len(saved) == 0

            # But we verified that storage.load was called for "2023-01-01.json"
            qiita_explorer.storage.load.assert_awaited_with("2023-01-01.json")
            qiita_explorer._group_articles_by_date.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_collect_flow(self, qiita_explorer):
        qiita_explorer.setup_http_client = AsyncMock()
        qiita_explorer.feed_config = {"python": ["http://url"]}
        qiita_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.return_value = (False, "Title")

        with (
            patch(
                "nook.services.explorers.qiita.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch(
                "nook.services.explorers.qiita.qiita_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.qiita.qiita_explorer.is_within_target_dates",
                return_value=True,
            ),
            patch(
                "nook.services.explorers.qiita.qiita_explorer.target_dates_set"
            ) as mock_target_dates_set,
        ):
            mock_load_dedup.return_value = mock_dedup

            entry = MagicMock()
            entry.title = "Test Title"
            entry.link = "http://example.com"
            mock_feed = MagicMock()
            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            mock_article = Article(
                title="Test Title",
                url="http://example.com",
                category="python",
                text="content",
                soup=None,
                published_at=datetime(2023, 1, 1),
                popularity_score=10,
                feed_name="Feed",
            )
            qiita_explorer._retrieve_article = AsyncMock(return_value=mock_article)
            qiita_explorer._filter_entries = MagicMock(
                side_effect=lambda e, *a: list(e)
            )

            qiita_explorer._summarize_article = AsyncMock()
            qiita_explorer._store_summaries_for_date = AsyncMock(
                return_value=("path.json", "path.md")
            )
            qiita_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": [mock_article]}
            )
            qiita_explorer.storage.load = AsyncMock(return_value=None)

            mock_target_dates_set.return_value = {date(2023, 1, 1)}

            result = await qiita_explorer.collect(days=1)

            assert len(result) == 1
            assert result[0] == ("path.json", "path.md")
            qiita_explorer._group_articles_by_date.assert_called_once_with(
                [mock_article]
            )

    @pytest.mark.asyncio
    async def test_collect_skip_duplicates(self, qiita_explorer):
        qiita_explorer.setup_http_client = AsyncMock()
        qiita_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.side_effect = (
            lambda t: (True, t) if t == "Dup" else (False, t)
        )
        mock_dedup.get_original_title.return_value = "Original"

        with (
            patch(
                "nook.services.explorers.qiita.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch(
                "nook.services.explorers.qiita.qiita_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.qiita.qiita_explorer.is_within_target_dates",
                return_value=True,
            ),
            patch("nook.services.explorers.qiita.qiita_explorer.target_dates_set"),
        ):
            mock_load_dedup.return_value = mock_dedup

            entry1 = MagicMock(title="Dup", link="http://dup")
            mock_feed = MagicMock()
            mock_feed.entries = [entry1]
            mock_parse.return_value = mock_feed

            mock_article = Article(
                title="Dup",
                url="http://dup",
                category="python",
                text="content",
                soup=None,
                published_at=datetime(2023, 1, 1),
                popularity_score=10,
                feed_name="Feed",
            )
            qiita_explorer._retrieve_article = AsyncMock(return_value=mock_article)
            qiita_explorer._filter_entries = MagicMock(
                side_effect=lambda e, *a: list(e)
            )
            qiita_explorer._unique_articles = []  # Reset ? No, collect creates local list

            # Assuming no other articles, result should be empty if skipped
            # We need to mock _group_articles_by_date return empty or check calls
            qiita_explorer._group_articles_by_date = MagicMock(return_value={})

            result = await qiita_explorer.collect(days=1)

            assert len(result) == 0
            # Ensure _retrieve_article was called but added to candidates = NO
            # We can check _group_articles_by_date call args
            qiita_explorer._group_articles_by_date.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_store_summaries(self, qiita_explorer):
        # Testing _store_summaries which imports store_daily_snapshots locally
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
            "nook.core.storage.daily_snapshot.store_daily_snapshots", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = [("f.json", "f.md")]
            # Note: _store_summaries does local import.
            # unittest.mock.patching 'nook.core.storage.daily_snapshot.store_daily_snapshots' globally should work if it patches the module where function is defined.

            res = await qiita_explorer._store_summaries(articles, target_dates)
            assert res == [("f.json", "f.md")]
