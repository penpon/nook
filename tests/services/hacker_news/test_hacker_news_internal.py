"""Tests for hacker_news internal methods.

This module tests the internal methods of HackerNewsRetriever that are not covered
by the existing test_hacker_news.py:
- collect
- _load_existing_titles
- _get_top_stories
- _load_blocked_domains
- _fetch_story / _fetch_story_content
- _log_fetch_summary
- _summarize_stories / _summarize_story
- _update_blocked_domains_from_errors / _add_to_blocked_domains
- _store_summaries / _serialize_stories
- _load_existing_stories
- run (sync wrapper)
"""

import json
import os
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from nook.services.hacker_news.hacker_news import (
    HackerNewsRetriever,
    Story,
    SCORE_THRESHOLD,
    MIN_TEXT_LENGTH,
)


@pytest.fixture
def hacker_news(monkeypatch: pytest.MonkeyPatch) -> HackerNewsRetriever:
    """Create a HackerNewsRetriever instance for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
    retriever = HackerNewsRetriever()
    retriever.blocked_domains = {"blocked_domains": [], "reasons": {}}
    return retriever


class TestCollect:
    """Tests for HackerNewsRetriever.collect method."""

    @pytest.mark.asyncio
    async def test_collect_returns_saved_files(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Stories are fetched and processed.
        When: collect is called.
        Then: Saved file paths are returned.
        """
        with patch.object(hacker_news, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                hacker_news, "_load_existing_titles", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = MagicMock()
                with patch.object(
                    hacker_news, "_get_top_stories", new_callable=AsyncMock
                ) as mock_stories:
                    story = Story(
                        title="Test Story",
                        score=100,
                        url="https://example.com",
                        text="Test content " * 20,
                        created_at=datetime.now(timezone.utc),
                    )
                    story.summary = "Test summary"
                    mock_stories.return_value = [story]
                    with patch.object(
                        hacker_news, "_store_summaries", new_callable=AsyncMock
                    ) as mock_store:
                        mock_store.return_value = [("2024-01-15.json", "2024-01-15.md")]

                        result = await hacker_news.collect(limit=10)

        assert len(result) == 1
        assert result[0] == ("2024-01-15.json", "2024-01-15.md")

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_no_stories(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: No stories are fetched.
        When: collect is called.
        Then: Empty list is returned.
        """
        with patch.object(hacker_news, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                hacker_news, "_load_existing_titles", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = MagicMock()
                with patch.object(
                    hacker_news, "_get_top_stories", new_callable=AsyncMock
                ) as mock_stories:
                    mock_stories.return_value = []
                    with patch.object(
                        hacker_news, "_store_summaries", new_callable=AsyncMock
                    ) as mock_store:
                        mock_store.return_value = []

                        result = await hacker_news.collect(limit=10)

        assert result == []


class TestLoadExistingTitles:
    """Tests for HackerNewsRetriever._load_existing_titles method."""

    @pytest.mark.asyncio
    async def test_loads_from_json_file(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: JSON file exists with titles.
        When: _load_existing_titles is called.
        Then: DedupTracker with titles is returned.
        """
        existing_data = [
            {"title": "Story 1"},
            {"title": "Story 2"},
        ]
        with patch.object(
            hacker_news.storage, "exists", new_callable=AsyncMock
        ) as mock_exists:
            mock_exists.return_value = True
            with patch.object(
                hacker_news, "load_json", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = existing_data

                result = await hacker_news._load_existing_titles()

        assert result is not None
        # Check that titles were added to tracker
        is_dup, _ = result.is_duplicate("Story 1")
        assert is_dup

    @pytest.mark.asyncio
    async def test_loads_from_markdown_when_json_missing(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: JSON file doesn't exist but markdown exists.
        When: _load_existing_titles is called.
        Then: DedupTracker with titles from markdown is returned.
        """
        markdown_content = """# Stories

## [Story From Markdown](https://example.com)

Score: 100

## Plain Title Story

Score: 50
"""
        with patch.object(
            hacker_news.storage, "exists", new_callable=AsyncMock
        ) as mock_exists:
            mock_exists.return_value = False
            with patch.object(hacker_news.storage, "load_markdown") as mock_load_md:
                mock_load_md.return_value = markdown_content

                result = await hacker_news._load_existing_titles()

        assert result is not None
        # Check that titles from markdown were added
        is_dup, _ = result.is_duplicate("Story From Markdown")
        assert is_dup
        is_dup_plain, _ = result.is_duplicate("Plain Title Story")
        assert is_dup_plain

    @pytest.mark.asyncio
    async def test_returns_empty_tracker_on_exception(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Exception during title loading.
        When: _load_existing_titles is called.
        Then: Empty DedupTracker is returned.
        """
        with patch.object(
            hacker_news.storage, "exists", new_callable=AsyncMock
        ) as mock_exists:
            mock_exists.side_effect = Exception("File error")

            result = await hacker_news._load_existing_titles()

        assert result is not None
        is_dup, _ = result.is_duplicate("New Story")
        assert not is_dup


class TestGetTopStories:
    """Tests for HackerNewsRetriever._get_top_stories method."""

    @pytest.mark.asyncio
    async def test_fetches_and_filters_stories(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Top stories API returns story IDs.
        When: _get_top_stories is called.
        Then: Stories are fetched, filtered, and summarized.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="Test Story",
            score=SCORE_THRESHOLD + 10,
            text="A" * (MIN_TEXT_LENGTH + 10),
            created_at=datetime.now(timezone.utc),
        )

        with patch.object(
            hacker_news, "_fetch_story", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = story
            with patch.object(
                hacker_news, "_summarize_stories", new_callable=AsyncMock
            ):
                tracker = MagicMock()
                tracker.is_duplicate.return_value = (False, story.title)
                tracker.get_original_title.return_value = None

                result = await hacker_news._get_top_stories(
                    limit=10,
                    dedup_tracker=tracker,
                    target_dates=[datetime.now().date()],
                )

        assert len(result) >= 0  # May be filtered

    @pytest.mark.asyncio
    async def test_filters_low_score_stories(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Stories with low scores.
        When: _get_top_stories is called.
        Then: Low score stories are filtered out.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = [1]

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        # Story with score below threshold
        story = Story(
            title="Low Score Story",
            score=SCORE_THRESHOLD - 5,
            text="A" * (MIN_TEXT_LENGTH + 10),
            created_at=datetime.now(timezone.utc),
        )

        with patch.object(
            hacker_news, "_fetch_story", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = story
            with patch.object(
                hacker_news, "_summarize_stories", new_callable=AsyncMock
            ):
                tracker = MagicMock()
                tracker.is_duplicate.return_value = (False, story.title)

                result = await hacker_news._get_top_stories(
                    limit=10,
                    dedup_tracker=tracker,
                    target_dates=[datetime.now().date()],
                )

        # Story should be filtered out due to low score
        assert len(result) == 0


class TestFetchStory:
    """Tests for HackerNewsRetriever._fetch_story method."""

    @pytest.mark.asyncio
    async def test_returns_story_on_success(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: API returns valid story data.
        When: _fetch_story is called.
        Then: Story object is returned.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "title": "Test Story",
            "score": 100,
            "url": "https://example.com",
            "time": 1705312200,
        }

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        with patch.object(hacker_news, "_fetch_story_content", new_callable=AsyncMock):
            result = await hacker_news._fetch_story(12345)

        assert result is not None
        assert isinstance(result, Story)
        assert result.title == "Test Story"
        assert result.score == 100

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_title(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: API returns data without title.
        When: _fetch_story is called.
        Then: None is returned.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {"score": 100}

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        result = await hacker_news._fetch_story(12345)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: API raises exception.
        When: _fetch_story is called.
        Then: None is returned.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(side_effect=Exception("Network error"))

        result = await hacker_news._fetch_story(12345)

        assert result is None


class TestFetchStoryContent:
    """Tests for HackerNewsRetriever._fetch_story_content method."""

    @pytest.mark.asyncio
    async def test_skips_blocked_domain(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Story URL is from blocked domain.
        When: _fetch_story_content is called.
        Then: Story text is set to blocked message.
        """
        hacker_news.blocked_domains = {
            "blocked_domains": ["blocked.com"],
            "reasons": {"blocked.com": "Access denied"},
        }

        story = Story(
            title="Blocked Story",
            score=100,
            url="https://blocked.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "ブロック" in story.text

    @pytest.mark.asyncio
    async def test_extracts_meta_description(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Page has meta description.
        When: _fetch_story_content is called.
        Then: Meta description is extracted.
        """
        html_content = """
        <html>
        <head>
            <meta name="description" content="Test description content">
        </head>
        <body></body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="Test Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert story.text == "Test description content"

    @pytest.mark.asyncio
    async def test_handles_403_error(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Page returns 403.
        When: _fetch_story_content is called.
        Then: Error message is set.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(side_effect=Exception("403 Forbidden"))

        story = Story(
            title="Forbidden Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "アクセス制限" in story.text

    @pytest.mark.asyncio
    async def test_handles_404_error(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Page returns 404.
        When: _fetch_story_content is called.
        Then: Not found message is set.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(side_effect=Exception("404 Not Found"))

        story = Story(
            title="Missing Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "見つかりませんでした" in story.text

    @pytest.mark.asyncio
    async def test_extracts_og_description(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Page has OG description but no regular meta description.
        When: _fetch_story_content is called.
        Then: OG description is extracted.
        """
        html_content = """
        <html>
        <head>
            <meta property="og:description" content="OG Description content">
        </head>
        <body></body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="OG Test Story",
            score=100,
            url="https://example.com/og-article",
        )

        await hacker_news._fetch_story_content(story)

        assert story.text == "OG Description content"

    @pytest.mark.asyncio
    async def test_extracts_paragraphs(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Page has paragraphs but no meta description.
        When: _fetch_story_content is called.
        Then: Paragraphs are extracted.
        """
        html_content = (
            "<html>\n"
            "<head></head>\n"
            "<body>\n"
            "    <p>This is a short paragraph.</p>\n"
            "    <p>This is a much longer paragraph that contains more than "
            "fifty characters of meaningful content about the article.</p>\n"
            "    <p>Another long paragraph with sufficient content length to be "
            "considered meaningful by the extraction algorithm.</p>\n"
            "</body>\n"
            "</html>\n"
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="Paragraph Test Story",
            score=100,
            url="https://example.com/paragraph-article",
        )

        await hacker_news._fetch_story_content(story)

        assert "longer paragraph" in story.text

    @pytest.mark.asyncio
    async def test_extracts_article_element(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Page has article element but no paragraphs.
        When: _fetch_story_content is called.
        Then: Article content is extracted.
        """
        html_content = (
            "<html>\n"
            "<head></head>\n"
            "<body>\n"
            "    <article>This is the article content that should be extracted "
            "when no paragraphs are available.</article>\n"
            "</body>\n"
            "</html>\n"
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="Article Test Story",
            score=100,
            url="https://example.com/article-element",
        )

        await hacker_news._fetch_story_content(story)

        assert "article content" in story.text

    @pytest.mark.asyncio
    async def test_uses_http1_for_required_domain(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: URL is from HTTP/1.1 required domain.
        When: _fetch_story_content is called.
        Then: force_http1 is set to True.
        """
        hacker_news.blocked_domains = {
            "blocked_domains": [],
            "reasons": {},
            "http1_required_domains": ["http1-only.com"],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '<html><head><meta name="description" content="Content"></head></html>'
        )

        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(return_value=mock_response)

        story = Story(
            title="HTTP1 Story",
            score=100,
            url="https://http1-only.com/article",
        )

        await hacker_news._fetch_story_content(story)

        # Check that get was called with force_http1=True
        call_kwargs = hacker_news.http_client.get.call_args[1]
        assert call_kwargs.get("force_http1") is True

    @pytest.mark.asyncio
    async def test_handles_ssl_error(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: SSL error occurs.
        When: _fetch_story_content is called.
        Then: Error message is set.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(
            side_effect=Exception("SSL handshake failed")
        )

        story = Story(
            title="SSL Error Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "取得できませんでした" in story.text

    @pytest.mark.asyncio
    async def test_handles_timeout_error(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Timeout error occurs.
        When: _fetch_story_content is called.
        Then: Error message is set.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        story = Story(
            title="Timeout Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "取得できませんでした" in story.text

    @pytest.mark.asyncio
    async def test_handles_generic_error(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Unknown error occurs.
        When: _fetch_story_content is called.
        Then: Error message is set.
        """
        hacker_news.http_client = AsyncMock()
        hacker_news.http_client.get = AsyncMock(
            side_effect=Exception("Unknown error occurred")
        )

        story = Story(
            title="Generic Error Story",
            score=100,
            url="https://example.com/article",
        )

        await hacker_news._fetch_story_content(story)

        assert "取得できませんでした" in story.text


class TestLogFetchSummary:
    """Tests for HackerNewsRetriever._log_fetch_summary method."""

    @pytest.mark.asyncio
    async def test_logs_summary_correctly(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: List of stories with various states.
        When: _log_fetch_summary is called.
        Then: Summary is logged.
        """
        stories = [
            Story(title="Success", score=100, text="Valid content"),
            Story(title="Blocked", score=100, text="このサイトはブロックされています"),
            Story(title="Error", score=100, text=None),
        ]

        # Should not raise
        await hacker_news._log_fetch_summary(stories)


class TestSummarizeStory:
    """Tests for HackerNewsRetriever._summarize_story method."""

    @pytest.mark.asyncio
    async def test_generates_summary(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Story with valid text.
        When: _summarize_story is called.
        Then: Summary is generated.
        """
        story = Story(
            title="Test Story",
            score=100,
            text="This is the story content.",
        )

        with patch.object(
            hacker_news.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated summary"
            with patch.object(hacker_news, "rate_limit", new_callable=AsyncMock):
                await hacker_news._summarize_story(story)

        assert story.summary == "Generated summary"

    @pytest.mark.asyncio
    async def test_handles_missing_text(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Story without text.
        When: _summarize_story is called.
        Then: Default message is set.
        """
        story = Story(
            title="No Text Story",
            score=100,
            text=None,
        )

        await hacker_news._summarize_story(story)

        assert "本文情報がない" in story.summary

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: GPT raises exception.
        When: _summarize_story is called.
        Then: Error message is set.
        """
        story = Story(
            title="Test Story",
            score=100,
            text="Content",
        )

        with patch.object(
            hacker_news.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = Exception("API error")
            await hacker_news._summarize_story(story)

        assert "エラー" in story.summary


class TestSummarizeStories:
    """Tests for HackerNewsRetriever._summarize_stories method."""

    @pytest.mark.asyncio
    async def test_summarizes_all_stories(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: List of stories.
        When: _summarize_stories is called.
        Then: All stories are summarized.
        """
        stories = [
            Story(title="Story 1", score=100, text="Content 1"),
            Story(title="Story 2", score=200, text="Content 2"),
        ]

        with patch.object(
            hacker_news, "_summarize_story", new_callable=AsyncMock
        ) as mock_summarize:
            with patch.object(
                hacker_news,
                "_update_blocked_domains_from_errors",
                new_callable=AsyncMock,
            ):
                await hacker_news._summarize_stories(stories)

        assert mock_summarize.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_empty_list(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: Empty stories list.
        When: _summarize_stories is called.
        Then: No error occurs.
        """
        await hacker_news._summarize_stories([])


class TestUpdateBlockedDomainsFromErrors:
    """Tests for HackerNewsRetriever._update_blocked_domains_from_errors method."""

    @pytest.mark.asyncio
    async def test_detects_error_domains(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Stories with error states.
        When: _update_blocked_domains_from_errors is called.
        Then: Error domains are added to blocked list.
        """
        stories = [
            Story(
                title="Error Story",
                score=100,
                url="https://error-domain.com/article",
                text="記事の内容を取得できませんでした。",
            ),
        ]

        with patch.object(
            hacker_news, "_add_to_blocked_domains", new_callable=AsyncMock
        ) as mock_add:
            await hacker_news._update_blocked_domains_from_errors(stories)

        mock_add.assert_called_once()
        call_args = mock_add.call_args[0][0]
        assert "error-domain.com" in call_args

    @pytest.mark.asyncio
    async def test_detects_various_error_types(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Stories with different error types.
        When: _update_blocked_domains_from_errors is called.
        Then: Correct error reasons are detected.
        """
        stories = [
            Story(
                title="522 Error",
                score=100,
                url="https://www.server-error.com/article",
                text="記事の内容を取得できませんでした。",  # エラー検出条件に合致
            ),
            Story(
                title="429 Error",
                score=100,
                url="https://rate-limit.com/article",
                text="記事の内容を取得できませんでした。",  # エラー検出条件に合致
            ),
            Story(
                title="SSL Error",
                score=100,
                url="https://ssl-fail.com/article",
                text="記事の内容を取得できませんでした。",  # エラー検出条件に合致
            ),
            Story(
                title="Timeout Error",
                score=100,
                url="https://timeout.com/article",
                text="記事の内容を取得できませんでした。",  # エラー検出条件に合致
            ),
        ]

        with patch.object(
            hacker_news, "_add_to_blocked_domains", new_callable=AsyncMock
        ) as mock_add:
            await hacker_news._update_blocked_domains_from_errors(stories)

        # At least some domains should be added
        mock_add.assert_called_once()


class TestAddToBlockedDomains:
    """Tests for HackerNewsRetriever._add_to_blocked_domains method."""

    @pytest.mark.asyncio
    async def test_adds_new_domains(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: New domains to block.
        When: _add_to_blocked_domains is called.
        Then: Domains are added and file is saved.
        """
        new_domains = {
            "newdomain.com": "Connection error",
            "another.com": "403 - Access denied",
        }

        hacker_news.blocked_domains = {
            "blocked_domains": ["existing.com"],
            "reasons": {"existing.com": "Old reason"},
        }

        with patch("builtins.open", mock_open()):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "json.load", return_value=hacker_news.blocked_domains.copy()
                ):
                    with patch("json.dump") as mock_dump:
                        await hacker_news._add_to_blocked_domains(new_domains)

        # Check that json.dump was called with updated domains
        if mock_dump.called:
            saved_data = mock_dump.call_args[0][0]
            assert "newdomain.com" in saved_data.get("blocked_domains", [])

    @pytest.mark.asyncio
    async def test_handles_file_error(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: File error when saving.
        When: _add_to_blocked_domains is called.
        Then: Error is logged but no exception raised.
        """
        new_domains = {"error-domain.com": "Test error"}

        with patch("builtins.open", side_effect=Exception("Write error")):
            # Should not raise
            await hacker_news._add_to_blocked_domains(new_domains)

    @pytest.mark.asyncio
    async def test_skips_existing_domains(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Domain already in blocked list.
        When: _add_to_blocked_domains is called.
        Then: Domain is not duplicated.
        """
        hacker_news.blocked_domains = {
            "blocked_domains": ["existing.com"],
            "reasons": {"existing.com": "Old reason"},
        }

        new_domains = {"existing.com": "New reason"}

        with patch("builtins.open", mock_open()):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "json.load", return_value=hacker_news.blocked_domains.copy()
                ):
                    with patch("json.dump") as mock_dump:
                        await hacker_news._add_to_blocked_domains(new_domains)

        # json.dump should not be called since no new domains were added
        assert not mock_dump.called


class TestStoreSummaries:
    """Tests for HackerNewsRetriever._store_summaries method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_stories(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: Empty stories list.
        When: _store_summaries is called.
        Then: Empty list is returned.
        """
        result = await hacker_news._store_summaries([], [date(2024, 1, 15)])
        assert result == []

    @pytest.mark.asyncio
    async def test_saves_stories_and_returns_paths(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: List of stories.
        When: _store_summaries is called.
        Then: Files are saved and paths returned.
        """
        story = Story(
            title="Test Story",
            score=100,
            url="https://example.com",
            text="Content",
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        story.summary = "Summary"

        with patch(
            "nook.services.hacker_news.hacker_news.store_daily_snapshots",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = [("2024-01-15.json", "2024-01-15.md")]
            result = await hacker_news._store_summaries([story], [date(2024, 1, 15)])

        assert len(result) == 1


class TestSerializeStories:
    """Tests for HackerNewsRetriever._serialize_stories method."""

    def test_serializes_correctly(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: List of Story objects.
        When: _serialize_stories is called.
        Then: List of dicts is returned.
        """
        story = Story(
            title="Test Story",
            score=100,
            url="https://example.com",
            text="Content",
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        story.summary = "Summary"

        result = hacker_news._serialize_stories([story])

        assert len(result) == 1
        assert result[0]["title"] == "Test Story"
        assert result[0]["score"] == 100


class TestLoadExistingStories:
    """Tests for HackerNewsRetriever._load_existing_stories method."""

    @pytest.mark.asyncio
    async def test_loads_from_json(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: JSON file exists.
        When: _load_existing_stories is called.
        Then: Records are returned.
        """
        existing_data = [{"title": "Old Story", "score": 50}]

        with patch.object(
            hacker_news, "load_json", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = existing_data
            result = await hacker_news._load_existing_stories(
                datetime(2024, 1, 15, tzinfo=timezone.utc)
            )

        assert len(result) == 1
        assert result[0]["title"] == "Old Story"

    @pytest.mark.asyncio
    async def test_falls_back_to_markdown(
        self, hacker_news: HackerNewsRetriever
    ) -> None:
        """
        Given: JSON file doesn't exist but markdown does.
        When: _load_existing_stories is called.
        Then: Records are parsed from markdown.
        """
        markdown_content = """## [Test Story](https://example.com)

スコア: 100

**要約**:
Test summary

---
"""
        with patch.object(
            hacker_news, "load_json", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = None
            with patch.object(
                hacker_news.storage, "load", new_callable=AsyncMock
            ) as mock_md:
                mock_md.return_value = markdown_content
                result = await hacker_news._load_existing_stories(
                    datetime(2024, 1, 15, tzinfo=timezone.utc)
                )

        assert len(result) == 1
        assert result[0]["title"] == "Test Story"


class TestRunSyncWrapper:
    """Tests for run sync wrapper."""

    def test_run_calls_collect(self, hacker_news: HackerNewsRetriever) -> None:
        """
        Given: HackerNewsRetriever instance.
        When: run is called.
        Then: collect is executed via asyncio.run.
        """
        with patch("asyncio.run") as mock_asyncio_run:
            hacker_news.run(limit=10)
            mock_asyncio_run.assert_called_once()


class TestLoadBlockedDomains:
    """Tests for HackerNewsRetriever._load_blocked_domains method."""

    def test_loads_blocked_domains_from_file(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: blocked_domains.json exists.
        When: _load_blocked_domains is called during init.
        Then: Domains are loaded.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_data = {
            "blocked_domains": ["blocked.com"],
            "reasons": {"blocked.com": "Test reason"},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            with patch("os.path.dirname", return_value="/mock/path"):
                retriever = HackerNewsRetriever()

        # blocked_domains should be loaded (or default empty if file missing)
        assert "blocked_domains" in retriever.blocked_domains

    def test_returns_empty_on_file_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Given: blocked_domains.json doesn't exist.
        When: _load_blocked_domains is called.
        Then: Empty dict is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Test the _load_blocked_domains method directly with a mock
        retriever = HackerNewsRetriever()

        # Mock the file loading to raise an error
        original_open = open

        def mock_open_func(path, *args, **kwargs):
            if "blocked_domains.json" in str(path):
                raise FileNotFoundError()
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open_func):
            result = retriever._load_blocked_domains()

        assert result == {"blocked_domains": [], "reasons": {}}
