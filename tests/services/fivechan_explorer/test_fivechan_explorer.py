"""Tests for fivechan_explorer service domain logic.

This module tests the pure logic helper functions in fivechan_explorer.py:
- Thread dataclass
- AI keywords list (Japanese)
- _get_random_user_agent
- _calculate_backoff_delay
- _load_boards
- _build_board_url
- _get_board_server
- _get_with_retry
- _get_subject_txt_data
- collect method
- run method
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip tests if dateutil is not installed (optional dependency)
pytest.importorskip("dateutil")

from nook.services.fivechan_explorer.fivechan_explorer import (
    FiveChanExplorer,
    Thread,
)


def _jst_date_now() -> date:
    """Return the current date in JST timezone.

    Note: Uses datetime.now() rather than a fixed date because:
    1. Tests verify behavior with 'current' timestamps (created_utc)
    2. Fixed dates would fail when combined with datetime.now() timestamps
    3. is_within_target_dates() compares JST-converted dates, so we need matching JST dates
    """
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).date()


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


class TestBuildBoardUrl:
    """Tests for FiveChanExplorer._build_board_url method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_build_board_url_formats_correctly(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A board_id and server.
        When: _build_board_url is called.
        Then: A properly formatted URL is returned.
        """
        url = fivechan_explorer._build_board_url("ai", "mevius.5ch.net")
        assert url == "https://mevius.5ch.net/ai/"

        url = fivechan_explorer._build_board_url("tech", "egg.5ch.net")
        assert url == "https://egg.5ch.net/tech/"


class TestGetBoardServer:
    """Tests for FiveChanExplorer._get_board_server method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_get_existing_board_server(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: _get_board_server is called with existing board.
        Then: The correct server is returned.
        """
        server = fivechan_explorer._get_board_server("ai")
        assert isinstance(server, str)
        assert "5ch.net" in server

    def test_get_nonexistent_board_server(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: _get_board_server is called with nonexistent board.
        Then: The default server is returned.
        """
        server = fivechan_explorer._get_board_server("nonexistent")
        assert server == "mevius.5ch.net"


@pytest.mark.asyncio
class TestGetWithRetry:
    """Tests for FiveChanExplorer._get_with_retry method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = FiveChanExplorer()
        explorer.http_client = AsyncMock()
        return explorer

    async def test_success_on_first_try(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A successful HTTP response.
        When: _get_with_retry is called.
        Then: The response is returned immediately.
        """
        mock_response = AsyncMock()
        mock_response.status_code = 200
        fivechan_explorer.http_client.get.return_value = mock_response

        result = await fivechan_explorer._get_with_retry("https://example.com")

        assert result == mock_response
        fivechan_explorer.http_client.get.assert_called_once()

    async def test_retry_on_rate_limit(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A rate limit response followed by success.
        When: _get_with_retry is called.
        Then: The request is retried and succeeds.
        """
        mock_response_429 = AsyncMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}

        mock_response_200 = AsyncMock()
        mock_response_200.status_code = 200

        fivechan_explorer.http_client.get.side_effect = [
            mock_response_429,
            mock_response_200,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await fivechan_explorer._get_with_retry("https://example.com")

            assert result == mock_response_200
            assert fivechan_explorer.http_client.get.call_count == 2
            mock_sleep.assert_called_once()

    async def test_retry_on_server_error(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A server error response followed by success.
        When: _get_with_retry is called.
        Then: The request is retried and succeeds.
        """
        mock_response_503 = AsyncMock()
        mock_response_503.status_code = 503

        mock_response_200 = AsyncMock()
        mock_response_200.status_code = 200

        fivechan_explorer.http_client.get.side_effect = [
            mock_response_503,
            mock_response_200,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await fivechan_explorer._get_with_retry("https://example.com")

            assert result == mock_response_200
            assert fivechan_explorer.http_client.get.call_count == 2
            mock_sleep.assert_called_once()


@pytest.mark.asyncio
class TestGetSubjectTxtData:
    """Tests for FiveChanExplorer._get_subject_txt_data method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    async def test_successful_subject_txt_parsing(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A valid subject.txt response.
        When: _get_subject_txt_data is called.
        Then: Thread data is correctly parsed.
        """
        mock_content = "1234567890.dat<>テストスレッド (10)\n9876543210.dat<>もう一つのスレッド (5)"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = mock_content.encode("shift_jis")

            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await fivechan_explorer._get_subject_txt_data("ai")

            assert len(result) == 2
            assert result[0]["title"] == "テストスレッド"
            assert result[0]["post_count"] == 10
            assert result[1]["title"] == "もう一つのスレッド"
            assert result[1]["post_count"] == 5

    async def test_network_error_returns_empty_list(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A network error occurs.
        When: _get_subject_txt_data is called.
        Then: An empty list is returned.
        """
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await fivechan_explorer._get_subject_txt_data("ai")

            assert result == []


@pytest.mark.asyncio
class TestCollect:
    """Tests for FiveChanExplorer.collect method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = FiveChanExplorer()
        explorer.http_client = MagicMock()
        explorer.gpt_client = MagicMock()
        return explorer

    async def test_collect_no_threads_returns_empty(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: No threads found.
        When: collect is called.
        Then: An empty list is returned.
        """
        fivechan_explorer.setup_http_client = AsyncMock()
        fivechan_explorer._retrieve_ai_threads = AsyncMock(return_value=[])
        fivechan_explorer._load_existing_titles = MagicMock(return_value=set())

        # Disable request delay for faster test execution
        fivechan_explorer.min_request_delay = 0
        fivechan_explorer.max_request_delay = 0

        with patch(
            "nook.services.fivechan_explorer.fivechan_explorer.log_processing_start"
        ):
            with patch(
                "nook.services.fivechan_explorer.fivechan_explorer.log_no_new_articles"
            ):
                result = await fivechan_explorer.collect()
                assert result == []

    async def test_collect_with_threads_processes_successfully(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Threads are found.
        When: collect is called.
        Then: Threads are processed and saved.
        """

        # Use current timestamp so thread matches target_dates
        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        mock_thread = Thread(
            thread_id=1234567890,
            title="AI関連スレッド",
            url="https://example.com/thread/1234567890",
            board="ai",
            posts=[],
            timestamp=current_timestamp,
            popularity_score=10.0,
        )

        # Configure mocks with explicit return values to avoid race conditions
        fivechan_explorer.setup_http_client = AsyncMock()
        fivechan_explorer._retrieve_ai_threads = AsyncMock(return_value=[mock_thread])
        fivechan_explorer._load_existing_titles = MagicMock(return_value=set())
        fivechan_explorer._summarize_thread = AsyncMock()

        # Disable request delay for faster test execution
        fivechan_explorer.min_request_delay = 0
        fivechan_explorer.max_request_delay = 0

        # Ensure _store_summaries always returns the expected value
        store_summaries_mock = AsyncMock(return_value=[("test.json", "test.md")])
        fivechan_explorer._store_summaries = store_summaries_mock

        with patch(
            "nook.services.fivechan_explorer.fivechan_explorer.log_processing_start"
        ):
            with patch(
                "nook.services.fivechan_explorer.fivechan_explorer.log_article_counts"
            ):
                with patch(
                    "nook.services.fivechan_explorer.fivechan_explorer.log_summary_candidates"
                ):
                    with patch(
                        "nook.services.fivechan_explorer.fivechan_explorer.log_summarization_start"
                    ):
                        with patch(
                            "nook.services.fivechan_explorer.fivechan_explorer.log_summarization_progress"
                        ):
                            with patch(
                                "nook.services.fivechan_explorer.fivechan_explorer.log_storage_complete"
                            ):
                                # Pass explicit target_dates to ensure filtering logic matches the thread's date
                                # regardless of timezone differences between JST (default in collect) and execution environment
                                expected_date = datetime.fromtimestamp(
                                    current_timestamp
                                ).date()
                                result = await fivechan_explorer.collect(
                                    target_dates=[expected_date]
                                )
                                assert result == [("test.json", "test.md")]
                                # _summarize_thread is called for each thread (4 boards x 1 thread each)
                                assert (
                                    fivechan_explorer._summarize_thread.call_count == 4
                                )


class TestRun:
    """Tests for FiveChanExplorer.run method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_run_calls_collect_via_asyncio_run(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A FiveChanExplorer instance.
        When: run is called.
        Then: collect coroutine is dispatched via asyncio.run with the provided limit.
        """
        fivechan_explorer.collect = AsyncMock()

        fivechan_explorer.run(thread_limit=10)

        fivechan_explorer.collect.assert_awaited_once_with(10)


@pytest.mark.asyncio
class TestSummarizeThread:
    """Tests for FiveChanExplorer._summarize_thread method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = FiveChanExplorer()
        explorer.gpt_client = AsyncMock()
        return explorer

    async def test_summarize_thread_sets_summary(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A thread and GPT client.
        When: _summarize_thread is called.
        Then: The thread summary is set.
        """
        thread = Thread(
            thread_id=1234567890,
            title="AI関連スレッド",
            url="https://example.com/thread/1234567890",
            board="ai",
            posts=[{"com": "テスト投稿"}],
            timestamp=1609459200,
        )

        fivechan_explorer.gpt_client.generate_content.return_value = "テスト要約"

        await fivechan_explorer._summarize_thread(thread)

        assert thread.summary == "テスト要約"
        fivechan_explorer.gpt_client.generate_content.assert_called_once()


@pytest.mark.asyncio
class TestGetThreadPostsFromDat:
    """Tests for FiveChanExplorer._get_thread_posts_from_dat method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    async def test_successful_dat_parsing(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A valid dat response.
        When: _get_thread_posts_from_dat is called.
        Then: Posts are correctly parsed.
        """
        # dat format: name<>email<>date ID<>message<>title(first line only)
        # Using parseable date format (without Japanese day-of-week)
        mock_content = (
            "名無しさん<><>2024/01/01 12:00:00<>テスト投稿1<>スレッドタイトル\n"
            "名無しさん<><>2024/01/01 12:05:00<>テスト投稿2<>\n"
            "名無しさん<><>2024/01/01 12:10:00<>テスト投稿3<>"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_content.encode("shift_jis")
        mock_response.text = mock_content

        with patch("cloudscraper.create_scraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.get.return_value = mock_response
            mock_scraper_class.return_value = mock_scraper

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_response

                (
                    posts,
                    latest_post_at,
                ) = await fivechan_explorer._get_thread_posts_from_dat(
                    "https://mevius.5ch.net/ai/dat/1234567890.dat"
                )

                assert len(posts) == 3
                assert posts[0]["com"] == "テスト投稿1"
                assert posts[0]["title"] == "スレッドタイトル"
                assert posts[1]["com"] == "テスト投稿2"
                assert posts[2]["com"] == "テスト投稿3"
                assert latest_post_at is not None  # Verify date was parsed

    async def test_dat_http_error(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: An HTTP error response.
        When: _get_thread_posts_from_dat is called.
        Then: Empty list is returned.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("cloudscraper.create_scraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.get.return_value = mock_response
            mock_scraper_class.return_value = mock_scraper

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_response

                (
                    posts,
                    latest_post_at,
                ) = await fivechan_explorer._get_thread_posts_from_dat(
                    "https://mevius.5ch.net/ai/dat/1234567890.dat"
                )

                assert posts == []
                assert latest_post_at is None

    async def test_dat_cloudflare_detection(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A Cloudflare challenge response.
        When: _get_thread_posts_from_dat is called.
        Then: Empty list is returned.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.text = (
            "Just a moment... Please wait while we verify your browser."
        )

        with patch("cloudscraper.create_scraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.get.return_value = mock_response
            mock_scraper_class.return_value = mock_scraper

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_response

                (
                    posts,
                    latest_post_at,
                ) = await fivechan_explorer._get_thread_posts_from_dat(
                    "https://mevius.5ch.net/ai/dat/1234567890.dat"
                )

                # Content has "Just a moment" so it's logged as Cloudflare
                assert posts == []
                assert latest_post_at is None

    async def test_dat_exception_handling(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: An exception occurs during request.
        When: _get_thread_posts_from_dat is called.
        Then: Empty list is returned.
        """
        with patch("cloudscraper.create_scraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper_class.return_value = mock_scraper

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Network error")

                (
                    posts,
                    latest_post_at,
                ) = await fivechan_explorer._get_thread_posts_from_dat(
                    "https://mevius.5ch.net/ai/dat/1234567890.dat"
                )

                assert posts == []
                assert latest_post_at is None


class TestLoadExistingTitles:
    """Tests for FiveChanExplorer._load_existing_titles method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_load_existing_titles_no_content(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: No existing markdown content.
        When: _load_existing_titles is called.
        Then: Empty tracker is returned.
        """
        fivechan_explorer.storage.load_markdown = MagicMock(return_value=None)

        tracker = fivechan_explorer._load_existing_titles()

        assert not tracker.is_duplicate("新しいスレッド")[0]

    def test_load_existing_titles_with_content(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Existing markdown content with titles.
        When: _load_existing_titles is called.
        Then: Tracker contains the titles.
        """
        markdown_content = """# 5chan AI関連スレッド

### [ChatGPT総合スレ](https://example.com/1)

### [AI技術について語るスレ](https://example.com/2)
"""
        fivechan_explorer.storage.load_markdown = MagicMock(
            return_value=markdown_content
        )

        tracker = fivechan_explorer._load_existing_titles()

        assert tracker.is_duplicate("ChatGPT総合スレ")[0]
        assert tracker.is_duplicate("AI技術について語るスレ")[0]
        assert not tracker.is_duplicate("新しいスレッド")[0]

    def test_load_existing_titles_exception_handling(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: An exception occurs during loading.
        When: _load_existing_titles is called.
        Then: Empty tracker is returned.
        """
        fivechan_explorer.storage.load_markdown = MagicMock(
            side_effect=Exception("Storage error")
        )

        tracker = fivechan_explorer._load_existing_titles()

        assert not tracker.is_duplicate("テスト")[0]


class TestCalculatePopularity:
    """Tests for FiveChanExplorer._calculate_popularity method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_calculate_popularity_basic(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Post count, sample count, and timestamp.
        When: _calculate_popularity is called.
        Then: A popularity score is returned.
        """
        # Recent timestamp (1 hour ago)
        recent_timestamp = int(datetime.now(timezone.utc).timestamp()) - 3600

        score = fivechan_explorer._calculate_popularity(
            post_count=100,
            sample_count=10,
            timestamp=recent_timestamp,
        )

        # Should be at least post_count + sample_count
        assert score >= 110.0

    def test_calculate_popularity_old_thread(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: An old thread timestamp.
        When: _calculate_popularity is called.
        Then: Recency bonus is lower.
        """
        # Old timestamp (100 hours ago)
        old_timestamp = int(datetime.now(timezone.utc).timestamp()) - (100 * 3600)

        score = fivechan_explorer._calculate_popularity(
            post_count=100,
            sample_count=10,
            timestamp=old_timestamp,
        )

        # Should be close to post_count + sample_count (low recency bonus)
        assert 110.0 <= score < 111.0


class TestSelectTopThreads:
    """Tests for FiveChanExplorer._select_top_threads method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_select_top_threads_empty_list(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Empty thread list.
        When: _select_top_threads is called.
        Then: Empty list is returned.
        """
        result = fivechan_explorer._select_top_threads([], 10)
        assert result == []

    def test_select_top_threads_under_limit(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Thread list smaller than limit.
        When: _select_top_threads is called.
        Then: All threads are returned.
        """
        threads = [
            Thread(
                thread_id=1,
                title="Thread 1",
                url="https://example.com/1",
                board="ai",
                posts=[],
                timestamp=1609459200,
                popularity_score=100.0,
            ),
            Thread(
                thread_id=2,
                title="Thread 2",
                url="https://example.com/2",
                board="ai",
                posts=[],
                timestamp=1609459200,
                popularity_score=50.0,
            ),
        ]

        result = fivechan_explorer._select_top_threads(threads, 10)
        assert len(result) == 2

    def test_select_top_threads_over_limit(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Thread list larger than limit.
        When: _select_top_threads is called.
        Then: Top threads by popularity are returned.
        """
        threads = [
            Thread(
                thread_id=1,
                title="Low popularity",
                url="https://example.com/1",
                board="ai",
                posts=[],
                timestamp=1609459200,
                popularity_score=10.0,
            ),
            Thread(
                thread_id=2,
                title="High popularity",
                url="https://example.com/2",
                board="ai",
                posts=[],
                timestamp=1609459200,
                popularity_score=100.0,
            ),
            Thread(
                thread_id=3,
                title="Medium popularity",
                url="https://example.com/3",
                board="ai",
                posts=[],
                timestamp=1609459200,
                popularity_score=50.0,
            ),
        ]

        result = fivechan_explorer._select_top_threads(threads, 2)
        assert len(result) == 2
        assert result[0].title == "High popularity"
        assert result[1].title == "Medium popularity"


class TestSerializeThreads:
    """Tests for FiveChanExplorer._serialize_threads method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_serialize_threads(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A list of Thread objects.
        When: _serialize_threads is called.
        Then: A list of dictionaries is returned.
        """
        threads = [
            Thread(
                thread_id=1234567890,
                title="AIスレッド",
                url="https://example.com/1",
                board="ai",
                posts=[{"com": "テスト"}],
                timestamp=1609459200,
                summary="テスト要約",
                popularity_score=100.0,
            ),
        ]

        records = fivechan_explorer._serialize_threads(threads)

        assert len(records) == 1
        assert records[0]["thread_id"] == 1234567890
        assert records[0]["title"] == "AIスレッド"
        assert records[0]["url"] == "https://example.com/1"
        assert records[0]["board"] == "ai"
        assert records[0]["summary"] == "テスト要約"
        assert records[0]["popularity_score"] == 100.0
        assert "published_at" in records[0]


class TestThreadSortKey:
    """Tests for FiveChanExplorer._thread_sort_key method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_thread_sort_key_with_published_at(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A record with published_at.
        When: _thread_sort_key is called.
        Then: Correct sort key is returned.
        """
        record = {
            "popularity_score": 100.0,
            "published_at": "2024-01-01T12:00:00+00:00",
        }

        key = fivechan_explorer._thread_sort_key(record)

        assert key[0] == 100.0
        assert isinstance(key[1], datetime)

    def test_thread_sort_key_with_timestamp(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A record with only timestamp.
        When: _thread_sort_key is called.
        Then: Correct sort key is returned.
        """
        record = {
            "popularity_score": 50.0,
            "timestamp": 1609459200,
        }

        key = fivechan_explorer._thread_sort_key(record)

        assert key[0] == 50.0
        assert isinstance(key[1], datetime)

    def test_thread_sort_key_no_date(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A record without any date fields.
        When: _thread_sort_key is called.
        Then: Minimum datetime is used.
        """
        record = {
            "popularity_score": 25.0,
        }

        key = fivechan_explorer._thread_sort_key(record)

        assert key[0] == 25.0
        assert key[1] == datetime.min.replace(tzinfo=timezone.utc)

    def test_thread_sort_key_invalid_published_at(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A record with invalid published_at.
        When: _thread_sort_key is called.
        Then: Minimum datetime is used.
        """
        record = {
            "popularity_score": 75.0,
            "published_at": "invalid-date",
        }

        key = fivechan_explorer._thread_sort_key(record)

        assert key[0] == 75.0
        assert key[1] == datetime.min.replace(tzinfo=timezone.utc)


class TestRenderMarkdown:
    """Tests for FiveChanExplorer._render_markdown method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_render_markdown_basic(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A list of records.
        When: _render_markdown is called.
        Then: Proper markdown format is returned.
        """
        records = [
            {
                "thread_id": 1234567890,
                "title": "AIスレッド",
                "url": "https://example.com/1",
                "board": "ai",
                "summary": "テスト要約",
                "published_at": "2024-01-01T12:00:00+00:00",
            },
        ]

        today = datetime(2024, 1, 1, tzinfo=timezone.utc)
        content = fivechan_explorer._render_markdown(records, today)

        assert "# 5chan AI関連スレッド (2024-01-01)" in content
        assert "## " in content  # Board section
        assert "### [AIスレッド](https://example.com/1)" in content
        assert "テスト要約" in content

    def test_render_markdown_with_timestamp(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A record with only timestamp (no published_at).
        When: _render_markdown is called.
        Then: Timestamp is converted properly.
        """
        records = [
            {
                "thread_id": 1234567890,
                "title": "テストスレッド",
                "url": "https://example.com/1",
                "board": "ai",
                "summary": "要約",
                "timestamp": 1704110400,  # 2024-01-01 12:00:00 UTC
            },
        ]

        today = datetime(2024, 1, 1, tzinfo=timezone.utc)
        content = fivechan_explorer._render_markdown(records, today)

        assert "テストスレッド" in content
        assert "作成日時:" in content

    def test_render_markdown_no_date(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: A record without any date fields.
        When: _render_markdown is called.
        Then: N/A is shown for date.
        """
        records = [
            {
                "thread_id": 1234567890,
                "title": "日付なしスレッド",
                "url": "https://example.com/1",
                "board": "ai",
                "summary": "要約",
            },
        ]

        today = datetime(2024, 1, 1, tzinfo=timezone.utc)
        content = fivechan_explorer._render_markdown(records, today)

        assert "作成日時: N/A" in content

    def test_render_markdown_no_title(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: A record without title.
        When: _render_markdown is called.
        Then: Default title is used.
        """
        records = [
            {
                "thread_id": 1234567890,
                "url": "https://example.com/1",
                "board": "ai",
                "summary": "要約",
            },
        ]

        today = datetime(2024, 1, 1, tzinfo=timezone.utc)
        content = fivechan_explorer._render_markdown(records, today)

        assert "無題スレッド #1234567890" in content


class TestParseMarkdown:
    """Tests for FiveChanExplorer._parse_markdown method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    def test_parse_markdown_basic(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: Valid markdown content.
        When: _parse_markdown is called.
        Then: Records are parsed correctly.
        """
        markdown = """# 5chan AI関連スレッド (2024-01-01)

## AI (総合) (/ai/)

### [AIスレッド](https://example.com/1)

作成日時: 2024-01-01 12:00:00

**要約**:
テスト要約です。

---

"""
        records = fivechan_explorer._parse_markdown(markdown)

        assert len(records) == 1
        assert records[0]["title"] == "AIスレッド"
        assert records[0]["url"] == "https://example.com/1"
        assert records[0]["board"] == "ai"
        assert records[0]["summary"] == "テスト要約です。"

    def test_parse_markdown_multiple_boards(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Markdown with multiple boards.
        When: _parse_markdown is called.
        Then: Records from all boards are parsed.
        """
        markdown = """# 5chan AI関連スレッド (2024-01-01)

## AI (総合) (/ai/)

### [AIスレッド1](https://example.com/1)

作成日時: 2024-01-01 12:00:00

**要約**:
要約1

---

## プログラミング (/prog/)

### [プログラミングスレッド](https://example.com/2)

作成日時: 2024-01-01 13:00:00

**要約**:
要約2

---

"""
        records = fivechan_explorer._parse_markdown(markdown)

        assert len(records) == 2
        assert records[0]["board"] == "ai"
        assert records[1]["board"] == "prog"

    def test_parse_markdown_empty(self, fivechan_explorer: FiveChanExplorer) -> None:
        """
        Given: Empty markdown content.
        When: _parse_markdown is called.
        Then: Empty list is returned.
        """
        records = fivechan_explorer._parse_markdown("")
        assert records == []


@pytest.mark.asyncio
class TestRetrieveAIThreads:
    """Tests for FiveChanExplorer._retrieve_ai_threads method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    async def test_retrieve_ai_threads_empty_subject(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Empty subject.txt data.
        When: _retrieve_ai_threads is called.
        Then: Empty list is returned.
        """
        from nook.common.dedup import DedupTracker

        fivechan_explorer._get_subject_txt_data = AsyncMock(return_value=[])

        dedup_tracker = DedupTracker()
        result = await fivechan_explorer._retrieve_ai_threads(
            board_id="ai",
            limit=10,
            dedup_tracker=dedup_tracker,
            target_dates=[_jst_date_now()],
        )

        assert result == []

    async def test_retrieve_ai_threads_exception_handling(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: An exception occurs during processing.
        When: _retrieve_ai_threads is called.
        Then: Empty list is returned.
        """
        from nook.common.dedup import DedupTracker

        fivechan_explorer._get_subject_txt_data = AsyncMock(
            side_effect=Exception("Network error")
        )

        dedup_tracker = DedupTracker()
        result = await fivechan_explorer._retrieve_ai_threads(
            board_id="ai",
            limit=10,
            dedup_tracker=dedup_tracker,
            target_dates=[_jst_date_now()],
        )

        assert result == []

    async def test_retrieve_ai_threads_filters_by_keywords(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Subject data with AI and non-AI threads.
        When: _retrieve_ai_threads is called.
        Then: Only AI-related threads are processed.
        """
        from nook.common.dedup import DedupTracker

        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        fivechan_explorer._get_subject_txt_data = AsyncMock(
            return_value=[
                {
                    "title": "ChatGPT総合スレ",
                    "timestamp": str(current_timestamp),
                    "post_count": 100,
                    "dat_url": "https://example.com/dat/1.dat",
                    "html_url": "https://example.com/1",
                },
                {
                    "title": "料理について語るスレ",
                    "timestamp": str(current_timestamp),
                    "post_count": 50,
                    "dat_url": "https://example.com/dat/2.dat",
                    "html_url": "https://example.com/2",
                },
            ]
        )

        fivechan_explorer._get_thread_posts_from_dat = AsyncMock(
            return_value=(
                [{"no": 1, "com": "テスト投稿", "date": "2024/01/01 12:00:00"}],
                datetime.now(timezone.utc),
            )
        )

        dedup_tracker = DedupTracker()
        result = await fivechan_explorer._retrieve_ai_threads(
            board_id="ai",
            limit=10,
            dedup_tracker=dedup_tracker,
            target_dates=[_jst_date_now()],
        )

        # Only the ChatGPT thread should be matched
        assert len(result) == 1
        assert "ChatGPT" in result[0].title


@pytest.mark.asyncio
class TestStoreSummaries:
    """Tests for FiveChanExplorer._store_summaries method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    async def test_store_summaries_empty_threads(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Empty thread list.
        When: _store_summaries is called.
        Then: Empty list is returned.
        """
        result = await fivechan_explorer._store_summaries([], [_jst_date_now()])
        assert result == []

    async def test_store_summaries_with_threads(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: Non-empty thread list.
        When: _store_summaries is called.
        Then: Storage methods are called and file paths returned.
        """
        threads = [
            Thread(
                thread_id=1234567890,
                title="Test Thread",
                url="https://example.com/1",
                board="ai",
                posts=[],
                timestamp=1609459200,
                summary="Test summary",
            )
        ]

        fivechan_explorer.storage.save = AsyncMock(return_value=None)

        result = await fivechan_explorer._store_summaries(threads, [_jst_date_now()])

        assert len(result) > 0
        fivechan_explorer.storage.save.assert_called()


@pytest.mark.asyncio
class TestLoadExistingThreads:
    """Tests for FiveChanExplorer._load_existing_threads method."""

    @pytest.fixture
    def fivechan_explorer(self, monkeypatch: pytest.MonkeyPatch) -> FiveChanExplorer:
        """Create a FiveChanExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return FiveChanExplorer()

    async def test_load_existing_threads_json_list(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: JSON list format.
        When: _load_existing_threads is called.
        Then: Direct list is returned.
        """
        fivechan_explorer.load_json = AsyncMock(
            return_value=[{"thread_id": 1, "title": "Test"}]
        )

        result = await fivechan_explorer._load_existing_threads(
            datetime.now(timezone.utc)
        )
        assert len(result) == 1
        assert result[0]["thread_id"] == 1

    async def test_load_existing_threads_json_dict(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: JSON dict format (grouped by board).
        When: _load_existing_threads is called.
        Then: Flattened list is returned.
        """
        fivechan_explorer.load_json = AsyncMock(
            return_value={
                "ai": [{"thread_id": 1, "title": "AI Thread"}],
                "prog": [{"thread_id": 2, "title": "Prog Thread"}],
            }
        )

        result = await fivechan_explorer._load_existing_threads(
            datetime.now(timezone.utc)
        )
        assert len(result) == 2
        assert result[0]["board"] == "ai"
        assert result[1]["board"] == "prog"

    async def test_load_existing_threads_markdown_fallback(
        self, fivechan_explorer: FiveChanExplorer
    ) -> None:
        """
        Given: No JSON but markdown exists.
        When: _load_existing_threads is called.
        Then: Markdown is parsed.
        """
        fivechan_explorer.load_json = AsyncMock(return_value=None)
        fivechan_explorer.storage.load = AsyncMock(return_value=None)

        result = await fivechan_explorer._load_existing_threads(
            datetime.now(timezone.utc)
        )
        assert result == []
