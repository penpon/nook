from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.note.note_explorer import NoteExplorer


@pytest.fixture
def mock_feed_config():
    return {
        "design": ["https://note.com/topic/design/rss"],
        "tech": ["https://note.com/topic/tech/rss"],
    }


@pytest.fixture
def note_explorer(monkeypatch, mock_feed_config):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    explorer = NoteExplorer()
    explorer.feed_config = mock_feed_config
    explorer.http_client = AsyncMock()
    explorer.storage = AsyncMock()
    explorer.logger = MagicMock()
    return explorer


class TestSelectTopArticles:
    def test_select_top_articles_limit(self, note_explorer):
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

        selected = note_explorer._select_top_articles(articles, limit=3)
        assert len(selected) == 3
        # Should be sorted by popularity desc
        assert selected[0].popularity_score == 9
        assert selected[1].popularity_score == 8

    def test_select_top_articles_empty(self, note_explorer):
        assert note_explorer._select_top_articles([]) == []


class TestRetrieveArticle:
    @pytest.mark.asyncio
    async def test_retrieve_article_success(self, note_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        entry.summary = "Summary"
        mock_response = MagicMock()
        mock_response.text = (
            '<html><meta name="description" content="Meta Description"></html>'
        )
        note_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.note.note_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            note_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await note_explorer._retrieve_article(entry, "Test Feed", "tech")

            assert article is not None
            assert article.title == "Test Article"
            assert article.text == "Summary"  # Entry summary preference
            assert article.popularity_score == 123.0
            assert article.category == "tech"

    @pytest.mark.asyncio
    async def test_retrieve_article_fallback_meta(self, note_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary  # ensure no summary

        mock_response = MagicMock()
        mock_response.text = (
            '<html><meta name="description" content="Meta Desc"></html>'
        )
        note_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.note.note_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            note_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await note_explorer._retrieve_article(entry, "Feed", "cat")

            assert article.text == "Meta Desc"

    @pytest.mark.asyncio
    async def test_retrieve_article_fallback_paragraphs(self, note_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        entry.title = "Test Article"
        del entry.summary

        mock_response = MagicMock()
        mock_response.text = "<html><body><p>P1</p><p>P2</p></body></html>"
        note_explorer.http_client.get.return_value = mock_response

        with patch(
            "nook.services.explorers.note.note_explorer.parse_entry_datetime"
        ) as mock_parse:
            mock_parse.return_value = datetime(2023, 1, 1, 12, 0, 0)
            note_explorer._extract_popularity = MagicMock(return_value=123.0)

            article = await note_explorer._retrieve_article(entry, "Feed", "cat")

            assert "P1" in article.text
            assert "P2" in article.text

    @pytest.mark.asyncio
    async def test_retrieve_article_network_error(self, note_explorer):
        entry = MagicMock()
        entry.link = "http://example.com/article"
        note_explorer.http_client.get.side_effect = Exception("Network Error")

        article = await note_explorer._retrieve_article(entry, "Test Feed", "tech")
        assert article is None


class TestCollect:
    @pytest.mark.asyncio
    async def test_collect_flow(self, note_explorer):
        note_explorer.setup_http_client = AsyncMock()
        note_explorer.feed_config = {"design": ["http://url"]}
        note_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.return_value = (False, "Title")

        with (
            patch(
                "nook.services.explorers.note.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch(
                "nook.services.explorers.note.note_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.note.note_explorer.is_within_target_dates",
                return_value=True,
            ),
            patch(
                "nook.services.explorers.note.note_explorer.target_dates_set"
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
                category="tech",
                text="content",
                soup=None,
                published_at=datetime(2023, 1, 1),
                popularity_score=10,
                feed_name="Feed",
            )
            note_explorer._retrieve_article = AsyncMock(return_value=mock_article)
            note_explorer._filter_entries = MagicMock(side_effect=lambda e, *a: list(e))

            note_explorer._summarize_article = AsyncMock()
            note_explorer._store_summaries_for_date = AsyncMock(
                return_value=("path.json", "path.md")
            )
            note_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": [mock_article]}
            )
            note_explorer.storage.load = AsyncMock(return_value=None)

            mock_target_dates_set.return_value = {date(2023, 1, 1)}

            result = await note_explorer.collect(days=1)

            assert len(result) == 1
            assert result[0] == ("path.json", "path.md")
            note_explorer._group_articles_by_date.assert_called_once_with(
                [mock_article]
            )

    @pytest.mark.asyncio
    async def test_collect_skip_duplicates(self, note_explorer):
        note_explorer.setup_http_client = AsyncMock()
        note_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.side_effect = (
            lambda t: (True, t) if t == "Dup" else (False, t)
        )
        mock_dedup.get_original_title.return_value = "Original"

        with (
            patch(
                "nook.services.explorers.note.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_dedup,
            patch(
                "nook.services.explorers.note.note_explorer.feedparser.parse"
            ) as mock_parse,
            patch(
                "nook.services.explorers.note.note_explorer.is_within_target_dates",
                return_value=True,
            ),
        ):
            mock_load_dedup.return_value = mock_dedup
            mock_parse.return_value = MagicMock(
                entries=[MagicMock(title="Dup", link="http://dup")]
            )

            mock_article = Article(
                title="Dup",
                url="http://dup",
                category="tech",
                text="content",
                soup=None,
                published_at=datetime(2023, 1, 1),
                popularity_score=10,
                feed_name="Feed",
            )
            note_explorer._retrieve_article = AsyncMock(return_value=mock_article)
            note_explorer._filter_entries = MagicMock(side_effect=lambda e, *a: list(e))

            note_explorer._group_articles_by_date = MagicMock(return_value={})

            await note_explorer.collect(days=1)

            # Should skip adding to candidate_articles, implying _group_articles_by_date receives empty list (if only duplicates)
            note_explorer._group_articles_by_date.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_collect_existing_files(self, note_explorer):
        # Note Explorer has same logic as Qiita: iterates sorted(articles_by_date.keys())
        # So we must mock _group_articles_by_date to return a key to trigger existing file check.
        note_explorer.setup_http_client = AsyncMock()
        note_explorer._get_all_existing_dates = AsyncMock(return_value=[])

        with (
            patch(
                "nook.services.explorers.note.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch(
                "nook.services.explorers.note.note_explorer.target_dates_set",
                return_value={date(2023, 1, 1)},
            ),
            patch(
                "nook.services.explorers.note.note_explorer.feedparser.parse"
            ) as mock_parse,
        ):
            mock_parse.return_value = MagicMock(entries=[])
            note_explorer._group_articles_by_date = MagicMock(
                return_value={"2023-01-01": []}
            )

            note_explorer.storage.load = AsyncMock(return_value='[{"title": "algo"}]')

            saved = await note_explorer.collect(days=1)

            assert len(saved) == 0
            note_explorer.storage.load.assert_awaited_with("2023-01-01.json")
            note_explorer._group_articles_by_date.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_store_summaries(self, note_explorer):
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
            "nook.core.storage.daily_snapshot.store_daily_snapshots",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = [("f.json", "f.md")]
            res = await note_explorer._store_summaries(articles, target_dates)
            assert res == [("f.json", "f.md")]

    @pytest.mark.asyncio
    async def test_store_summaries_empty(self, note_explorer):
        res = await note_explorer._store_summaries([], [])
        assert res == []

    def test_load_existing_titles_method(self, note_explorer):
        # Testing the unused _load_existing_titles method specifically
        note_explorer.storage.load_markdown = MagicMock(
            return_value="### [Title 1](url)\n### [Title 2](url)"
        )
        tracker = note_explorer._load_existing_titles()
        assert tracker.is_duplicate("Title 1")[0] is True
        assert tracker.is_duplicate("Title 2")[0] is True

    def test_load_existing_titles_method_error(self, note_explorer):
        note_explorer.storage.load_markdown = MagicMock(side_effect=Exception("Error"))
        tracker = note_explorer._load_existing_titles()
        # Should return empty tracker, not raise
        assert tracker.count() == 0
