"""Additional coverage tests for fivechan_explorer service.

This module adds tests for previously uncovered code paths:
- _get_with_retry: Rate limiting (429), Server errors (503), Exception handling
- _get_with_403_tolerance: Cloudflare bypass strategies
- _try_alternative_endpoints: Alternative endpoint strategies
- _thread_sort_key: Edge cases with missing/invalid data
- _render_markdown: Date fallback handling
- _load_existing_threads: Dict flattening, Markdown fallback
- _calculate_popularity: Exception handling
- collect: Thread sorting when > limit
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.fivechan.fivechan_explorer import FiveChanExplorer, Thread


def _jst_date_now() -> date:
    """Return the current date in JST timezone.

    Note: Uses datetime.now() rather than a fixed date because:
    1. Tests verify behavior with 'current' timestamps (created_utc)
    2. Fixed dates would fail when combined with datetime.now() timestamps
    3. is_within_target_dates() compares JST-converted dates, so we need matching JST dates
    """
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).date()


@pytest.fixture
def mock_fivechan_explorer(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")
    explorer = FiveChanExplorer(storage_dir=str(tmp_path))
    explorer.http_client = AsyncMock()
    explorer.gpt_client = AsyncMock()
    return explorer


class TestGetWithRetryRateLimiting:
    """Tests for _get_with_retry rate limiting handling (lines 268-280)."""

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_after_header(self, mock_fivechan_explorer):
        """
        Given: A 429 response with Retry-After header
        When: _get_with_retry is called
        Then: It waits the specified time and retries
        """
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_fivechan_explorer.http_client.get = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await mock_fivechan_explorer._get_with_retry(
                "https://test.com", max_retries=1
            )

        assert result.status_code == 200
        mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_rate_limit_without_retry_after_header(self, mock_fivechan_explorer):
        """
        Given: A 429 response without Retry-After header
        When: _get_with_retry is called
        Then: It uses exponential backoff
        """
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_fivechan_explorer.http_client.get = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await mock_fivechan_explorer._get_with_retry(
                "https://test.com", max_retries=1
            )

        assert result.status_code == 200
        mock_sleep.assert_called()


class TestGetWithRetryServerError:
    """Tests for _get_with_retry server error handling (lines 283-290)."""

    @pytest.mark.asyncio
    async def test_server_error_retry(self, mock_fivechan_explorer):
        """
        Given: A 503 server error
        When: _get_with_retry is called
        Then: It retries with backoff
        """
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_fivechan_explorer.http_client.get = AsyncMock(
            side_effect=[mock_response_503, mock_response_200]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_retry(
                "https://test.com", max_retries=1
            )

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_server_error_returns_response_after_max_retries(
        self, mock_fivechan_explorer
    ):
        """
        Given: Persistent 503 errors
        When: _get_with_retry exhausts retries
        Then: It returns the error response
        """
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503

        mock_fivechan_explorer.http_client.get = AsyncMock(
            return_value=mock_response_503
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_retry(
                "https://test.com", max_retries=0
            )

        assert result.status_code == 503


class TestGetWithRetryException:
    """Tests for _get_with_retry exception handling (lines 296-304)."""

    @pytest.mark.asyncio
    async def test_exception_retry(self, mock_fivechan_explorer):
        """
        Given: A request raises an exception
        When: _get_with_retry is called
        Then: It retries with backoff
        """
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_fivechan_explorer.http_client.get = AsyncMock(
            side_effect=[Exception("Network error"), mock_response_200]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_retry(
                "https://test.com", max_retries=1
            )

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_exception_raised_after_max_retries(self, mock_fivechan_explorer):
        """
        Given: Persistent exceptions
        When: _get_with_retry exhausts retries
        Then: It raises the exception
        """
        mock_fivechan_explorer.http_client.get = AsyncMock(
            side_effect=Exception("Network error")
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Network error"):
                await mock_fivechan_explorer._get_with_retry(
                    "https://test.com", max_retries=0
                )


class TestCollectThreadSorting:
    """Tests for collect method thread sorting (lines 405-412)."""

    @pytest.mark.asyncio
    async def test_collect_sorts_threads_when_exceeds_limit(
        self, mock_fivechan_explorer
    ):
        """
        Given: More threads than the limit
        When: collect is called
        Then: Threads are sorted by popularity and limited
        """
        # Create multiple threads
        threads = [
            Thread(
                thread_id=i,
                title=f"Thread {i}",
                url=f"https://url{i}",
                board="ai",
                posts=[],
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                popularity_score=float(i * 10),
            )
            for i in range(20)
        ]

        mock_fivechan_explorer._retrieve_ai_threads = AsyncMock(return_value=threads)
        mock_fivechan_explorer._summarize_thread = AsyncMock()
        mock_fivechan_explorer._store_summaries = AsyncMock(return_value=[])
        mock_fivechan_explorer.target_boards = {"ai": "人工知能"}
        mock_fivechan_explorer.TOTAL_LIMIT = 5

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mock_fivechan_explorer.collect(target_dates=[_jst_date_now()])

        # Verify summarize was called for limited threads
        assert mock_fivechan_explorer._summarize_thread.call_count <= 5


class TestCollectNoSavedFiles:
    """Tests for collect when _store_summaries returns empty (line 447)."""

    @pytest.mark.asyncio
    async def test_collect_no_saved_files_logs_correctly(self, mock_fivechan_explorer):
        """
        Given: Selected threads but _store_summaries returns empty
        When: collect is called
        Then: No new articles message is logged
        """
        thread = Thread(
            thread_id=1,
            title="Thread",
            url="https://url",
            board="ai",
            posts=[],
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )

        mock_fivechan_explorer._retrieve_ai_threads = AsyncMock(return_value=[thread])
        mock_fivechan_explorer._summarize_thread = AsyncMock()
        mock_fivechan_explorer._store_summaries = AsyncMock(return_value=[])
        mock_fivechan_explorer.target_boards = {"ai": "人工知能"}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer.collect(
                target_dates=[_jst_date_now()]
            )

        assert result == []


class TestBoardError:
    """Tests for board processing error (line 381-382)."""

    @pytest.mark.asyncio
    async def test_board_error_continues_processing(self, mock_fivechan_explorer):
        """
        Given: One board raises an exception
        When: collect is called
        Then: Processing continues with other boards
        """
        mock_fivechan_explorer.target_boards = {"ai": "AI", "tech": "Tech"}
        mock_fivechan_explorer._retrieve_ai_threads = AsyncMock(
            side_effect=[Exception("Board error"), []]
        )
        mock_fivechan_explorer._store_summaries = AsyncMock(return_value=[])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mock_fivechan_explorer.collect(target_dates=[_jst_date_now()])

        # Should have tried both boards
        assert mock_fivechan_explorer._retrieve_ai_threads.call_count == 2


class TestThreadSortKeyEdgeCases:
    """Tests for _thread_sort_key edge cases (lines 1191-1201)."""

    def test_sort_key_invalid_published_at(self, mock_fivechan_explorer):
        """
        Given: A record with invalid published_at format
        When: _thread_sort_key is called
        Then: Returns minimum datetime
        """
        item = {"popularity_score": 10.0, "published_at": "invalid-date"}
        result = mock_fivechan_explorer._thread_sort_key(item)

        assert result[0] == 10.0
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)

    def test_sort_key_uses_timestamp_when_no_published_at(self, mock_fivechan_explorer):
        """
        Given: A record with timestamp but no published_at
        When: _thread_sort_key is called
        Then: Uses timestamp to calculate datetime
        """
        timestamp = int(datetime(2023, 6, 1, tzinfo=timezone.utc).timestamp())
        item = {"popularity_score": 5.0, "timestamp": timestamp}
        result = mock_fivechan_explorer._thread_sort_key(item)

        assert result[0] == 5.0
        assert result[1].year == 2023

    def test_sort_key_invalid_timestamp(self, mock_fivechan_explorer):
        """
        Given: A record with invalid timestamp
        When: _thread_sort_key is called
        Then: Returns minimum datetime
        """
        item = {"popularity_score": 5.0, "timestamp": "not-a-number"}
        result = mock_fivechan_explorer._thread_sort_key(item)

        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)

    def test_sort_key_no_date_info(self, mock_fivechan_explorer):
        """
        Given: A record with no date info
        When: _thread_sort_key is called
        Then: Returns minimum datetime
        """
        item = {"popularity_score": 5.0}
        result = mock_fivechan_explorer._thread_sort_key(item)

        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)


class TestRenderMarkdownDateFallback:
    """Tests for _render_markdown date fallback (lines 1225-1237)."""

    def test_render_markdown_invalid_published_at(self, mock_fivechan_explorer):
        """
        Given: A record with invalid published_at
        When: _render_markdown is called
        Then: Uses raw published_at string
        """
        records = [
            {"board": "ai", "title": "Test", "url": "url", "published_at": "bad"}
        ]
        result = mock_fivechan_explorer._render_markdown(
            records, datetime(2023, 1, 1, tzinfo=timezone.utc)
        )

        assert "作成日時: bad" in result

    def test_render_markdown_uses_timestamp_fallback(self, mock_fivechan_explorer):
        """
        Given: A record with timestamp but no published_at
        When: _render_markdown is called
        Then: Uses timestamp for date string
        """
        timestamp = int(datetime(2023, 6, 1, 12, 0, 0).timestamp())
        records = [
            {"board": "ai", "title": "Test", "url": "url", "timestamp": timestamp}
        ]
        result = mock_fivechan_explorer._render_markdown(
            records, datetime(2023, 1, 1, tzinfo=timezone.utc)
        )

        assert "2023-06-01" in result

    def test_render_markdown_invalid_timestamp(self, mock_fivechan_explorer):
        """
        Given: A record with invalid timestamp
        When: _render_markdown is called
        Then: Uses N/A for date string
        """
        records = [{"board": "ai", "title": "Test", "url": "url", "timestamp": "bad"}]
        result = mock_fivechan_explorer._render_markdown(
            records, datetime(2023, 1, 1, tzinfo=timezone.utc)
        )

        assert "作成日時: N/A" in result

    def test_render_markdown_no_date_info(self, mock_fivechan_explorer):
        """
        Given: A record with no date info
        When: _render_markdown is called
        Then: Uses N/A for date string
        """
        records = [{"board": "ai", "title": "Test", "url": "url"}]
        result = mock_fivechan_explorer._render_markdown(
            records, datetime(2023, 1, 1, tzinfo=timezone.utc)
        )

        assert "作成日時: N/A" in result


class TestLoadExistingThreads:
    """Tests for _load_existing_threads (lines 1170-1182)."""

    @pytest.mark.asyncio
    async def test_load_existing_threads_flattens_dict(self, mock_fivechan_explorer):
        """
        Given: JSON file with dict structure
        When: _load_existing_threads is called
        Then: It flattens to list with board info
        """
        mock_fivechan_explorer.load_json = AsyncMock(
            return_value={"ai": [{"thread_id": 1}], "tech": [{"thread_id": 2}]}
        )

        result = await mock_fivechan_explorer._load_existing_threads(
            datetime(2023, 1, 1)
        )

        assert len(result) == 2
        assert result[0]["board"] == "ai"
        assert result[1]["board"] == "tech"

    @pytest.mark.asyncio
    async def test_load_existing_threads_returns_list_directly(
        self, mock_fivechan_explorer
    ):
        """
        Given: JSON file with list structure
        When: _load_existing_threads is called
        Then: It returns the list directly
        """
        mock_fivechan_explorer.load_json = AsyncMock(
            return_value=[{"thread_id": 1, "board": "ai"}]
        )

        result = await mock_fivechan_explorer._load_existing_threads(
            datetime(2023, 1, 1)
        )

        assert len(result) == 1
        assert result[0]["thread_id"] == 1

    @pytest.mark.asyncio
    async def test_load_existing_threads_markdown_fallback(
        self, mock_fivechan_explorer
    ):
        """
        Given: No JSON file but Markdown exists
        When: _load_existing_threads is called
        Then: It parses Markdown
        """
        mock_fivechan_explorer.load_json = AsyncMock(return_value=None)
        mock_fivechan_explorer.storage.load = AsyncMock(
            return_value="""# 5chan AI関連スレッド (2023-01-01)

## 人工知能 (/ai/)

### [Test Thread](https://url)

作成日時: 2023-01-01 12:00:00

**要約**:
Summary text
---"""
        )

        result = await mock_fivechan_explorer._load_existing_threads(
            datetime(2023, 1, 1)
        )

        assert len(result) == 1
        assert result[0]["title"] == "Test Thread"

    @pytest.mark.asyncio
    async def test_load_existing_threads_no_data(self, mock_fivechan_explorer):
        """
        Given: No JSON and no Markdown
        When: _load_existing_threads is called
        Then: Returns empty list
        """
        mock_fivechan_explorer.load_json = AsyncMock(return_value=None)
        mock_fivechan_explorer.storage.load = AsyncMock(return_value=None)

        result = await mock_fivechan_explorer._load_existing_threads(
            datetime(2023, 1, 1)
        )

        assert result == []


class TestCalculatePopularityException:
    """Tests for _calculate_popularity exception handling (lines 1040-1041)."""

    def test_calculate_popularity_invalid_timestamp(self, mock_fivechan_explorer):
        """
        Given: An invalid timestamp
        When: _calculate_popularity is called
        Then: Returns score without recency bonus
        """
        # Very large timestamp that might cause issues
        result = mock_fivechan_explorer._calculate_popularity(
            post_count=10, sample_count=5, timestamp=-1
        )

        # Should still return a valid float
        assert isinstance(result, float)
        assert result >= 15.0  # At least post_count + sample_count


class TestLoadExistingTitlesException:
    """Tests for _load_existing_titles exception handling (lines 1027-1028)."""

    def test_load_existing_titles_exception(self, mock_fivechan_explorer):
        """
        Given: storage.load_markdown raises an exception
        When: _load_existing_titles is called
        Then: Returns empty tracker without raising
        """
        mock_fivechan_explorer.storage.load_markdown = MagicMock(
            side_effect=Exception("Storage error")
        )

        tracker = mock_fivechan_explorer._load_existing_titles()

        assert tracker.count() == 0


class TestRetrieveAiThreadsDuplicateSkip:
    """Tests for _retrieve_ai_threads duplicate skipping (lines 948-954)."""

    @pytest.mark.asyncio
    async def test_duplicate_thread_skipped(self, mock_fivechan_explorer):
        """
        Given: A duplicate thread
        When: _retrieve_ai_threads is called
        Then: The duplicate is skipped
        """
        thread_data = [
            {
                "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
                "title": "AI Thread",
                "post_count": 10,
                "dat_url": "https://dat.url",
                "html_url": "https://html.url",
                "server": "server",
            }
        ]

        mock_fivechan_explorer._get_subject_txt_data = AsyncMock(
            return_value=thread_data
        )

        # Mock tracker that says everything is duplicate
        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (True, "normalized")
        mock_tracker.get_original_title.return_value = "Original AI Thread"
        mock_fivechan_explorer._load_existing_titles = MagicMock(
            return_value=mock_tracker
        )

        result = await mock_fivechan_explorer._retrieve_ai_threads(
            "ai", None, mock_tracker, [_jst_date_now()]
        )

        assert len(result) == 0


class TestRetrieveAiThreadsLimit:
    """Tests for _retrieve_ai_threads limit handling (lines 1004-1006)."""

    @pytest.mark.asyncio
    async def test_thread_limit_stops_processing(self, mock_fivechan_explorer):
        """
        Given: A limit is set and successful thread fetches
        When: _retrieve_ai_threads is called
        Then: Processing stops at limit
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())
        thread_data = [
            {
                "timestamp": str(timestamp + i),
                "title": f"AI Thread {i}",
                "post_count": 10,
                "dat_url": f"https://dat.url/{i}",
                "html_url": f"https://html.url/{i}",
                "server": "server",
            }
            for i in range(5)
        ]

        mock_fivechan_explorer._get_subject_txt_data = AsyncMock(
            return_value=thread_data
        )
        mock_fivechan_explorer._get_thread_posts_from_dat = AsyncMock(
            return_value=([{"no": 1, "com": "text"}], datetime.now(timezone.utc))
        )

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")
        mock_tracker.add = MagicMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._retrieve_ai_threads(
                "ai", 2, mock_tracker, [_jst_date_now()]
            )

        assert len(result) == 2


class TestRetrieveAiThreadsNoPostsWarning:
    """Tests for _retrieve_ai_threads no posts warning (lines 1004-1006)."""

    @pytest.mark.asyncio
    async def test_no_posts_logs_warning(self, mock_fivechan_explorer):
        """
        Given: Thread data fetch returns no posts
        When: _retrieve_ai_threads is called
        Then: Warning is logged and thread not added
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())
        thread_data = [
            {
                "timestamp": str(timestamp),
                "title": "AI Thread",
                "post_count": 10,
                "dat_url": "https://dat.url",
                "html_url": "https://html.url",
                "server": "server",
            }
        ]

        mock_fivechan_explorer._get_subject_txt_data = AsyncMock(
            return_value=thread_data
        )
        mock_fivechan_explorer._get_thread_posts_from_dat = AsyncMock(
            return_value=([], None)
        )

        mock_tracker = MagicMock()
        mock_tracker.is_duplicate.return_value = (False, "norm")

        result = await mock_fivechan_explorer._retrieve_ai_threads(
            "ai", None, mock_tracker, [_jst_date_now()]
        )

        assert len(result) == 0


class TestGetWith403Tolerance:
    """Tests for _get_with_403_tolerance (lines 513-607)."""

    @pytest.mark.asyncio
    async def test_403_tolerance_success_on_first_strategy(
        self, mock_fivechan_explorer
    ):
        """
        Given: First strategy succeeds with valid content
        When: _get_with_403_tolerance is called
        Then: Returns the successful response
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Valid 5ch content"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_403_tolerance(
                "https://test.5ch.net/board/", "board"
            )

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_403_tolerance_cloudflare_detected(self, mock_fivechan_explorer):
        """
        Given: Cloudflare challenge page detected
        When: _get_with_403_tolerance is called
        Then: Retries with next strategy
        """
        cloudflare_response = MagicMock()
        cloudflare_response.status_code = 200
        cloudflare_response.text = "Just a moment... challenge page"

        valid_response = MagicMock()
        valid_response.status_code = 200
        valid_response.text = "Valid 5ch content"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[cloudflare_response, valid_response])
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            _ = await mock_fivechan_explorer._get_with_403_tolerance(
                "https://test.5ch.net/board/", "board"
            )

        # Should have tried multiple times
        assert mock_client.get.call_count >= 2

    @pytest.mark.asyncio
    async def test_403_tolerance_403_with_valid_content(self, mock_fivechan_explorer):
        """
        Given: 403 response but with valid content
        When: _get_with_403_tolerance is called
        Then: Returns the response
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "x" * 200  # Long content, not Cloudflare

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client
        mock_fivechan_explorer._try_alternative_endpoints = AsyncMock(return_value=None)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_403_tolerance(
                "https://test.5ch.net/board/", "board"
            )

        # Should accept 403 with long content (treated as valid, not Cloudflare)
        assert result is not None
        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_403_tolerance_all_strategies_fail(self, mock_fivechan_explorer):
        """
        Given: All strategies fail
        When: _get_with_403_tolerance is called
        Then: Returns None
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client
        mock_fivechan_explorer._try_alternative_endpoints = AsyncMock(return_value=None)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_403_tolerance(
                "https://test.5ch.net/board/", "board"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_403_tolerance_request_exception(self, mock_fivechan_explorer):
        """
        Given: Request raises exception
        When: _get_with_403_tolerance is called
        Then: Continues to next strategy
        """
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_fivechan_explorer.http_client._client = mock_client
        mock_fivechan_explorer._try_alternative_endpoints = AsyncMock(return_value=None)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._get_with_403_tolerance(
                "https://test.5ch.net/board/", "board"
            )

        assert result is None


class TestTryAlternativeEndpoints:
    """Tests for _try_alternative_endpoints (lines 626-692)."""

    @pytest.mark.asyncio
    async def test_alternative_endpoint_success(self, mock_fivechan_explorer):
        """
        Given: An alternative endpoint returns valid content
        When: _try_alternative_endpoints is called
        Then: Returns the successful response
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Valid 5ch content with some text that is longer than fifty characters to pass validation"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._try_alternative_endpoints(
                "https://test.5ch.net/board/", "board"
            )

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_alternative_endpoint_403_with_valid_content(
        self, mock_fivechan_explorer
    ):
        """
        Given: Alternative endpoint returns 403 but with valid content
        When: _try_alternative_endpoints is called
        Then: Returns the response as valid
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "5ch content with enough text to pass the length validation check and newlines\n"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._try_alternative_endpoints(
                "https://test.5ch.net/board/", "board"
            )

        assert result is not None
        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_alternative_endpoint_cloudflare_content(
        self, mock_fivechan_explorer
    ):
        """
        Given: Alternative endpoint returns Cloudflare challenge
        When: _try_alternative_endpoints is called
        Then: Tries next alternative
        """
        cloudflare_response = MagicMock()
        cloudflare_response.status_code = 200
        cloudflare_response.text = "Just a moment challenge page"

        valid_response = MagicMock()
        valid_response.status_code = 200
        valid_response.text = "Valid 5ch content"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[cloudflare_response, valid_response])
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            _ = await mock_fivechan_explorer._try_alternative_endpoints(
                "https://test.5ch.net/board/", "board"
            )

        # Should have tried multiple alternatives
        assert mock_client.get.call_count >= 2

    @pytest.mark.asyncio
    async def test_alternative_endpoint_all_fail(self, mock_fivechan_explorer):
        """
        Given: All alternative endpoints fail
        When: _try_alternative_endpoints is called
        Then: Returns None
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = ""

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._try_alternative_endpoints(
                "https://test.5ch.net/board/", "board"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_alternative_endpoint_exception(self, mock_fivechan_explorer):
        """
        Given: Alternative endpoint request raises exception
        When: _try_alternative_endpoints is called
        Then: Continues to next alternative
        """
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_fivechan_explorer.http_client._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await mock_fivechan_explorer._try_alternative_endpoints(
                "https://test.5ch.net/board/", "board"
            )

        assert result is None


class TestParseMarkdownEdgeCases:
    """Tests for _parse_markdown edge cases (lines 1269-1270)."""

    def test_parse_markdown_invalid_datetime(self, mock_fivechan_explorer):
        """
        Given: Markdown with invalid datetime format
        When: _parse_markdown is called
        Then: Parses without published_at and timestamp
        """
        markdown = """# 5chan AI関連スレッド (2023-01-01)

## 人工知能 (/ai/)

### [Test Thread](https://url)

作成日時: invalid-datetime

**要約**:
Summary text
---"""

        result = mock_fivechan_explorer._parse_markdown(markdown)

        assert len(result) == 1
        assert result[0]["title"] == "Test Thread"
        assert "published_at" not in result[0]
