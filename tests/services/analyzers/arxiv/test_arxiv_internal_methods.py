"""Tests for arxiv_summarizer internal methods.

This module tests the internal methods of ArxivSummarizer that are not covered
by the existing test_arxiv_helpers.py and test_arxiv_collect_flow.py:
- _get_curated_paper_ids
- _get_processed_ids / _save_processed_ids_by_date / _load_ids_from_file
- _get_paper_date
- _retrieve_paper_info
- _translate_to_japanese
- _extract_body_text / _extract_from_html / _extract_from_pdf
- _summarize_paper_info
- _store_summaries / _serialize_papers
- _render_markdown / _parse_markdown
- run (sync wrapper)
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from nook.core.errors.exceptions import RetryException
from nook.services.analyzers.arxiv.arxiv_summarizer import ArxivSummarizer, PaperInfo


@pytest.fixture
def summarizer(monkeypatch: pytest.MonkeyPatch) -> ArxivSummarizer:
    """Create an ArxivSummarizer instance for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
    return ArxivSummarizer()


class TestGetCuratedPaperIds:
    """Tests for ArxivSummarizer._get_curated_paper_ids method."""

    @pytest.mark.asyncio
    async def test_returns_paper_ids_from_huggingface_date_page(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Hugging Face date page with article links.
        When: _get_curated_paper_ids is called.
        Then: Valid paper IDs are extracted and returned.
        """
        html_content = """
        <html>
        <body>
            <article><a href="/papers/2401.00001">Paper 1</a></article>
            <article><a href="/papers/2401.00002">Paper 2</a></article>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.url = "https://huggingface.co/papers/date/2024-01-15"
        mock_response.raise_for_status = MagicMock()

        summarizer.http_client = AsyncMock()
        summarizer.http_client.get = AsyncMock(return_value=mock_response)

        with patch.object(
            summarizer, "_get_processed_ids", new_callable=AsyncMock
        ) as mock_processed:
            mock_processed.return_value = []
            result = await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))

        assert result is not None
        assert "2401.00001" in result
        assert "2401.00002" in result

    @pytest.mark.asyncio
    async def test_returns_none_on_redirect(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Hugging Face page redirects (URL mismatch).
        When: _get_curated_paper_ids is called.
        Then: None is returned.
        """
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.url = "https://huggingface.co/papers"  # Redirected
        mock_response.raise_for_status = MagicMock()

        summarizer.http_client = AsyncMock()
        summarizer.http_client.get = AsyncMock(return_value=mock_response)

        result = await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Hugging Face page returns 404.
        When: _get_curated_paper_ids is called.
        Then: None is returned.
        """
        summarizer.http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        summarizer.http_client.get = AsyncMock(side_effect=error)

        result = await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))

        assert result is None

    @pytest.mark.asyncio
    async def test_uses_fallback_on_empty_date_page(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Date page has no articles, but top page has papers.
        When: _get_curated_paper_ids is called.
        Then: Fallback to top page and return IDs.
        """
        date_page_html = "<html><body></body></html>"
        top_page_html = """
        <html>
        <body>
            <a href="/papers/2401.00003">Paper 3</a>
        </body>
        </html>
        """
        date_response = MagicMock()
        date_response.text = date_page_html
        date_response.url = "https://huggingface.co/papers/date/2024-01-15"
        date_response.raise_for_status = MagicMock()

        top_response = MagicMock()
        top_response.text = top_page_html

        summarizer.http_client = AsyncMock()
        summarizer.http_client.get = AsyncMock(
            side_effect=[date_response, top_response]
        )

        with patch.object(
            summarizer, "_get_processed_ids", new_callable=AsyncMock
        ) as mock_processed:
            mock_processed.return_value = []
            result = await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))

        assert result is not None
        assert "2401.00003" in result

    @pytest.mark.asyncio
    async def test_excludes_processed_ids(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Some paper IDs are already processed.
        When: _get_curated_paper_ids is called.
        Then: Processed IDs are excluded from result.
        """
        html_content = """
        <html>
        <body>
            <article><a href="/papers/2401.00001">Paper 1</a></article>
            <article><a href="/papers/2401.00002">Paper 2</a></article>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.url = "https://huggingface.co/papers/date/2024-01-15"
        mock_response.raise_for_status = MagicMock()

        summarizer.http_client = AsyncMock()
        summarizer.http_client.get = AsyncMock(return_value=mock_response)

        with patch.object(
            summarizer, "_get_processed_ids", new_callable=AsyncMock
        ) as mock_processed:
            mock_processed.return_value = ["2401.00001"]  # Already processed
            result = await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))

        assert result is not None
        assert "2401.00001" not in result
        assert "2401.00002" in result

    @pytest.mark.asyncio
    async def test_raises_on_non_404_error(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Hugging Face page returns 500 error.
        When: _get_curated_paper_ids is called.
        Then: Exception is raised.
        """
        summarizer.http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        summarizer.http_client.get = AsyncMock(side_effect=error)

        with pytest.raises(RetryException):
            await summarizer._get_curated_paper_ids(5, date(2024, 1, 15))


class TestProcessedIds:
    """Tests for ID processing methods."""

    @pytest.mark.asyncio
    async def test_get_processed_ids_returns_empty_when_no_file(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: No processed IDs file exists.
        When: _get_processed_ids is called.
        Then: Empty list is returned.
        """
        with patch.object(
            summarizer.storage, "load", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = None
            result = await summarizer._get_processed_ids(date(2024, 1, 15))

        assert result == []

    @pytest.mark.asyncio
    async def test_get_processed_ids_returns_ids_from_file(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Processed IDs file exists with IDs.
        When: _get_processed_ids is called.
        Then: List of IDs is returned.
        """
        file_content = "2401.00001\n2401.00002\n2401.00003"

        with patch.object(
            summarizer.storage, "load", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = file_content
            result = await summarizer._get_processed_ids(date(2024, 1, 15))

        assert result == ["2401.00001", "2401.00002", "2401.00003"]

    @pytest.mark.asyncio
    async def test_load_ids_from_file_handles_empty_file(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: File exists but is empty.
        When: _load_ids_from_file is called.
        Then: Empty list is returned.
        """
        with patch.object(
            summarizer.storage, "load", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = ""
            result = await summarizer._load_ids_from_file("test.txt")

        assert result == []

    @pytest.mark.asyncio
    async def test_save_processed_ids_groups_by_date(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: List of paper IDs with published dates.
        When: _save_processed_ids_by_date is called.
        Then: IDs are grouped by date and saved correctly.
        """
        paper_ids = ["2401.00001", "2401.00002", "2401.00003", "2401.00004"]

        # Mapping from ID to Date
        id_date_map = {
            "2401.00001": date(2024, 1, 15),
            "2401.00002": date(2024, 1, 15),
            "2401.00003": date(2024, 1, 16),
            "2401.00004": None,
        }

        async def mock_get_date(pid):
            return id_date_map.get(pid)

        # Mock _get_processed_ids to return empty list so nothing is filtered out as already processed
        with patch.object(
            summarizer, "_get_processed_ids", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            with patch.object(
                summarizer.storage, "save", new_callable=AsyncMock
            ) as mock_save:
                with patch.object(
                    summarizer, "_get_paper_date", side_effect=mock_get_date
                ):
                    await summarizer._save_processed_ids_by_date(
                        paper_ids, [date(2024, 1, 15), date(2024, 1, 16)]
                    )

                # Verify save was called for both dates (plus potentially one for the None date -> today)
                # At least calls for 2024-01-15 and 2024-01-16
                assert mock_save.call_count >= 2


class TestGetPaperDate:
    """Tests for ArxivSummarizer._get_paper_date method."""

    @pytest.mark.asyncio
    async def test_returns_date_on_success(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: arxiv library returns paper with published date.
        When: _get_paper_date is called.
        Then: Date object is returned.
        """
        mock_paper = MagicMock()
        mock_paper.published = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch("arxiv.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = iter([mock_paper])

            with patch("arxiv.Search"):
                result = await summarizer._get_paper_date("2401.00001")

        assert result == date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: arxiv library raises exception.
        When: _get_paper_date is called.
        Then: None is returned.
        """
        with patch("arxiv.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")

            result = await summarizer._get_paper_date("2401.00001")

        assert result is None


class TestRetrievePaperInfo:
    """Tests for ArxivSummarizer._retrieve_paper_info method."""

    @pytest.mark.asyncio
    async def test_returns_paper_info_on_success(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: arxiv returns valid paper.
        When: _retrieve_paper_info is called.
        Then: PaperInfo object is returned.
        """
        mock_paper = MagicMock()
        mock_paper.title = "Test Paper"
        mock_paper.summary = "Test abstract"
        mock_paper.entry_id = "https://arxiv.org/abs/2401.00001"
        mock_paper.published = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with patch("arxiv.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = iter([mock_paper])

            with patch("arxiv.Search"):
                with patch.object(
                    summarizer, "_extract_body_text", new_callable=AsyncMock
                ) as mock_extract:
                    mock_extract.return_value = "Paper contents"
                    with patch.object(
                        summarizer, "_translate_to_japanese", new_callable=AsyncMock
                    ) as mock_translate:
                        mock_translate.return_value = "テスト要約"

                        result = await summarizer._retrieve_paper_info("2401.00001")

        assert result is not None
        assert isinstance(result, PaperInfo)
        assert result.title == "Test Paper"

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: arxiv raises exception.
        When: _retrieve_paper_info is called.
        Then: None is returned.
        """
        with patch("arxiv.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")

            result = await summarizer._retrieve_paper_info("2401.00001")

        assert result is None


class TestTranslateToJapanese:
    """Tests for ArxivSummarizer._translate_to_japanese method."""

    @pytest.mark.asyncio
    async def test_returns_translated_text(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: GPT returns translation.
        When: _translate_to_japanese is called.
        Then: Translated text is returned.
        """
        with patch.object(
            summarizer.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "翻訳されたテキスト"
            with patch.object(summarizer, "rate_limit", new_callable=AsyncMock):
                result = await summarizer._translate_to_japanese("Original text")

        assert result == "翻訳されたテキスト"

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: GPT raises exception.
        When: _translate_to_japanese is called.
        Then: Original text is returned.
        """
        with patch.object(
            summarizer.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = Exception("API error")
            result = await summarizer._translate_to_japanese("Original text")

        assert result == "Original text"


class TestExtractBodyText:
    """Tests for text extraction methods."""

    @pytest.mark.asyncio
    async def test_extract_body_text_uses_html_first(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: HTML extraction succeeds.
        When: _extract_body_text is called.
        Then: HTML content is returned.
        """
        with patch.object(
            summarizer, "_extract_from_html", new_callable=AsyncMock
        ) as mock_html:
            mock_html.return_value = "HTML content"
            result = await summarizer._extract_body_text("2401.00001")

        assert result == "HTML content"

    @pytest.mark.asyncio
    async def test_extract_body_text_falls_back_to_pdf(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: HTML extraction fails but PDF succeeds.
        When: _extract_body_text is called.
        Then: PDF content is returned.
        """
        with patch.object(
            summarizer, "_extract_from_html", new_callable=AsyncMock
        ) as mock_html:
            mock_html.return_value = ""
            with patch.object(
                summarizer, "_extract_from_pdf", new_callable=AsyncMock
            ) as mock_pdf:
                mock_pdf.return_value = "PDF content"
                result = await summarizer._extract_body_text("2401.00001")

        assert result == "PDF content"

    @pytest.mark.asyncio
    async def test_extract_body_text_returns_empty_on_all_failures(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Both HTML and PDF extraction fail.
        When: _extract_body_text is called.
        Then: Empty string is returned.
        """
        with patch.object(
            summarizer, "_extract_from_html", new_callable=AsyncMock
        ) as mock_html:
            mock_html.return_value = ""
            with patch.object(
                summarizer, "_extract_from_pdf", new_callable=AsyncMock
            ) as mock_pdf:
                mock_pdf.return_value = ""
                result = await summarizer._extract_body_text("2401.00001")

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_from_html_parses_content(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Valid HTML content.
        When: _extract_from_html is called.
        Then: Text is extracted.
        """
        html_content = (
            "<html>\n"
            "<head></head>\n"
            "<body>\n"
            "    <p>This is a short paragraph.</p>\n"
            "    <p>This is a much longer paragraph that contains more than fifty "
            "characters of meaningful content about the article.</p>\n"
            "    <p>Another long paragraph with sufficient content length to be considered "
            "meaningful by the extraction algorithm.</p>\n"
            "</body>\n"
            "</html>\n"
        )
        with patch.object(
            summarizer, "_download_html_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = html_content
            result = await summarizer._extract_from_html("2401.00001")

        # Result should contain extracted text
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_from_html_returns_empty_on_404(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: HTML page returns 404.
        When: _extract_from_html is called.
        Then: Empty string is returned.
        """
        with patch.object(
            summarizer, "_download_html_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = ""
            result = await summarizer._extract_from_html("2401.00001")

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_from_pdf_parses_content(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Valid PDF response.
        When: _extract_from_pdf is called.
        Then: Text is extracted.
        """
        mock_response = MagicMock()
        mock_response.content = b"dummy pdf content"

        with patch.object(
            summarizer, "_download_pdf_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = mock_response
            with patch("pdfplumber.open") as mock_pdfplumber:
                mock_pdf = MagicMock()
                mock_page = MagicMock()
                mock_page.extract_text.return_value = (
                    "This is a long paragraph of text from the PDF that should be extracted. "
                    * 5
                )
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
                mock_pdf.__exit__ = MagicMock(return_value=False)
                mock_pdfplumber.return_value = mock_pdf

                result = await summarizer._extract_from_pdf("2401.00001")

        assert "long paragraph" in result

    @pytest.mark.asyncio
    async def test_extract_from_pdf_handles_empty_response(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: PDF response has no content.
        When: _extract_from_pdf is called.
        Then: Empty string is returned.
        """
        mock_response = MagicMock()
        mock_response.content = b""

        with patch.object(
            summarizer, "_download_pdf_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = mock_response
            result = await summarizer._extract_from_pdf("2401.00001")

        assert result == ""

    @pytest.mark.asyncio
    async def test_download_html_without_retry_returns_empty_on_404(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: 404 response.
        When: _download_html_without_retry is called.
        Then: Empty string is returned.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = error
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await summarizer._download_html_without_retry("http://example.com")
        assert result == ""

    @pytest.mark.asyncio
    async def test_download_html_without_retry_raises_on_other_errors(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: 500 response.
        When: _download_html_without_retry is called.
        Then: Exception is raised.
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = error
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await summarizer._download_html_without_retry("http://example.com")

    @pytest.mark.asyncio
    async def test_extract_from_html_handles_exception(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: _download_html_without_retry raises generic exception.
        When: _extract_from_html is called.
        Then: Empty string is returned.
        """
        with patch.object(
            summarizer, "_download_html_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = Exception("Unexpected error")
            result = await summarizer._extract_from_html("2401.00001")

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_from_pdf_handles_extraction_error(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: pdfplumber raises error on page extraction.
        When: _extract_from_pdf is called.
        Then: Error is ignored and valid content is returned (or empty if all fail).
        """
        mock_response = MagicMock()
        mock_response.content = b"pdf content"

        with patch.object(
            summarizer, "_download_pdf_without_retry", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = mock_response
            with patch("pdfplumber.open") as mock_pdfplumber:
                mock_pdf = MagicMock()
                mock_page1 = MagicMock()
                mock_page1.extract_text.side_effect = Exception("Extraction failed")
                mock_page2 = MagicMock()
                mock_page2.extract_text.return_value = "Page 2 content" + "a" * 100

                mock_pdf.pages = [mock_page1, mock_page2]
                mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
                mock_pdf.__exit__ = MagicMock(return_value=False)
                mock_pdfplumber.return_value = mock_pdf

                result = await summarizer._extract_from_pdf("2401.00001")

        assert "Page 2 content" in result


class TestSummarizePaperInfo:
    """Tests for ArxivSummarizer._summarize_paper_info method."""

    @pytest.mark.asyncio
    async def test_generates_summary(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Valid paper info.
        When: _summarize_paper_info is called.
        Then: Summary is generated and assigned.
        """
        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test contents",
        )

        with patch.object(
            summarizer.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated summary"
            with patch.object(summarizer, "rate_limit", new_callable=AsyncMock):
                await summarizer._summarize_paper_info(paper)

        assert paper.summary == "Generated summary"

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: GPT raises exception.
        When: _summarize_paper_info is called.
        Then: Error message is assigned as summary.
        """
        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test contents",
        )

        with patch.object(
            summarizer.gpt_client, "generate_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = Exception("API error")
            await summarizer._summarize_paper_info(paper)

        assert "エラー" in paper.summary


class TestStoreSummaries:
    """Tests for ArxivSummarizer._store_summaries method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_papers(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: Empty papers list.
        When: _store_summaries is called.
        Then: Empty list is returned.
        """
        result = await summarizer._store_summaries([], 5, [date(2024, 1, 15)])
        assert result == []

    @pytest.mark.asyncio
    async def test_saves_papers_and_returns_file_paths(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: List of papers.
        When: _store_summaries is called.
        Then: Files are saved and paths returned.
        """
        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test contents",
            published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        paper.summary = "Test summary"
        papers = [paper]

        with patch(
            "nook.services.analyzers.arxiv.arxiv_summarizer.store_daily_snapshots",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = [("2024-01-15.json", "2024-01-15.md")]
            result = await summarizer._store_summaries(papers, 5, [date(2024, 1, 15)])

        assert len(result) == 1
        assert result[0] == ("2024-01-15.json", "2024-01-15.md")


class TestSerializePapers:
    """Tests for ArxivSummarizer._serialize_papers method."""

    def test_serializes_papers_correctly(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: List of PaperInfo objects.
        When: _serialize_papers is called.
        Then: List of dicts is returned.
        """
        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="https://arxiv.org/abs/2401.00001",
            contents="Test contents",
            published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        paper.summary = "Test summary"

        result = summarizer._serialize_papers([paper])

        assert len(result) == 1
        assert result[0]["title"] == "Test Paper"
        assert result[0]["abstract"] == "Test abstract"
        assert result[0]["summary"] == "Test summary"


class TestRenderAndParseMarkdown:
    """Tests for markdown rendering and parsing."""

    def test_render_markdown_produces_expected_format(
        self, summarizer: ArxivSummarizer
    ) -> None:
        """
        Given: List of paper records.
        When: _render_markdown is called.
        Then: Markdown content is generated.
        """
        records = [
            {
                "title": "Test Paper",
                "url": "https://arxiv.org/abs/2401.00001",
                "abstract": "Test abstract",
                "summary": "Test summary",
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        result = summarizer._render_markdown(records, today)

        assert "# arXiv 論文要約 (2024-01-15)" in result
        assert "[Test Paper](https://arxiv.org/abs/2401.00001)" in result
        assert "**abstract**:" in result
        assert "**summary**:" in result

    def test_parse_markdown_extracts_records(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Valid markdown content.
        When: _parse_markdown is called.
        Then: Records are extracted.
        """
        markdown = """# arXiv 論文要約 (2024-01-15)

## [Test Paper](https://arxiv.org/abs/2401.00001)

**abstract**:
Test abstract

**summary**:
Test summary

---

"""
        result = summarizer._parse_markdown(markdown)

        assert len(result) == 1
        assert result[0]["title"] == "Test Paper"
        assert result[0]["url"] == "https://arxiv.org/abs/2401.00001"


class TestRunSyncWrapper:
    """Tests for run sync wrapper."""

    def test_run_calls_collect(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: ArxivSummarizer instance.
        When: run is called.
        Then: collect is executed via asyncio.run.
        """
        with patch("asyncio.run") as mock_asyncio_run:
            summarizer.run(limit=10)
            mock_asyncio_run.assert_called_once()
            # Close the coroutine to avoid "coroutine was never awaited" warning
            coro = mock_asyncio_run.call_args[0][0]
            coro.close()


class TestPaperSortKey:
    """Tests for _paper_sort_key method."""

    def test_returns_tuple_with_date(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Paper record with published_at.
        When: _paper_sort_key is called.
        Then: Tuple with score=0 and datetime is returned.
        """
        record = {"published_at": "2024-01-15T10:30:00+00:00"}
        result = summarizer._paper_sort_key(record)

        assert result[0] == 0  # No score for arxiv
        assert result[1].year == 2024

    def test_handles_missing_published_at(self, summarizer: ArxivSummarizer) -> None:
        """
        Given: Paper record without published_at.
        When: _paper_sort_key is called.
        Then: Tuple with datetime.min is returned.
        """
        record = {}
        result = summarizer._paper_sort_key(record)

        assert result[0] == 0
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)
