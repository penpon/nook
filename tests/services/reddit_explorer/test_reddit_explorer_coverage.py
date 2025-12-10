"""Additional coverage tests for reddit_explorer service.

This module adds tests for previously uncovered code paths:
- Various post type detection (video, gallery, poll, crosspost, image, link)
- Duplicate post skipping
- Error handling in load_existing_posts
- _post_sort_key edge cases
- _select_top_posts method
- Empty permalink handling
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.reddit_explorer.reddit_explorer import RedditExplorer


def _jst_date_now() -> date:
    """Return the current date in JST timezone."""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).date()


@pytest.fixture
def mock_reddit_explorer(tmp_path):
    with patch.dict(
        "os.environ",
        {
            "REDDIT_CLIENT_ID": "dummy_id",
            "REDDIT_CLIENT_SECRET": "dummy_secret",
            "REDDIT_USER_AGENT": "dummy_agent",
            "OPENAI_API_KEY": "dummy_key",
        },
    ):
        explorer = RedditExplorer(storage_dir=str(tmp_path))
        explorer.http_client = AsyncMock()
        explorer.gpt_client = AsyncMock()
        return explorer


class TestPostTypeDetection:
    """Tests for post type detection logic (_retrieve_hot_posts lines 326-350)."""

    @pytest.mark.asyncio
    async def test_stickied_post_skipped(self, mock_reddit_explorer):
        """
        Given: A stickied post
        When: _retrieve_hot_posts is called
        Then: The stickied post is skipped
        """
        mock_subreddit = MagicMock()

        # Create stickied submission
        stickied = MagicMock()
        stickied.stickied = True

        async def async_iter(*args, **kwargs):
            yield stickied

        mock_subreddit.hot.side_effect = async_iter

        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")

        posts, total_found = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 0
        assert total_found == 0

    @pytest.mark.asyncio
    async def test_video_post_type(self, mock_reddit_explorer):
        """
        Given: A video post
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'video'
        """
        mock_subreddit = MagicMock()

        video_submission = MagicMock()
        video_submission.stickied = False
        video_submission.is_video = True
        video_submission.is_gallery = False
        video_submission.poll_data = None
        video_submission.crosspost_parent = None
        video_submission.is_self = False
        video_submission.title = "Video Post"
        video_submission.selftext = ""
        video_submission.id = "vid1"
        video_submission.score = 100
        video_submission.permalink = "/r/test/comments/vid1/"
        video_submission.url = "https://v.redd.it/video"
        video_submission.thumbnail = "thumb"
        video_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield video_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()

        mock_reddit_explorer._translate_to_japanese = AsyncMock(return_value="")

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "video"

    @pytest.mark.asyncio
    async def test_gallery_post_type(self, mock_reddit_explorer):
        """
        Given: A gallery post
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'gallery'
        """
        mock_subreddit = MagicMock()

        gallery_submission = MagicMock()
        gallery_submission.stickied = False
        gallery_submission.is_video = False
        gallery_submission.is_gallery = True
        gallery_submission.poll_data = None
        gallery_submission.crosspost_parent = None
        gallery_submission.is_self = False
        gallery_submission.title = "Gallery Post"
        gallery_submission.selftext = ""
        gallery_submission.id = "gal1"
        gallery_submission.score = 50
        gallery_submission.permalink = "/r/test/comments/gal1/"
        gallery_submission.url = "https://imgur.com/gallery"
        gallery_submission.thumbnail = "thumb"
        gallery_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield gallery_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()
        mock_reddit_explorer._translate_to_japanese = AsyncMock(return_value="")

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "gallery"

    @pytest.mark.asyncio
    async def test_poll_post_type(self, mock_reddit_explorer):
        """
        Given: A poll post
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'poll'
        """
        mock_subreddit = MagicMock()

        poll_submission = MagicMock()
        poll_submission.stickied = False
        poll_submission.is_video = False
        poll_submission.is_gallery = False
        poll_submission.poll_data = {"options": ["A", "B"]}
        poll_submission.crosspost_parent = None
        poll_submission.is_self = True
        poll_submission.title = "Poll Post"
        poll_submission.selftext = "Vote!"
        poll_submission.id = "poll1"
        poll_submission.score = 75
        poll_submission.permalink = "/r/test/comments/poll1/"
        poll_submission.url = "https://reddit.com/poll"
        poll_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield poll_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()
        mock_reddit_explorer._translate_to_japanese = AsyncMock(
            return_value="Translated"
        )

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "poll"

    @pytest.mark.asyncio
    async def test_crosspost_type(self, mock_reddit_explorer):
        """
        Given: A crosspost
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'crosspost'
        """
        mock_subreddit = MagicMock()

        cross_submission = MagicMock()
        cross_submission.stickied = False
        cross_submission.is_video = False
        cross_submission.is_gallery = False
        cross_submission.poll_data = None
        cross_submission.crosspost_parent = "t3_abc123"
        cross_submission.is_self = False
        cross_submission.title = "Crosspost"
        cross_submission.selftext = ""
        cross_submission.id = "cross1"
        cross_submission.score = 30
        cross_submission.permalink = "/r/test/comments/cross1/"
        cross_submission.url = "https://reddit.com/original"
        cross_submission.thumbnail = "thumb"
        cross_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield cross_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()
        mock_reddit_explorer._translate_to_japanese = AsyncMock(return_value="")

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "crosspost"

    @pytest.mark.asyncio
    async def test_image_post_type(self, mock_reddit_explorer):
        """
        Given: An image post (URL ends with .jpg, .png, etc.)
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'image'
        """
        mock_subreddit = MagicMock()

        image_submission = MagicMock()
        image_submission.stickied = False
        image_submission.is_video = False
        image_submission.is_gallery = False
        image_submission.poll_data = None
        image_submission.crosspost_parent = None
        image_submission.is_self = False
        image_submission.title = "Image Post"
        image_submission.selftext = ""
        image_submission.id = "img1"
        image_submission.score = 200
        image_submission.permalink = "/r/test/comments/img1/"
        image_submission.url = "https://i.redd.it/image.jpg"
        image_submission.thumbnail = "thumb"
        image_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield image_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()
        mock_reddit_explorer._translate_to_japanese = AsyncMock(return_value="")

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "image"

    @pytest.mark.asyncio
    async def test_link_post_type(self, mock_reddit_explorer):
        """
        Given: A link post (external URL, not image)
        When: _retrieve_hot_posts is called
        Then: The post type is set to 'link'
        """
        mock_subreddit = MagicMock()

        link_submission = MagicMock()
        link_submission.stickied = False
        link_submission.is_video = False
        link_submission.is_gallery = False
        link_submission.poll_data = None
        link_submission.crosspost_parent = None
        link_submission.is_self = False
        link_submission.title = "Link Post"
        link_submission.selftext = ""
        link_submission.id = "link1"
        link_submission.score = 150
        link_submission.permalink = "/r/test/comments/link1/"
        link_submission.url = "https://example.com/article"
        link_submission.thumbnail = "thumb"
        link_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield link_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()
        mock_reddit_explorer._translate_to_japanese = AsyncMock(return_value="")

        posts, _ = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 1
        assert posts[0].type == "link"


class TestDuplicateSkipping:
    """Tests for duplicate post skipping (lines 357-363)."""

    @pytest.mark.asyncio
    async def test_duplicate_post_is_skipped(self, mock_reddit_explorer):
        """
        Given: A duplicate post (dedup_tracker returns True)
        When: _retrieve_hot_posts is called
        Then: The duplicate post is skipped
        """
        mock_subreddit = MagicMock()

        dup_submission = MagicMock()
        dup_submission.stickied = False
        dup_submission.is_video = False
        dup_submission.is_gallery = False
        dup_submission.poll_data = None
        dup_submission.crosspost_parent = None
        dup_submission.is_self = True
        dup_submission.title = "Duplicate Post"
        dup_submission.selftext = "text"
        dup_submission.id = "dup1"
        dup_submission.score = 100
        dup_submission.permalink = "/r/test/comments/dup1/"
        dup_submission.url = "https://reddit.com/dup1"
        dup_submission.created_utc = datetime.now(timezone.utc).timestamp()

        async def async_iter(*args, **kwargs):
            yield dup_submission

        mock_subreddit.hot.side_effect = async_iter
        mock_reddit_explorer.reddit = MagicMock()
        mock_reddit_explorer.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (True, "normalized")
        mock_tracker.get_original_title.return_value = "Original Title"

        posts, total_found = await mock_reddit_explorer._retrieve_hot_posts(
            "test", None, mock_tracker, [_jst_date_now()]
        )

        assert len(posts) == 0
        assert total_found == 1
        mock_tracker.get_original_title.assert_called_once()


class TestLoadExistingPostsEdgeCases:
    """Tests for _load_existing_posts edge cases (lines 574, 578)."""

    @pytest.mark.asyncio
    async def test_load_existing_posts_returns_list_directly(
        self, mock_reddit_explorer
    ):
        """
        Given: JSON file returns a list (not dict)
        When: _load_existing_posts is called
        Then: The list is returned directly
        """
        mock_reddit_explorer.load_json = AsyncMock(
            return_value=[{"id": "1", "title": "Post"}]
        )

        result = await mock_reddit_explorer._load_existing_posts(datetime(2023, 1, 1))

        assert len(result) == 1
        assert result[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_load_existing_posts_no_markdown(self, mock_reddit_explorer):
        """
        Given: No JSON and no Markdown file exists
        When: _load_existing_posts is called
        Then: Empty list is returned
        """
        mock_reddit_explorer.load_json = AsyncMock(return_value=None)
        mock_reddit_explorer.storage.load = AsyncMock(return_value=None)

        result = await mock_reddit_explorer._load_existing_posts(datetime(2023, 1, 1))

        assert result == []


class TestPostSortKey:
    """Tests for _post_sort_key edge cases (lines 588-589)."""

    def test_sort_key_with_invalid_date(self, mock_reddit_explorer):
        """
        Given: A record with invalid date format
        When: _post_sort_key is called
        Then: Returns minimum datetime
        """
        item = {"popularity_score": 10.0, "created_at": "invalid-date"}
        result = mock_reddit_explorer._post_sort_key(item)

        assert result[0] == 10.0
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)


class TestSelectTopPosts:
    """Tests for _select_top_posts method (lines 689)."""

    def test_select_top_posts_empty(self, mock_reddit_explorer):
        """
        Given: Empty posts list
        When: _select_top_posts is called
        Then: Returns empty list
        """
        result = mock_reddit_explorer._select_top_posts([])
        assert result == []


class TestExtractPostIdEdgeCases:
    """Tests for _extract_post_id_from_permalink edge cases (line 616)."""

    def test_extract_from_trailing_slash_only(self, mock_reddit_explorer):
        """
        Given: A URL with only slashes
        When: _extract_post_id_from_permalink is called
        Then: Returns empty string
        """
        result = mock_reddit_explorer._extract_post_id_from_permalink("///")
        assert result == ""


class TestStoreEmptyPosts:
    """Tests for _store_summaries with empty posts (lines 517-518)."""

    @pytest.mark.asyncio
    async def test_store_summaries_empty_posts(self, mock_reddit_explorer):
        """
        Given: Empty posts list
        When: _store_summaries is called
        Then: Returns empty list
        """
        result = await mock_reddit_explorer._store_summaries([], [_jst_date_now()])
        assert result == []


class TestLoadExistingTitlesError:
    """Tests for _load_existing_titles error handling (lines 709-710)."""

    @pytest.mark.asyncio
    async def test_load_existing_titles_exception(self, mock_reddit_explorer):
        """
        Given: storage.load_markdown raises an exception
        When: _load_existing_titles is called
        Then: Returns empty tracker without raising
        """
        mock_reddit_explorer.storage.load_markdown = MagicMock(
            side_effect=Exception("Storage error")
        )

        tracker = await mock_reddit_explorer._load_existing_titles()

        assert tracker.count() == 0
