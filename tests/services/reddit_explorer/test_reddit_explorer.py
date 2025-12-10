"""Tests for reddit_explorer service domain logic.

This module tests the pure logic helper functions in reddit_explorer.py:
- RedditPost dataclass
- RedditExplorer class methods
- Translation, post retrieval, and summarization logic
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip tests if asyncpraw is not installed (optional dependency)
pytest.importorskip("asyncpraw")

from nook.services.reddit_explorer.reddit_explorer import RedditExplorer, RedditPost


class TestRedditPostDataclass:
    """Tests for RedditPost dataclass."""

    def test_post_creation_with_required_fields(self) -> None:
        """
        Given: Required fields for a RedditPost.
        When: A RedditPost is created.
        Then: The instance has correct values and defaults.
        """
        post = RedditPost(
            type="text",
            id="abc123",
            title="Test Post",
            url=None,
            upvotes=100,
            text="Post content",
        )

        assert post.type == "text"
        assert post.id == "abc123"
        assert post.title == "Test Post"
        assert post.url is None
        assert post.upvotes == 100
        assert post.text == "Post content"
        assert post.permalink == ""
        assert post.comments == []
        assert post.thumbnail == "self"
        assert post.popularity_score == 0.0
        assert post.created_at is None

    def test_post_creation_with_all_fields(self) -> None:
        """
        Given: All fields for a RedditPost.
        When: A RedditPost is created.
        Then: The instance has all correct values.
        """
        created = datetime.now(timezone.utc)
        post = RedditPost(
            type="link",
            id="xyz789",
            title="Full Post",
            url="https://example.com",
            upvotes=500,
            text="Post content with link",
            permalink="https://reddit.com/r/test/comments/xyz789",
            comments=[{"author": "user1", "body": "Comment 1", "score": 10}],
            thumbnail="https://example.com/thumb.jpg",
            popularity_score=500.0,
            created_at=created,
        )

        assert post.type == "link"
        assert post.id == "xyz789"
        assert post.title == "Full Post"
        assert post.url == "https://example.com"
        assert post.upvotes == 500
        assert post.text == "Post content with link"
        assert post.permalink == "https://reddit.com/r/test/comments/xyz789"
        assert len(post.comments) == 1
        assert post.thumbnail == "https://example.com/thumb.jpg"
        assert post.popularity_score == 500.0
        assert post.created_at == created

    def test_post_types_are_valid(self) -> None:
        """
        Given: Various post types.
        When: Creating RedditPost instances with different types.
        Then: All valid types are accepted.
        """
        valid_types = ["image", "gallery", "video", "poll", "crosspost", "text", "link"]

        for post_type in valid_types:
            post = RedditPost(
                type=post_type,
                id="test",
                title="Test",
                url=None,
                upvotes=0,
                text="",
            )
            assert post.type == post_type

    def test_summary_field_is_initialized(self) -> None:
        """
        Given: A new RedditPost.
        When: Accessing the summary field.
        Then: It should be accessible (initialized by dataclass).
        """
        post = RedditPost(
            type="text",
            id="test",
            title="Test",
            url=None,
            upvotes=0,
            text="",
        )
        # summary is field(init=False) so it's not set during init
        # but should be accessible after creation
        assert hasattr(post, "summary")

    def test_comments_default_is_empty_list(self) -> None:
        """
        Given: A RedditPost without comments specified.
        When: Accessing the comments field.
        Then: It should be an empty list (not None).
        """
        post = RedditPost(
            type="text",
            id="test",
            title="Test",
            url=None,
            upvotes=0,
            text="",
        )
        assert post.comments == []
        assert isinstance(post.comments, list)


class TestRedditExplorer:
    """Tests for RedditExplorer class methods."""

    @pytest.fixture
    def reddit_explorer(self, monkeypatch: pytest.MonkeyPatch) -> RedditExplorer:
        """Create a RedditExplorer instance for testing."""
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "test-user-agent")
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

        explorer = RedditExplorer()
        explorer.http_client = AsyncMock()
        explorer.gpt_client = MagicMock()
        explorer.gpt_client.generate_content = AsyncMock()
        explorer.reddit = MagicMock()
        return explorer

    def test_init_with_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Given: Reddit API credentials are set as environment variables.
        When: RedditExplorer is initialized.
        Then: A valid instance is created.
        """
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "test-user-agent")
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

        explorer = RedditExplorer()

        assert explorer.client_id == "test-client-id"
        assert explorer.client_secret == "test-secret"
        assert explorer.user_agent == "test-user-agent"
        assert explorer.SUMMARY_LIMIT == 15
        assert explorer.http_client is None
        assert explorer.reddit is None

    def test_init_missing_credentials_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: Missing Reddit API credentials.
        When: RedditExplorer is initialized.
        Then: ValueError is raised.
        """
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

        with pytest.raises(ValueError, match="Reddit API credentials must be provided"):
            RedditExplorer()

    def test_init_with_direct_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: Direct credentials provided.
        When: RedditExplorer is initialized with credentials.
        Then: A valid instance is created with provided credentials.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        explorer = RedditExplorer(
            client_id="direct-id",
            client_secret="test-secret",
            user_agent="direct-agent",
        )

        assert explorer.client_id == "direct-id"
        assert explorer.client_secret == "test-secret"
        assert explorer.user_agent == "direct-agent"

    @pytest.mark.asyncio
    async def test_translate_to_japanese_empty_text(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: Empty text.
        When: _translate_to_japanese is called.
        Then: Empty string is returned.
        """
        result = await reddit_explorer._translate_to_japanese("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_translate_to_japanese_success(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: English text and GPT client.
        When: _translate_to_japanese is called.
        Then: Translated text is returned.
        """
        reddit_explorer.gpt_client.generate_content.return_value = "翻訳されたテキスト"

        result = await reddit_explorer._translate_to_japanese("Hello world")

        assert result == "翻訳されたテキスト"
        reddit_explorer.gpt_client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_to_japanese_error_returns_original(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: GPT client raises an exception.
        When: _translate_to_japanese is called.
        Then: Original text is returned.
        """
        reddit_explorer.gpt_client.generate_content.side_effect = Exception("API Error")

        result = await reddit_explorer._translate_to_japanese("Original text")

        assert result == "Original text"

    @pytest.mark.asyncio
    async def test_retrieve_top_comments_of_post(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: A Reddit post and mocked comments.
        When: _retrieve_top_comments_of_post is called.
        Then: Translated comments are returned.
        """
        # Mock Reddit submission and comments
        mock_submission = MagicMock()
        mock_comment = MagicMock()
        mock_comment.body = "Test comment"
        mock_comment.score = 10

        mock_submission.comments.replace_more = AsyncMock()
        mock_submission.comments.list.return_value = [mock_comment]

        reddit_explorer.reddit.submission = MagicMock(return_value=mock_submission)
        reddit_explorer._translate_to_japanese = AsyncMock(
            return_value="テストコメント"
        )

        result = await reddit_explorer._retrieve_top_comments_of_post(
            RedditPost(
                id="test123", type="text", title="Test", url=None, upvotes=0, text=""
            )
        )

        assert len(result) == 1
        assert result[0]["text"] == "テストコメント"
        assert result[0]["score"] == 10

    @pytest.mark.asyncio
    async def test_summarize_reddit_post(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: A Reddit post with comments.
        When: _summarize_reddit_post is called.
        Then: Summary is set on the post.
        """
        post = RedditPost(
            id="test123",
            type="text",
            title="Test Post",
            url="https://example.com",
            upvotes=100,
            text="Test content",
            comments=[{"text": "Test comment", "score": 10}],
        )

        reddit_explorer.gpt_client.generate_content.return_value = "テスト投稿の要約"

        await reddit_explorer._summarize_reddit_post(post)

        assert post.summary == "テスト投稿の要約"
        reddit_explorer.gpt_client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_reddit_post_error_handling(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: GPT client raises an exception.
        When: _summarize_reddit_post is called.
        Then: Error message is set as summary.
        """
        post = RedditPost(
            id="test123",
            type="text",
            title="Test Post",
            url=None,
            upvotes=0,
            text="Test content",
        )

        reddit_explorer.gpt_client.generate_content.side_effect = Exception("API Error")

        await reddit_explorer._summarize_reddit_post(post)

        assert "要約の生成中にエラーが発生しました" in post.summary

    def test_serialize_posts(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: A list of posts with categories.
        When: _serialize_posts is called.
        Then: Posts are correctly serialized to dictionaries.
        """
        created = datetime.now(timezone.utc)
        post = RedditPost(
            type="link",
            id="test123",
            title="Test Post",
            url="https://example.com",
            upvotes=100,
            text="Test content",
            created_at=created,
        )

        result = reddit_explorer._serialize_posts([("tech", "python", post)])

        assert len(result) == 1
        assert result[0]["id"] == "test123"
        assert result[0]["category"] == "tech"
        assert result[0]["subreddit"] == "python"
        assert result[0]["title"] == "Test Post"
        assert result[0]["url"] == "https://example.com"
        assert result[0]["upvotes"] == 100
        assert result[0]["created_at"] == created.isoformat()

    def test_extract_post_id_from_permalink(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: Various permalink formats.
        When: _extract_post_id_from_permalink is called.
        Then: Correct post ID is extracted.
        """
        # Standard Reddit permalink
        permalink = "https://www.reddit.com/r/python/comments/abc123/test_post/"
        result = reddit_explorer._extract_post_id_from_permalink(permalink)
        assert result == "abc123"

        # Permalink with query parameters
        permalink = (
            "https://www.reddit.com/r/python/comments/xyz789/test_post/?sort=top"
        )
        result = reddit_explorer._extract_post_id_from_permalink(permalink)
        assert result == "xyz789"

        # Empty permalink
        result = reddit_explorer._extract_post_id_from_permalink("")
        assert result == ""

        # Invalid permalink
        result = reddit_explorer._extract_post_id_from_permalink("invalid-url")
        assert result == "invalid-url"

    def test_post_sort_key(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: Post data with different timestamps and scores.
        When: _post_sort_key is called.
        Then: Correct sort key tuple is returned.
        """
        created = datetime.now(timezone.utc)
        post_data = {"popularity_score": 100.0, "created_at": created.isoformat()}

        result = reddit_explorer._post_sort_key(post_data)

        assert result == (100.0, created)

    def test_post_sort_key_missing_fields(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: Post data with missing fields.
        When: _post_sort_key is called.
        Then: Default values are used.
        """
        post_data = {}

        result = reddit_explorer._post_sort_key(post_data)

        assert result == (0.0, datetime.min.replace(tzinfo=timezone.utc))

    def test_render_markdown(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: A list of post records.
        When: _render_markdown is called.
        Then: Properly formatted markdown is returned.
        """
        today = datetime.now(timezone.utc)
        records = [
            {
                "subreddit": "python",
                "title": "Test Post",
                "permalink": "https://reddit.com/r/python/comments/abc123",
                "url": "https://example.com",
                "text": "Test content",
                "upvotes": 100,
                "summary": "Test summary",
            }
        ]

        result = reddit_explorer._render_markdown(records, today)

        assert "# Reddit 人気投稿" in result
        assert "## r/python" in result
        assert "### [Test Post]" in result
        assert "アップボート数: 100" in result
        assert "**要約**:" in result
        assert "Test summary" in result

    def test_select_top_posts_under_limit(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: Posts fewer than SUMMARY_LIMIT.
        When: _select_top_posts is called.
        Then: All posts are returned.
        """
        created = datetime.now(timezone.utc)
        post = RedditPost(
            type="text",
            id="test123",
            title="Test",
            url=None,
            upvotes=0,
            text="",
            created_at=created,
        )
        posts = [("tech", "python", post)]

        result = reddit_explorer._select_top_posts(posts)

        assert result == posts

    def test_select_top_posts_over_limit(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: Posts more than SUMMARY_LIMIT.
        When: _select_top_posts is called.
        Then: Top posts are returned.
        """
        posts = []
        for i in range(20):  # More than SUMMARY_LIMIT (15)
            created = datetime.now(timezone.utc)
            post = RedditPost(
                type="text",
                id=f"test{i}",
                title=f"Test {i}",
                url=None,
                upvotes=i * 10,
                text="",
                created_at=created,
                popularity_score=float(i * 10),
            )
            posts.append(("tech", "python", post))

        result = reddit_explorer._select_top_posts(posts)

        assert len(result) == 15  # SUMMARY_LIMIT
        # Should be sorted by popularity_score (descending)
        assert result[0][2].id == "test19"
        assert result[-1][2].id == "test5"

    def test_run(self, reddit_explorer: RedditExplorer) -> None:
        """
        Given: A RedditExplorer instance.
        When: run is called.
        Then: collect coroutine is executed via asyncio.run and receives limit.
        """
        reddit_explorer.collect = AsyncMock()

        reddit_explorer.run(limit=10)

        reddit_explorer.collect.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_collect_no_posts_returns_empty(
        self, reddit_explorer: RedditExplorer
    ) -> None:
        """
        Given: No posts found.
        When: collect is called.
        Then: An empty list is returned.
        """
        reddit_explorer.setup_http_client = AsyncMock()
        reddit_explorer._load_existing_titles = AsyncMock(return_value=MagicMock())

        with patch("asyncpraw.Reddit") as mock_reddit_class:
            mock_reddit = AsyncMock()
            mock_reddit_class.return_value.__aenter__.return_value = mock_reddit

            # Mock subreddit to return empty async iterator
            mock_subreddit = AsyncMock()

            # Create a proper async iterator that yields nothing
            class EmptyAsyncIterator:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            mock_subreddit.hot = MagicMock(return_value=EmptyAsyncIterator())
            mock_reddit.subreddit = MagicMock(return_value=mock_subreddit)

            with patch(
                "nook.services.reddit_explorer.reddit_explorer.log_processing_start"
            ):
                with patch(
                    "nook.services.reddit_explorer.reddit_explorer.log_no_new_articles"
                ):
                    result = await reddit_explorer.collect()
                    assert result == []
