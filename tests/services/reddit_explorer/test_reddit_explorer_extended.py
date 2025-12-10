from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.reddit_explorer.reddit_explorer import RedditExplorer, RedditPost


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
        # Mock http_client and gpt_client
        explorer.http_client = AsyncMock()
        explorer.gpt_client = AsyncMock()
        return explorer


@pytest.mark.asyncio
async def test_collect_flow(mock_reddit_explorer):
    """Test the collect method flow with mocked reddit API."""
    # Mock asyncpraw.Reddit
    mock_reddit_instance = MagicMock()  # Use MagicMock for context manager
    mock_reddit_instance.__aenter__ = AsyncMock(return_value=mock_reddit_instance)
    mock_reddit_instance.__aexit__ = AsyncMock(return_value=None)

    mock_subreddit = MagicMock()
    # Correctly mock subreddit method as async
    mock_reddit_instance.subreddit = AsyncMock(return_value=mock_subreddit)

    # Mock submissions
    def create_mock_submission(id, title, is_video=False):
        m = MagicMock()
        m.stickied = False
        m.is_video = is_video
        m.is_gallery = False
        m.poll_data = None
        m.crosspost_parent = None
        m.is_self = not is_video
        m.title = title
        m.selftext = "Text" if not is_video else ""
        m.created_utc = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        m.id = id
        m.score = 100
        m.permalink = f"/r/test/comments/{id}/"
        m.url = f"https://reddit.com/{id}"
        if is_video:
            m.thumbnail = "thumb"
        return m

    mock_submission1 = create_mock_submission("post1", "Test Post 1")
    mock_submission2 = create_mock_submission("post2", "Test Post 2", is_video=True)

    # Mock async iterator for hot()
    async def async_iter(*args, **kwargs):
        yield mock_submission1
        yield mock_submission2

    # hot() returns the iterator, it is NOT awaitable itself in PRAW, but it IS an iterable
    # However, sometimes PRAW methods are async generators.
    # subreddit.hot(limit=...) returns an AsyncIterator.
    mock_subreddit.hot.side_effect = async_iter

    # Mock translate and summarize
    mock_reddit_explorer._translate_to_japanese = AsyncMock(
        side_effect=lambda x: f"Translated: {x}"
    )
    mock_reddit_explorer._summarize_reddit_post = AsyncMock()
    mock_reddit_explorer._retrieve_top_comments_of_post = AsyncMock(return_value=[])

    # Mock storage methods
    mock_tracker = MagicMock()
    mock_tracker.count.return_value = 0
    mock_tracker.is_duplicate.return_value = (False, "norm")
    mock_tracker.add.return_value = None

    mock_reddit_explorer._load_existing_titles = AsyncMock(return_value=mock_tracker)
    mock_reddit_explorer._load_existing_posts = AsyncMock(return_value=[])
    mock_reddit_explorer._store_summaries = AsyncMock(
        return_value=[("path/to.json", "path/to.md")]
    )

    with patch(
        "asyncpraw.Reddit", return_value=mock_reddit_instance
    ):  # Constructor returns the instance (which is a context manager)
        target_dates = [date(2023, 1, 1)]
        result = await mock_reddit_explorer.collect(limit=5, target_dates=target_dates)

    assert len(result) > 0  # Should have processed posts


@pytest.mark.asyncio
async def test_store_summaries(mock_reddit_explorer):
    """Test _store_summaries and interaction with store_daily_snapshots."""
    post = RedditPost(
        type="text",
        id="1",
        title="Title",
        url="url",
        upvotes=10,
        text="text",
        created_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    posts = [("tech", "python", post)]
    target_dates = [date(2023, 1, 1)]

    # Mock store_daily_snapshots
    with patch(
        "nook.services.reddit_explorer.reddit_explorer.store_daily_snapshots",
        new_callable=AsyncMock,
    ) as mock_store:
        mock_store.return_value = [("file.json", "file.md")]

        result = await mock_reddit_explorer._store_summaries(posts, target_dates)

        assert result == [("file.json", "file.md")]
        mock_store.assert_called_once()
        args, kwargs = mock_store.call_args

        # Verify serialized data structure
        records_by_date = args[0]
        assert date(2023, 1, 1) in records_by_date
        assert records_by_date[date(2023, 1, 1)][0]["title"] == "Title"


@pytest.mark.asyncio
async def test_load_existing_posts_json(mock_reddit_explorer):
    """Test loading existing posts from JSON."""
    mock_reddit_explorer.load_json = AsyncMock(
        return_value={"python": [{"id": "1", "title": "Existing"}]}
    )

    result = await mock_reddit_explorer._load_existing_posts(datetime(2023, 1, 1))

    assert len(result) == 1
    assert result[0]["title"] == "Existing"
    assert result[0]["subreddit"] == "python"


@pytest.mark.asyncio
async def test_load_existing_posts_markdown_fallback(mock_reddit_explorer):
    """Test loading existing posts from Markdown when JSON is missing."""
    mock_reddit_explorer.load_json = AsyncMock(return_value=None)
    mock_reddit_explorer.storage.load = AsyncMock(
        return_value="""# Reddit 人気投稿 (2023-01-01)

## r/python

### [Markdown Title](http://permalink)

リンク: http://url

本文: text

アップボート数: 100

**要約**:
Summary text
---"""
    )

    result = await mock_reddit_explorer._load_existing_posts(datetime(2023, 1, 1))

    assert len(result) == 1
    assert result[0]["title"] == "Markdown Title"
    assert result[0]["subreddit"] == "python"


@pytest.mark.asyncio
async def test_load_existing_titles(mock_reddit_explorer):
    """Test extracting titles for deduplication."""
    # Mock load_markdown to return a string (it's called synchronously in the code)
    mock_reddit_explorer.storage.load_markdown = MagicMock(
        return_value="""
### [Title 1]
### [Title 2]
"""
    )
    tracker = await mock_reddit_explorer._load_existing_titles()

    assert tracker.is_duplicate("Title 1")[0]
    assert tracker.is_duplicate("Title 2")[0]
    assert not tracker.is_duplicate("New Title")[0]


def test_extract_post_id(mock_reddit_explorer):
    """Test permalink parsing logic."""
    # Standard format
    assert (
        mock_reddit_explorer._extract_post_id_from_permalink(
            "/r/sub/comments/123id/title/"
        )
        == "123id"
    )
    # No title part
    assert (
        mock_reddit_explorer._extract_post_id_from_permalink("/r/sub/comments/123id/")
        == "123id"
    )
    # Full URL
    assert (
        mock_reddit_explorer._extract_post_id_from_permalink(
            "https://reddit.com/r/sub/comments/123id/title/"
        )
        == "123id"
    )
    # Fallback
    assert (
        mock_reddit_explorer._extract_post_id_from_permalink("/simple/path/123id")
        == "123id"
    )
    # Empty
    assert mock_reddit_explorer._extract_post_id_from_permalink("") == ""


@pytest.mark.asyncio
async def test_retrieve_top_comments(mock_reddit_explorer):
    """Test comment retrieval and translation."""
    post = RedditPost(type="text", id="1", title="T", url="u", upvotes=1, text="t")

    mock_submission = AsyncMock()
    mock_comment = MagicMock()
    mock_comment.body = "English Comment"
    mock_comment.score = 10

    # comments.list() is a method that returns a list (sync), replace_more is async
    mock_submission.comments.replace_more = AsyncMock()
    mock_submission.comments.list = MagicMock(return_value=[mock_comment])

    mock_reddit_explorer.reddit = MagicMock()  # Should contain submission method
    mock_reddit_explorer.reddit.submission = AsyncMock(
        return_value=mock_submission
    )  # submission(id=...) is a coro

    mock_reddit_explorer._translate_to_japanese = AsyncMock(
        return_value="Japanese Comment"
    )

    comments = await mock_reddit_explorer._retrieve_top_comments_of_post(post)

    assert len(comments) == 1
    assert comments[0]["text"] == "Japanese Comment"
    assert comments[0]["score"] == 10
