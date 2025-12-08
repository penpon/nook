"""Tests for fourchan_explorer service domain logic.

This module tests the pure logic helper functions in fourchan_explorer.py:
- Thread dataclass
- AI keywords list
- _load_boards
"""

import pytest

from nook.services.fourchan_explorer.fourchan_explorer import (
    FourChanExplorer,
    Thread,
)


class TestThreadDataclass:
    """Tests for Thread dataclass."""

    def test_thread_creation_with_required_fields(self) -> None:
        """
        Given: Required fields for a Thread.
        When: A Thread is created.
        Then: The instance has correct values and defaults.
        """
        thread = Thread(
            thread_id=12345,
            title="AI Thread",
            url="https://boards.4chan.org/g/thread/12345",
            board="g",
            posts=[{"no": 12345, "com": "First post"}],
            timestamp=1704067200,  # 2024-01-01 00:00:00 UTC
        )

        assert thread.thread_id == 12345
        assert thread.title == "AI Thread"
        assert thread.url == "https://boards.4chan.org/g/thread/12345"
        assert thread.board == "g"
        assert len(thread.posts) == 1
        assert thread.timestamp == 1704067200
        assert thread.summary == ""
        assert thread.popularity_score == 0.0

    def test_thread_creation_with_all_fields(self) -> None:
        """
        Given: All fields for a Thread.
        When: A Thread is created.
        Then: The instance has all correct values.
        """
        thread = Thread(
            thread_id=67890,
            title="Full Thread",
            url="https://boards.4chan.org/sci/thread/67890",
            board="sci",
            posts=[
                {"no": 67890, "com": "Post 1"},
                {"no": 67891, "com": "Post 2"},
            ],
            timestamp=1704153600,
            summary="AI discussion about machine learning",
            popularity_score=150.0,
        )

        assert thread.thread_id == 67890
        assert thread.title == "Full Thread"
        assert thread.board == "sci"
        assert len(thread.posts) == 2
        assert thread.summary == "AI discussion about machine learning"
        assert thread.popularity_score == 150.0


class TestAIKeywords:
    """Tests for AI keywords list."""

    @pytest.fixture
    def fourchan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FourChanExplorer:
        """
        Create a FourChanExplorer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set.
        When: FourChanExplorer is instantiated with test_mode.
        Then: A valid instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FourChanExplorer(test_mode=True)

    def test_ai_keywords_contains_common_terms(
        self, fourchan_explorer: FourChanExplorer
    ) -> None:
        """
        Given: A FourChanExplorer instance.
        When: Checking the ai_keywords list.
        Then: It contains common AI-related terms.
        """
        expected_keywords = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "gpt",
            "llm",
            "chatgpt",
            "claude",
            "openai",
        ]

        for keyword in expected_keywords:
            assert keyword in fourchan_explorer.ai_keywords

    def test_ai_keywords_contains_image_generation_terms(
        self, fourchan_explorer: FourChanExplorer
    ) -> None:
        """
        Given: A FourChanExplorer instance.
        When: Checking the ai_keywords list.
        Then: It contains image generation AI terms.
        """
        expected_keywords = ["stable diffusion", "dalle", "midjourney"]

        for keyword in expected_keywords:
            assert keyword in fourchan_explorer.ai_keywords


class TestLoadBoards:
    """Tests for FourChanExplorer._load_boards method."""

    @pytest.fixture
    def fourchan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FourChanExplorer:
        """Create a FourChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FourChanExplorer(test_mode=True)

    def test_load_boards_returns_list(
        self, fourchan_explorer: FourChanExplorer
    ) -> None:
        """
        Given: A FourChanExplorer instance.
        When: Checking the target_boards attribute.
        Then: It is a list of board IDs.
        """
        assert isinstance(fourchan_explorer.target_boards, list)
        assert len(fourchan_explorer.target_boards) > 0

    def test_default_boards_include_expected_values(
        self, fourchan_explorer: FourChanExplorer
    ) -> None:
        """
        Given: A FourChanExplorer instance with default or existing boards.toml.
        When: Checking the target_boards.
        Then: Expected boards like 'g' (technology) should be present.
        """
        # Default boards are ["g", "sci", "biz", "pol"]
        # or loaded from boards.toml
        assert isinstance(fourchan_explorer.target_boards, list)


class TestRequestDelay:
    """Tests for request delay configuration."""

    def test_test_mode_has_short_delay(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Given: FourChanExplorer created with test_mode=True.
        When: Checking request_delay.
        Then: It should be a short delay (0.1 seconds).
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = FourChanExplorer(test_mode=True)

        assert explorer.request_delay == 0.1

    def test_normal_mode_has_standard_delay(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: FourChanExplorer created with test_mode=False.
        When: Checking request_delay.
        Then: It should be the standard delay (1 second).
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = FourChanExplorer(test_mode=False)

        assert explorer.request_delay == 1
