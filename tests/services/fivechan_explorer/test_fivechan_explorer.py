"""Tests for fivechan_explorer service domain logic.

This module tests the pure logic helper functions in fivechan_explorer.py:
- Thread dataclass
- AI keywords list (Japanese)
- _get_random_user_agent
- _calculate_backoff_delay
- _load_boards
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Skip tests if dateutil is not installed (optional dependency)
pytest.importorskip("dateutil")

from nook.services.fivechan_explorer.fivechan_explorer import (
    FiveChanExplorer,
    Thread,
)


class TestThreadDataclass:
    """Tests for Thread dataclass (5chan version)."""

    def test_thread_creation_with_required_fields(self) -> None:
        """
        Given: Required fields for a Thread.
        When: A Thread is created.
        Then: The instance has correct values and defaults.
        """
        thread = Thread(
            thread_id=123456789,
            title="AIスレッド",
            url="https://mevius.5ch.net/test/read.cgi/tech/123456789/",
            board="tech",
            posts=[{"number": 1, "body": "最初の投稿"}],
            timestamp=1704067200,
        )

        assert thread.thread_id == 123456789
        assert thread.title == "AIスレッド"
        assert thread.url == "https://mevius.5ch.net/test/read.cgi/tech/123456789/"
        assert thread.board == "tech"
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
            thread_id=987654321,
            title="ChatGPT総合スレ",
            url="https://egg.5ch.net/test/read.cgi/software/987654321/",
            board="software",
            posts=[
                {"number": 1, "body": "投稿1"},
                {"number": 2, "body": "投稿2"},
                {"number": 3, "body": "投稿3"},
            ],
            timestamp=1704153600,
            summary="ChatGPTに関する議論スレッド",
            popularity_score=250.0,
        )

        assert thread.thread_id == 987654321
        assert thread.title == "ChatGPT総合スレ"
        assert thread.board == "software"
        assert len(thread.posts) == 3
        assert thread.summary == "ChatGPTに関する議論スレッド"
        assert thread.popularity_score == 250.0


class TestAIKeywords:
    """Tests for AI keywords list (Japanese version)."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """
        Create a FiveChanExplorer instance for testing.

        Given: Environment variable OPENAI_API_KEY is set.
        When: FiveChanExplorer is instantiated.
        Then: A valid instance is returned.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_ai_keywords_contains_english_terms(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the ai_keywords list.
        Then: It contains common English AI-related terms.
        """
        expected_keywords = [
            "ai",
            "gpt",
            "llm",
            "chatgpt",
            "claude",
            "openai",
        ]

        for keyword in expected_keywords:
            assert keyword in fivechan_explorer.ai_keywords

    def test_ai_keywords_contains_japanese_terms(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the ai_keywords list.
        Then: It contains Japanese AI-related terms.
        """
        expected_keywords = [
            "人工知能",
            "機械学習",
            "ディープラーニング",
            "自然言語処理",
            "大規模言語モデル",
            "生成ai",
            "画像生成",
        ]

        for keyword in expected_keywords:
            assert keyword in fivechan_explorer.ai_keywords


class TestGetRandomUserAgent:
    """Tests for FiveChanExplorer._get_random_user_agent method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_returns_valid_user_agent(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: _get_random_user_agent is called.
        Then: A valid user agent string is returned.
        """
        user_agent = fivechan_explorer._get_random_user_agent()

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        # User agents typically contain browser identifiers
        assert any(
            browser in user_agent for browser in ["Mozilla", "Chrome", "Firefox"]
        )

    def test_returns_user_agent_from_list(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: _get_random_user_agent is called.
        Then: The returned user agent is from the predefined list.
        """
        user_agent = fivechan_explorer._get_random_user_agent()

        assert user_agent in fivechan_explorer.user_agents


class TestCalculateBackoffDelay:
    """Tests for FiveChanExplorer._calculate_backoff_delay method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_first_retry_has_short_delay(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Retry count of 0.
        When: _calculate_backoff_delay is called.
        Then: A 1 second delay is returned (2^0).
        """
        delay = fivechan_explorer._calculate_backoff_delay(0)

        assert delay == 1

    def test_exponential_increase(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: Increasing retry counts.
        When: _calculate_backoff_delay is called.
        Then: Delays increase exponentially.
        """
        delays = [fivechan_explorer._calculate_backoff_delay(i) for i in range(5)]

        assert delays == [1, 2, 4, 8, 16]

    def test_max_delay_is_capped(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A very high retry count.
        When: _calculate_backoff_delay is called.
        Then: The delay is capped at 300 seconds.
        """
        delay = fivechan_explorer._calculate_backoff_delay(10)

        assert delay == 300  # min(2^10=1024, 300) = 300


class TestLoadBoards:
    """Tests for FiveChanExplorer._load_boards method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_load_boards_returns_dict(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the target_boards attribute.
        Then: It is a dict mapping board_id to board_name.
        """
        assert isinstance(fivechan_explorer.target_boards, dict)
        assert len(fivechan_explorer.target_boards) > 0

    def test_board_servers_are_set(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the board_servers attribute.
        Then: It contains server mappings for each board.
        """
        assert hasattr(fivechan_explorer, "board_servers")
        assert isinstance(fivechan_explorer.board_servers, dict)


class TestSubdomains:
    """Tests for subdomain configuration."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_subdomains_are_configured(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the subdomains list.
        Then: It contains 5ch.net subdomains.
        """
        assert isinstance(fivechan_explorer.subdomains, list)
        assert len(fivechan_explorer.subdomains) > 0
        assert all("5ch.net" in subdomain for subdomain in fivechan_explorer.subdomains)

    def test_subdomains_include_common_servers(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the subdomains list.
        Then: It includes common 5ch servers.
        """
        expected_servers = ["mevius.5ch.net", "egg.5ch.net"]

        for server in expected_servers:
            assert server in fivechan_explorer.subdomains


class TestBrowserHeaders:
    """Tests for browser headers configuration."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_browser_headers_are_configured(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: Checking the browser_headers dict.
        Then: It contains standard browser headers.
        """
        headers = fivechan_explorer.browser_headers

        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Referer" in headers
        assert "5ch.net" in headers.get("Referer", "")
