"""Tests for arxiv_summarizer collect flow.

This module tests the collect method flow of ArxivSummarizer by mocking
external dependencies:
- _get_curated_paper_ids
- _retrieve_paper_info
- _summarize_paper_info
- _store_summaries
- _save_processed_ids_by_date
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer, PaperInfo


@pytest.fixture
def summarizer(monkeypatch: pytest.MonkeyPatch) -> ArxivSummarizer:
    """
    Create an ArxivSummarizer instance for testing.

    Given: Environment variable OPENAI_API_KEY is set to a dummy value.
    When: ArxivSummarizer is instantiated.
    Then: A valid summarizer instance is returned.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
    return ArxivSummarizer()


@pytest.fixture
def sample_paper_info() -> PaperInfo:
    """Create a sample PaperInfo for testing."""
    paper = PaperInfo(
        title="Test Paper Title",
        abstract="This is a test abstract.",
        url="https://arxiv.org/abs/2401.00001",
        contents="This is the paper contents.",
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )
    paper.summary = "Test summary"
    return paper


class TestCollectFlow:
    """Tests for ArxivSummarizer.collect method flow."""

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_no_paper_ids_found(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: _get_curated_paper_ids returns None (no URL found).
        When: collect is called.
        Then: An empty list is returned.
        """
        # Given
        target_dates = [date(2024, 1, 15)]

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                mock_get_ids.return_value = None

                # When
                result = await summarizer.collect(limit=5, target_dates=target_dates)

                # Then
                assert result == []
                mock_get_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_paper_ids_list_is_empty(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: _get_curated_paper_ids returns an empty list.
        When: collect is called.
        Then: An empty list is returned.
        """
        # Given
        target_dates = [date(2024, 1, 15)]

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                mock_get_ids.return_value = []

                # When
                result = await summarizer.collect(limit=5, target_dates=target_dates)

                # Then
                assert result == []

    @pytest.mark.asyncio
    async def test_collect_processes_papers_and_returns_saved_files(
        self, summarizer: ArxivSummarizer, sample_paper_info: PaperInfo
    ) -> None:
        """
        Given: Valid paper IDs and paper info are available.
        When: collect is called.
        Then: Papers are processed and saved files are returned.
        """
        # Given
        target_dates = [date(2024, 1, 15)]
        paper_ids = ["2401.00001", "2401.00002"]
        saved_files = [("path/to/2024-01-15.json", "path/to/2024-01-15.md")]

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                with patch.object(
                    summarizer, "_retrieve_paper_info", new_callable=AsyncMock
                ) as mock_retrieve:
                    with patch.object(
                        summarizer, "_summarize_paper_info", new_callable=AsyncMock
                    ):
                        with patch.object(
                            summarizer, "_store_summaries", new_callable=AsyncMock
                        ) as mock_store:
                            with patch.object(
                                summarizer,
                                "_save_processed_ids_by_date",
                                new_callable=AsyncMock,
                            ) as mock_save_ids:
                                mock_get_ids.return_value = paper_ids
                                mock_retrieve.return_value = sample_paper_info
                                mock_store.return_value = saved_files

                                # When
                                result = await summarizer.collect(
                                    limit=5, target_dates=target_dates
                                )

                                # Then
                                assert result == saved_files
                                mock_get_ids.assert_called_once()
                                assert mock_retrieve.call_count == len(paper_ids)
                                mock_store.assert_called_once()
                                mock_save_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_filters_papers_by_target_dates(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Papers with different published dates.
        When: collect is called with specific target_dates.
        Then: Only papers within target dates are processed.
        """
        # Given
        target_dates = [date(2024, 1, 15)]
        paper_ids = ["2401.00001"]

        # Paper outside target date
        paper_outside_date = PaperInfo(
            title="Outside Date Paper",
            abstract="Abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Contents",
            published_at=datetime(2024, 1, 10, tzinfo=timezone.utc),  # Before target
        )
        paper_outside_date.summary = "Summary"

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                with patch.object(
                    summarizer, "_retrieve_paper_info", new_callable=AsyncMock
                ) as mock_retrieve:
                    with patch.object(
                        summarizer, "_store_summaries", new_callable=AsyncMock
                    ) as mock_store:
                        with patch.object(
                            summarizer,
                            "_save_processed_ids_by_date",
                            new_callable=AsyncMock,
                        ):
                            mock_get_ids.return_value = paper_ids
                            mock_retrieve.return_value = paper_outside_date
                            mock_store.return_value = []

                            # When
                            await summarizer.collect(limit=5, target_dates=target_dates)

                            # Then
                            # Paper is filtered out because published_at is outside target dates
                            # store_summaries is called with empty papers list
                            mock_store.assert_called_once()
                            call_args = mock_store.call_args
                            papers_arg = call_args[0][0]
                            assert len(papers_arg) == 0

    @pytest.mark.asyncio
    async def test_collect_handles_retrieve_exceptions(
        self, summarizer: ArxivSummarizer, sample_paper_info: PaperInfo
    ) -> None:
        """
        Given: _retrieve_paper_info raises an exception for some papers.
        When: collect is called.
        Then: Exceptions are logged and other papers are still processed.
        """
        # Given
        target_dates = [date(2024, 1, 15)]
        paper_ids = ["2401.00001", "2401.00002"]
        saved_files = [("path/to/2024-01-15.json", "path/to/2024-01-15.md")]

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                with patch.object(
                    summarizer, "_retrieve_paper_info", new_callable=AsyncMock
                ) as mock_retrieve:
                    with patch.object(
                        summarizer, "_summarize_paper_info", new_callable=AsyncMock
                    ):
                        with patch.object(
                            summarizer, "_store_summaries", new_callable=AsyncMock
                        ) as mock_store:
                            with patch.object(
                                summarizer,
                                "_save_processed_ids_by_date",
                                new_callable=AsyncMock,
                            ):
                                mock_get_ids.return_value = paper_ids
                                # First call raises exception, second returns valid paper
                                mock_retrieve.side_effect = [
                                    Exception("Network error"),
                                    sample_paper_info,
                                ]
                                mock_store.return_value = saved_files

                                # When
                                result = await summarizer.collect(
                                    limit=5, target_dates=target_dates
                                )

                                # Then
                                # Should still return saved files from successful paper
                                assert result == saved_files

    @pytest.mark.asyncio
    async def test_collect_deduplicates_paper_ids_across_dates(
        self, summarizer: ArxivSummarizer, sample_paper_info: PaperInfo
    ) -> None:
        """
        Given: Same paper ID appears in multiple dates.
        When: collect is called with multiple target_dates.
        Then: Paper is only retrieved once.
        """
        # Given
        target_dates = [date(2024, 1, 15), date(2024, 1, 16)]

        with patch.object(summarizer, "setup_http_client", new_callable=AsyncMock):
            with patch.object(
                summarizer, "_get_curated_paper_ids", new_callable=AsyncMock
            ) as mock_get_ids:
                with patch.object(
                    summarizer, "_retrieve_paper_info", new_callable=AsyncMock
                ) as mock_retrieve:
                    with patch.object(
                        summarizer, "_summarize_paper_info", new_callable=AsyncMock
                    ):
                        with patch.object(
                            summarizer, "_store_summaries", new_callable=AsyncMock
                        ) as mock_store:
                            with patch.object(
                                summarizer,
                                "_save_processed_ids_by_date",
                                new_callable=AsyncMock,
                            ):
                                # Same paper ID returned for both dates
                                mock_get_ids.side_effect = [
                                    ["2401.00001"],  # First date
                                    ["2401.00001"],  # Second date (duplicate)
                                ]
                                mock_retrieve.return_value = sample_paper_info
                                mock_store.return_value = []

                                # When
                                await summarizer.collect(
                                    limit=5, target_dates=target_dates
                                )

                                # Then
                                # Paper should only be retrieved once due to deduplication
                                assert mock_retrieve.call_count == 1

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_target_dates_is_empty(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: target_dates is empty.
        When: collect is called.
        Then: Empty list is returned immediately.
        """
        # Given
        target_dates = []

        # When
        result = await summarizer.collect(limit=5, target_dates=target_dates)

        # Then
        assert result == []


class TestPaperInfoDataclass:
    """Tests for PaperInfo dataclass."""

    def test_paper_info_creation(self) -> None:
        """
        Given: Valid paper information.
        When: PaperInfo is created.
        Then: All fields are correctly set.
        """
        # Given / When
        paper = PaperInfo(
            title="Test Title",
            abstract="Test Abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test Contents",
            published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )

        # Then
        assert paper.title == "Test Title"
        assert paper.abstract == "Test Abstract"
        assert paper.url == "https://arxiv.org/abs/2401.00001"
        assert paper.contents == "Test Contents"
        assert paper.published_at == datetime(2024, 1, 15, tzinfo=timezone.utc)

    def test_paper_info_summary_is_not_init(self) -> None:
        """
        Given: PaperInfo is created.
        When: Accessing summary before setting it.
        Then: AttributeError is raised (field is not initialized).
        """
        # Given
        paper = PaperInfo(
            title="Test Title",
            abstract="Test Abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test Contents",
        )

        # When / Then
        with pytest.raises(AttributeError):
            _ = paper.summary

    def test_paper_info_summary_can_be_set(self) -> None:
        """
        Given: PaperInfo is created.
        When: Summary is set after creation.
        Then: Summary is accessible.
        """
        # Given
        paper = PaperInfo(
            title="Test Title",
            abstract="Test Abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test Contents",
        )

        # When
        paper.summary = "This is the summary"

        # Then
        assert paper.summary == "This is the summary"

    def test_paper_info_published_at_optional(self) -> None:
        """
        Given: PaperInfo is created without published_at.
        When: Accessing published_at.
        Then: None is returned.
        """
        # Given / When
        paper = PaperInfo(
            title="Test Title",
            abstract="Test Abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test Contents",
        )

        # Then
        assert paper.published_at is None
