"""Tests for reddit_explorer service domain logic.

This module tests the pure logic helper functions in reddit_explorer.py:
- RedditPost dataclass
"""

from datetime import datetime, timezone

import pytest

# Skip tests if asyncpraw is not installed (optional dependency)
pytest.importorskip("asyncpraw")

from nook.services.reddit_explorer.reddit_explorer import RedditPost


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
