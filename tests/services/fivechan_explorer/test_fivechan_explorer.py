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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
        from datetime import datetime, timezone

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
                                result = await fivechan_explorer.collect()
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
