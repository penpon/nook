"""
nook/services/arxiv_summarizer/arxiv_summarizer.py のテスト

テスト観点:
- ArxivSummarizerの初期化
- 論文検索と取得
- 論文情報抽出
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: ArxivSummarizerを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        assert service.service_name == "arxiv_summarizer"


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_papers(mock_env_vars, mock_arxiv_api):
    """
    Given: 有効なarXiv API
    When: collectメソッドを呼び出す
    Then: 論文が正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ):

            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_categories(mock_env_vars):
    """
    Given: 複数のカテゴリ
    When: collectメソッドを呼び出す
    Then: 全てのカテゴリが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(return_value=Mock(text="<feed></feed>"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(mock_env_vars):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(side_effect=Exception("Network error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_xml(mock_env_vars):
    """
    Given: 不正なXML
    When: collectメソッドを呼び出す
    Then: エラーがログされ、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(return_value=Mock(text="Invalid XML"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<feed><entry></entry></feed>")
            )
            service.gpt_client.get_response = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ):

            service.http_client.get = AsyncMock(return_value=Mock(text="<feed></feed>"))
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)

            await service.cleanup()


# =============================================================================
# 5. _get_curated_paper_ids メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_success(mock_env_vars, respx_mock):
    """
    Given: 有効なHugging Faceページ
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: 論文IDが正常に取得される
    """
    # Given: Hugging Faceページのモック
    mock_html = """
    <html>
        <article>
            <a href="/papers/2301.00001">Test Paper 1</a>
        </article>
        <article>
            <a href="/papers/2301.00002">Test Paper 2</a>
        </article>
    </html>
    """
    respx_mock.get("https://huggingface.co/papers/date/2024-01-01").mock(
        return_value=httpx.Response(200, text=mock_html)
    )
    respx_mock.get("https://huggingface.co/papers").mock(
        return_value=httpx.Response(200, text=mock_html)
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text=mock_html, url="https://huggingface.co/papers/date/2024-01-01"
                )
            )

            # When
            result = await service._get_curated_paper_ids(
                limit=5, snapshot_date=date(2024, 1, 1)
            )

            # Then
            assert result is not None
            assert isinstance(result, list)
            assert len(result) <= 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_404_error(mock_env_vars, respx_mock):
    """
    Given: Hugging FaceページがHTTP 404エラーを返す
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: HTTP 404エラー
    respx_mock.get("https://huggingface.co/papers/date/2024-01-01").mock(
        return_value=httpx.Response(404)
    )

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            response_mock = AsyncMock()
            response_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=Mock(status_code=404)
            )
            service.http_client.get = AsyncMock(return_value=response_mock)

            # When
            result = await service._get_curated_paper_ids(
                limit=5, snapshot_date=date(2024, 1, 1)
            )

            # Then
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_redirect(mock_env_vars):
    """
    Given: Hugging Faceページがリダイレクトする
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            # リダイレクト後のURLが異なる
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text="<html></html>",
                    url="https://huggingface.co/papers",  # 異なるURL
                )
            )

            # When
            result = await service._get_curated_paper_ids(
                limit=5, snapshot_date=date(2024, 1, 1)
            )

            # Then
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_fallback_to_top_page(mock_env_vars):
    """
    Given: 日付ページが空でトップページにフォールバック
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: トップページから論文IDが取得される
    """
    # Given: 空の日付ページとトップページのモック
    mock_html_empty = "<html><body></body></html>"
    mock_html_top = """
    <html>
        <article>
            <a href="/papers/2301.00003">Test Paper 3</a>
        </article>
    </html>
    """

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            # 1回目: 空の日付ページ、2回目: トップページ
            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(
                        text=mock_html_empty,
                        url="https://huggingface.co/papers/date/2024-01-01",
                    ),
                    Mock(text=mock_html_top, url="https://huggingface.co/papers"),
                ]
            )

            # When
            result = await service._get_curated_paper_ids(
                limit=5, snapshot_date=date(2024, 1, 1)
            )

            # Then
            assert result is not None
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_empty_result(mock_env_vars):
    """
    Given: 全ページが空
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: 空リストが返される
    """
    # Given: 空のHTML
    mock_html_empty = "<html><body></body></html>"

    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text=mock_html_empty,
                    url="https://huggingface.co/papers/date/2024-01-01",
                )
            )

            # When
            result = await service._get_curated_paper_ids(
                limit=5, snapshot_date=date(2024, 1, 1)
            )

            # Then
            assert isinstance(result, list)
            assert len(result) == 0


# =============================================================================
# 6. _download_pdf_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_success(mock_env_vars):
    """
    Given: 有効なPDF URL
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: PDFが正常にダウンロードされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.content = b"%PDF-1.4 test content"
            mock_response.raise_for_status = Mock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            # When
            result = await service._download_pdf_without_retry(
                "https://arxiv.org/pdf/2301.00001"
            )

            # Then
            assert result.content == b"%PDF-1.4 test content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_timeout(mock_env_vars):
    """
    Given: PDFダウンロードがタイムアウト
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: TimeoutException が発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            # When/Then
            with pytest.raises(httpx.TimeoutException):
                await service._download_pdf_without_retry(
                    "https://arxiv.org/pdf/2301.00001"
                )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_404_error(mock_env_vars):
    """
    Given: PDF URLが404エラーを返す
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: HTTPStatusError が発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            # When/Then
            with pytest.raises(httpx.HTTPStatusError):
                await service._download_pdf_without_retry(
                    "https://arxiv.org/pdf/2301.00001"
                )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_500_error(mock_env_vars):
    """
    Given: PDF URLが500エラーを返す
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: HTTPStatusError が発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Internal Server Error", request=Mock(), response=mock_response
            )

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            # When/Then
            with pytest.raises(httpx.HTTPStatusError):
                await service._download_pdf_without_retry(
                    "https://arxiv.org/pdf/2301.00001"
                )


# =============================================================================
# 7. _extract_from_pdf メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_success(mock_env_vars):
    """
    Given: 有効なPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: テキストが正常に抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックPDF
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "This is a test paper content. " * 10
        )  # 十分な長さ

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None

        # モックHTTPレスポンス
        mock_response = Mock()
        mock_response.content = b"%PDF-1.4"

        with patch.object(
            service,
            "_download_pdf_without_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ), patch("pdfplumber.open", return_value=mock_pdf):

            # When
            result = await service._extract_from_pdf("2301.00001")

            # Then
            assert isinstance(result, str)
            assert len(result) > 0
            assert "test paper content" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_empty_content(mock_env_vars):
    """
    Given: 空のPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPレスポンス（空）
        mock_response = Mock()
        mock_response.content = b""

        with patch.object(
            service,
            "_download_pdf_without_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):

            # When
            result = await service._extract_from_pdf("2301.00001")

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_corrupted(mock_env_vars):
    """
    Given: 破損したPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPレスポンス
        mock_response = Mock()
        mock_response.content = b"corrupted data"

        with patch.object(
            service,
            "_download_pdf_without_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ), patch("pdfplumber.open", side_effect=Exception("Corrupted PDF")):

            # When
            result = await service._extract_from_pdf("2301.00001")

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_download_error(mock_env_vars):
    """
    Given: PDFダウンロードがエラー
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        with patch.object(
            service,
            "_download_pdf_without_retry",
            new_callable=AsyncMock,
            side_effect=Exception("Download error"),
        ):

            # When
            result = await service._extract_from_pdf("2301.00001")

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_filters_short_lines(mock_env_vars):
    """
    Given: 短い行を含むPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 短い行がフィルタリングされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックPDF（短い行と長い行が混在）
        mock_page = Mock()
        mock_page.extract_text.return_value = """Short
1
arXiv:2301.00001
This is a long enough line that should be kept in the extracted text because it meets the minimum length requirement.
References
Another long enough line that should be kept because it is sufficiently long.
12345"""

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None

        # モックHTTPレスポンス
        mock_response = Mock()
        mock_response.content = b"%PDF-1.4"

        with patch.object(
            service,
            "_download_pdf_without_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ), patch("pdfplumber.open", return_value=mock_pdf):

            # When
            result = await service._extract_from_pdf("2301.00001")

            # Then
            assert isinstance(result, str)
            # 短い行（Short, 1, arXiv:, 12345）が除外されていることを確認
            assert "Short" not in result
            assert "arXiv:" not in result
            # 長い行は含まれている
            assert "long enough line" in result


# =============================================================================
# 8. _translate_to_japanese メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_success(mock_env_vars):
    """
    Given: 有効な英語テキスト
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 日本語に翻訳される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックGPTクライアント
        service.gpt_client.generate_async = AsyncMock(
            return_value="これはテスト翻訳です。"
        )

        with patch.object(service, "rate_limit", new_callable=AsyncMock):

            # When
            result = await service._translate_to_japanese("This is a test.")

            # Then
            assert result == "これはテスト翻訳です。"
            service.gpt_client.generate_async.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_gpt_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 原文が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックGPTクライアント（エラー）
        service.gpt_client.generate_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        # When
        result = await service._translate_to_japanese("This is a test.")

        # Then
        assert result == "This is a test."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_empty_text(mock_env_vars):
    """
    Given: 空のテキスト
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックGPTクライアント
        service.gpt_client.generate_async = AsyncMock(return_value="")

        with patch.object(service, "rate_limit", new_callable=AsyncMock):

            # When
            result = await service._translate_to_japanese("")

            # Then
            assert result == ""


# =============================================================================
# 9. ユーティリティ関数のテスト
# =============================================================================


@pytest.mark.unit
def test_remove_tex_backticks_with_tex_format():
    """
    Given: TeX形式の文字列（`$...$`）
    When: remove_tex_backticksを呼び出す
    Then: バッククォートが除去される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import remove_tex_backticks

    # When
    result = remove_tex_backticks("`$\\ldots$`")

    # Then
    assert result == "$\\ldots$"


@pytest.mark.unit
def test_remove_tex_backticks_without_tex_format():
    """
    Given: TeX形式でない文字列
    When: remove_tex_backticksを呼び出す
    Then: 文字列が変更されない
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import remove_tex_backticks

    # When
    result = remove_tex_backticks("normal text")

    # Then
    assert result == "normal text"


@pytest.mark.unit
def test_remove_tex_backticks_partial_match():
    """
    Given: 部分的にマッチする文字列
    When: remove_tex_backticksを呼び出す
    Then: 文字列が変更されない
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import remove_tex_backticks

    # When
    result = remove_tex_backticks("`incomplete")

    # Then
    assert result == "`incomplete"


@pytest.mark.unit
def test_remove_outer_markdown_markers_with_markers():
    """
    Given: Markdownマーカーで囲まれた文字列
    When: remove_outer_markdown_markersを呼び出す
    Then: 外側のマーカーが除去される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_markdown_markers,
    )

    # When
    result = remove_outer_markdown_markers("```\ncode\n```")

    # Then
    assert result == "\ncode\n"


@pytest.mark.unit
def test_remove_outer_markdown_markers_without_markers():
    """
    Given: Markdownマーカーがない文字列
    When: remove_outer_markdown_markersを呼び出す
    Then: 文字列が変更されない
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_markdown_markers,
    )

    # When
    result = remove_outer_markdown_markers("normal text")

    # Then
    assert result == "normal text"


@pytest.mark.unit
def test_remove_outer_singlequotes_with_quotes():
    """
    Given: シングルクォートで囲まれた文字列
    When: remove_outer_singlequotesを呼び出す
    Then: 外側のクォートが除去される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_singlequotes,
    )

    # When
    result = remove_outer_singlequotes("'quoted text'")

    # Then
    assert result == "quoted text"


@pytest.mark.unit
def test_remove_outer_singlequotes_without_quotes():
    """
    Given: シングルクォートがない文字列
    When: remove_outer_singlequotesを呼び出す
    Then: 文字列が変更されない
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_singlequotes,
    )

    # When
    result = remove_outer_singlequotes("normal text")

    # Then
    assert result == "normal text"


# =============================================================================
# 10. _retrieve_paper_info メソッドのテスト（arxiv.Search モック）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_success(mock_env_vars):
    """
    Given: 有効な論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: 論文情報が正常に取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        # モックarxiv結果
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2301.00001v1"
        mock_paper.title = "Test Paper Title"
        mock_paper.summary = "Test abstract"
        mock_paper.published = datetime(2023, 1, 1, tzinfo=timezone.utc)

        # arxiv.Clientをモック
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_results = [mock_paper]
            mock_client.results.return_value = mock_results
            mock_client_class.return_value = mock_client

            # 翻訳と本文抽出をモック
            with patch.object(
                service, "_translate_to_japanese", new_callable=AsyncMock, return_value="テスト要約"
            ), patch.object(
                service, "_extract_body_text", new_callable=AsyncMock, return_value="Test content"
            ):

                # When
                result = await service._retrieve_paper_info("2301.00001")

                # Then
                assert result is not None
                assert isinstance(result, PaperInfo)
                assert result.title == "Test Paper Title"
                assert result.abstract == "テスト要約"
                assert result.url == "http://arxiv.org/abs/2301.00001v1"
                assert result.contents == "Test content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_no_results(mock_env_vars):
    """
    Given: 存在しない論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # arxiv.Clientをモック（結果なし）
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.return_value = []
            mock_client_class.return_value = mock_client

            # When
            result = await service._retrieve_paper_info("9999.99999")

            # Then
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_api_error(mock_env_vars):
    """
    Given: arxiv APIがエラーを返す
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # arxiv.Clientをモック（エラー）
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            # When
            result = await service._retrieve_paper_info("2301.00001")

            # Then
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_with_fallback_to_abstract(mock_env_vars):
    """
    Given: 本文抽出が失敗
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: アブストラクトが本文として使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        # モックarxiv結果
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2301.00001v1"
        mock_paper.title = "Test Paper Title"
        mock_paper.summary = "Test abstract content"
        mock_paper.published = datetime(2023, 1, 1, tzinfo=timezone.utc)

        # arxiv.Clientをモック
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.return_value = [mock_paper]
            mock_client_class.return_value = mock_client

            # 翻訳をモック、本文抽出は空文字列を返す
            with patch.object(
                service, "_translate_to_japanese", new_callable=AsyncMock, return_value="テスト要約"
            ), patch.object(
                service, "_extract_body_text", new_callable=AsyncMock, return_value=""
            ):

                # When
                result = await service._retrieve_paper_info("2301.00001")

                # Then
                assert result is not None
                assert isinstance(result, PaperInfo)
                assert result.contents == "Test abstract content"


# =============================================================================
# 11. _get_paper_date メソッドのテスト（arxiv.Search モック）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_success(mock_env_vars):
    """
    Given: 有効な論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: 公開日が正常に取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックarxiv結果
        mock_paper = Mock()
        mock_paper.published = datetime(2023, 1, 15, 10, 30, 0)

        # arxiv.Clientをモック
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.return_value = [mock_paper]
            mock_client_class.return_value = mock_client

            # When
            result = await service._get_paper_date("2301.00001")

            # Then
            assert result is not None
            assert result == date(2023, 1, 15)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_no_results(mock_env_vars):
    """
    Given: 存在しない論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # arxiv.Clientをモック（結果なし）
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.return_value = []
            mock_client_class.return_value = mock_client

            # When
            result = await service._get_paper_date("9999.99999")

            # Then
            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_api_error(mock_env_vars):
    """
    Given: arxiv APIがエラーを返す
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # arxiv.Clientをモック（エラー）
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.results.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            # When
            result = await service._get_paper_date("2301.00001")

            # Then
            assert result is None


# =============================================================================
# 12. _extract_from_html メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_success(mock_env_vars):
    """
    Given: 有効なHTML
    When: _extract_from_htmlメソッドを呼び出す
    Then: テキストが正常に抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTML
        mock_html = """
        <html>
        <body>
            <header>Header content</header>
            <nav>Navigation</nav>
            <p>This is a long enough paragraph that should be extracted from the HTML content because it meets the minimum length requirement for body text.</p>
            <p>Another valid paragraph with sufficient length to be considered as body content in the extraction process.</p>
            <footer>Footer content</footer>
        </body>
        </html>
        """

        with patch.object(
            service,
            "_download_html_without_retry",
            new_callable=AsyncMock,
            return_value=mock_html,
        ):

            # When
            result = await service._extract_from_html("2301.00001")

            # Then
            assert isinstance(result, str)
            assert len(result) > 0
            # ヘッダーやフッターは除外される
            assert "Header content" not in result
            assert "Navigation" not in result
            assert "Footer content" not in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_404_error(mock_env_vars):
    """
    Given: HTML URLが404エラーを返す
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # 404エラーをモック
        with patch.object(
            service, "_download_html_without_retry", new_callable=AsyncMock, return_value=""
        ):

            # When
            result = await service._extract_from_html("2301.00001")

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_empty_body(mock_env_vars):
    """
    Given: 空のHTML
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # 空のHTML
        mock_html = "<html><body></body></html>"

        with patch.object(
            service,
            "_download_html_without_retry",
            new_callable=AsyncMock,
            return_value=mock_html,
        ):

            # When
            result = await service._extract_from_html("2301.00001")

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_download_error(mock_env_vars):
    """
    Given: HTMLダウンロードがエラー
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        with patch.object(
            service,
            "_download_html_without_retry",
            new_callable=AsyncMock,
            side_effect=Exception("Download error"),
        ):

            # When
            result = await service._extract_from_html("2301.00001")

            # Then
            assert result == ""


# =============================================================================
# 13. _download_html_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_success(mock_env_vars):
    """
    Given: 有効なHTML URL
    When: _download_html_without_retryメソッドを呼び出す
    Then: HTMLが正常にダウンロードされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.text = "<html><body>Test HTML content</body></html>"
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # When
            result = await service._download_html_without_retry(
                "https://arxiv.org/html/2301.00001"
            )

            # Then
            assert result == "<html><body>Test HTML content</body></html>"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_404_returns_empty_string(mock_env_vars):
    """
    Given: HTML URLが404エラーを返す
    When: _download_html_without_retryメソッドを呼び出す
    Then: 空文字列が返される（例外は発生しない）
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # When
            result = await service._download_html_without_retry(
                "https://arxiv.org/html/2301.00001"
            )

            # Then
            assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_timeout(mock_env_vars):
    """
    Given: HTMLダウンロードがタイムアウト
    When: _download_html_without_retryメソッドを呼び出す
    Then: 例外が再発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # モックHTTPクライアント
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # When/Then
            with pytest.raises(httpx.TimeoutException):
                await service._download_html_without_retry(
                    "https://arxiv.org/html/2301.00001"
                )


# =============================================================================
# 14. _extract_body_text メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_from_html(mock_env_vars):
    """
    Given: HTMLが利用可能
    When: _extract_body_textメソッドを呼び出す
    Then: HTMLからテキストが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # HTMLからの抽出が成功
        with patch.object(
            service,
            "_extract_from_html",
            new_callable=AsyncMock,
            return_value="HTML extracted text",
        ):

            # When
            result = await service._extract_body_text("2301.00001")

            # Then
            assert result == "HTML extracted text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_fallback_to_pdf(mock_env_vars):
    """
    Given: HTML抽出が失敗し、PDF抽出が成功
    When: _extract_body_textメソッドを呼び出す
    Then: PDFからテキストが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # HTML抽出は空、PDF抽出は成功
        with patch.object(
            service, "_extract_from_html", new_callable=AsyncMock, return_value=""
        ), patch.object(
            service,
            "_extract_from_pdf",
            new_callable=AsyncMock,
            return_value="PDF extracted text",
        ):

            # When
            result = await service._extract_body_text("2301.00001")

            # Then
            assert result == "PDF extracted text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_both_fail(mock_env_vars):
    """
    Given: HTMLとPDFの両方の抽出が失敗
    When: _extract_body_textメソッドを呼び出す
    Then: 空文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # HTML、PDF両方とも空
        with patch.object(
            service, "_extract_from_html", new_callable=AsyncMock, return_value=""
        ), patch.object(
            service, "_extract_from_pdf", new_callable=AsyncMock, return_value=""
        ):

            # When
            result = await service._extract_body_text("2301.00001")

            # Then
            assert result == ""


# =============================================================================
# 15. _is_valid_body_line メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_is_valid_body_line_valid(mock_env_vars):
    """
    Given: 有効な本文行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: Trueが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # 十分な長さで、ピリオドを含む
        line = "This is a valid body line with sufficient length and proper sentence structure."

        # When
        result = service._is_valid_body_line(line, min_length=80)

        # Then
        assert result is True


@pytest.mark.unit
def test_is_valid_body_line_too_short(mock_env_vars):
    """
    Given: 短すぎる行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # 短い行
        line = "Short line."

        # When
        result = service._is_valid_body_line(line, min_length=80)

        # Then
        assert result is False


@pytest.mark.unit
def test_is_valid_body_line_with_email(mock_env_vars):
    """
    Given: メールアドレスを含む行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # メールアドレスを含む
        line = "Contact us at test@example.com for more information about this research paper."

        # When
        result = service._is_valid_body_line(line, min_length=80)

        # Then
        assert result is False


@pytest.mark.unit
def test_is_valid_body_line_with_university(mock_env_vars):
    """
    Given: 'university'を含む行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # 'university'を含む
        line = "Department of Computer Science, Stanford University, California, USA contact information."

        # When
        result = service._is_valid_body_line(line, min_length=80)

        # Then
        assert result is False


@pytest.mark.unit
def test_is_valid_body_line_no_period(mock_env_vars):
    """
    Given: ピリオドを含まない行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # ピリオドなし
        line = "This is a line without proper punctuation but with sufficient length to pass"

        # When
        result = service._is_valid_body_line(line, min_length=80)

        # Then
        assert result is False


# =============================================================================
# 16. _summarize_paper_info メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_success(mock_env_vars):
    """
    Given: 有効な論文情報
    When: _summarize_paper_infoメソッドを呼び出す
    Then: 要約が正常に生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="http://arxiv.org/abs/2301.00001",
            contents="Test contents",
        )

        # GPTクライアントをモック
        service.gpt_client.generate_async = AsyncMock(return_value="```markdown\nTest summary\n```")

        with patch.object(service, "rate_limit", new_callable=AsyncMock):

            # When
            await service._summarize_paper_info(paper)

            # Then
            assert paper.summary == "\nTest summary\n"
            service.gpt_client.generate_async.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_gpt_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_paper_infoメソッドを呼び出す
    Then: エラーメッセージが要約として設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="http://arxiv.org/abs/2301.00001",
            contents="Test contents",
        )

        # GPTクライアントをモック（エラー）
        service.gpt_client.generate_async = AsyncMock(side_effect=Exception("API Error"))

        # When
        await service._summarize_paper_info(paper)

        # Then
        assert "要約の生成中にエラーが発生しました" in paper.summary
        assert "API Error" in paper.summary


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_removes_tex_backticks(mock_env_vars):
    """
    Given: TeX形式のバッククォートを含む要約
    When: _summarize_paper_infoメソッドを呼び出す
    Then: バッククォートが除去される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        paper = PaperInfo(
            title="Test Paper",
            abstract="Test abstract",
            url="http://arxiv.org/abs/2301.00001",
            contents="Test contents",
        )

        # GPTクライアントをモック（TeX形式含む）
        service.gpt_client.generate_async = AsyncMock(return_value="`$\\alpha$`")

        with patch.object(service, "rate_limit", new_callable=AsyncMock):

            # When
            await service._summarize_paper_info(paper)

            # Then
            assert paper.summary == "$\\alpha$"


# =============================================================================
# 17. _get_processed_ids メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_processed_ids_success(mock_env_vars):
    """
    Given: 処理済みIDファイルが存在
    When: _get_processed_idsメソッドを呼び出す
    Then: IDリストが正常に取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # ストレージモック
        with patch.object(
            service.storage,
            "load",
            new_callable=AsyncMock,
            return_value="2301.00001\n2301.00002\n2301.00003\n",
        ):

            # When
            result = await service._get_processed_ids(date(2024, 1, 1))

            # Then
            assert result == ["2301.00001", "2301.00002", "2301.00003"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_processed_ids_empty_file(mock_env_vars):
    """
    Given: 処理済みIDファイルが空
    When: _get_processed_idsメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # ストレージモック（空）
        with patch.object(service.storage, "load", new_callable=AsyncMock, return_value=""):

            # When
            result = await service._get_processed_ids(date(2024, 1, 1))

            # Then
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_processed_ids_file_not_found(mock_env_vars):
    """
    Given: 処理済みIDファイルが存在しない
    When: _get_processed_idsメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        # ストレージモック（None）
        with patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None):

            # When
            result = await service._get_processed_ids(date(2024, 1, 1))

            # Then
            assert result == []


# =============================================================================
# 18. _serialize_papers メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_serialize_papers_success(mock_env_vars):
    """
    Given: 有効な論文情報のリスト
    When: _serialize_papersメソッドを呼び出す
    Then: 辞書のリストに正常にシリアライズされる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        papers = [
            PaperInfo(
                title="Test Paper 1",
                abstract="Abstract 1",
                url="http://arxiv.org/abs/2301.00001",
                contents="Contents 1",
                published_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            ),
            PaperInfo(
                title="Test Paper 2",
                abstract="Abstract 2",
                url="http://arxiv.org/abs/2301.00002",
                contents="Contents 2",
                published_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
            ),
        ]

        # summaryを設定
        papers[0].summary = "Summary 1"
        papers[1].summary = "Summary 2"

        # When
        result = service._serialize_papers(papers)

        # Then
        assert len(result) == 2
        assert result[0]["title"] == "Test Paper 1"
        assert result[0]["abstract"] == "Abstract 1"
        assert result[0]["url"] == "http://arxiv.org/abs/2301.00001"
        assert result[0]["summary"] == "Summary 1"
        assert result[0]["published_at"] == "2023-01-01T00:00:00+00:00"


@pytest.mark.unit
def test_serialize_papers_no_published_date(mock_env_vars):
    """
    Given: published_atがNoneの論文情報
    When: _serialize_papersメソッドを呼び出す
    Then: 現在時刻が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import (
            ArxivSummarizer,
            PaperInfo,
        )

        service = ArxivSummarizer()

        papers = [
            PaperInfo(
                title="Test Paper",
                abstract="Abstract",
                url="http://arxiv.org/abs/2301.00001",
                contents="Contents",
                published_at=None,
            )
        ]
        papers[0].summary = "Summary"

        # When
        result = service._serialize_papers(papers)

        # Then
        assert len(result) == 1
        assert "published_at" in result[0]
        # 現在時刻が使用されることを確認（厳密なチェックは避ける）
        assert result[0]["published_at"] is not None


# =============================================================================
# 19. _paper_sort_key メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_paper_sort_key_valid_date(mock_env_vars):
    """
    Given: 有効なpublished_atを持つ論文
    When: _paper_sort_keyメソッドを呼び出す
    Then: 正しいソートキーが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        item = {"published_at": "2023-01-15T10:30:00+00:00"}

        # When
        result = service._paper_sort_key(item)

        # Then
        assert result[0] == 0
        assert result[1] == datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.mark.unit
def test_paper_sort_key_invalid_date(mock_env_vars):
    """
    Given: 無効なpublished_atを持つ論文
    When: _paper_sort_keyメソッドを呼び出す
    Then: datetime.minが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        item = {"published_at": "invalid-date"}

        # When
        result = service._paper_sort_key(item)

        # Then
        assert result[0] == 0
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)


@pytest.mark.unit
def test_paper_sort_key_no_date(mock_env_vars):
    """
    Given: published_atがない論文
    When: _paper_sort_keyメソッドを呼び出す
    Then: datetime.minが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        item = {}

        # When
        result = service._paper_sort_key(item)

        # Then
        assert result[0] == 0
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)


# =============================================================================
# 20. _render_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_render_markdown_success(mock_env_vars):
    """
    Given: 有効な論文レコードのリスト
    When: _render_markdownメソッドを呼び出す
    Then: Markdown形式のテキストが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        records = [
            {
                "title": "Test Paper 1",
                "url": "http://arxiv.org/abs/2301.00001",
                "abstract": "Abstract 1",
                "summary": "Summary 1",
            },
            {
                "title": "Test Paper 2",
                "url": "http://arxiv.org/abs/2301.00002",
                "abstract": "Abstract 2",
                "summary": "Summary 2",
            },
        ]

        today = datetime(2024, 1, 1)

        # When
        result = service._render_markdown(records, today)

        # Then
        assert "# arXiv 論文要約 (2024-01-01)" in result
        assert "## [Test Paper 1](http://arxiv.org/abs/2301.00001)" in result
        assert "**abstract**:\nAbstract 1" in result
        assert "**summary**:\nSummary 1" in result
        assert "## [Test Paper 2](http://arxiv.org/abs/2301.00002)" in result
        assert "---" in result


@pytest.mark.unit
def test_render_markdown_empty_list(mock_env_vars):
    """
    Given: 空の論文レコードリスト
    When: _render_markdownメソッドを呼び出す
    Then: ヘッダーのみのMarkdownが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        records = []
        today = datetime(2024, 1, 1)

        # When
        result = service._render_markdown(records, today)

        # Then
        assert "# arXiv 論文要約 (2024-01-01)" in result
        assert len(result.strip()) > 0


# =============================================================================
# 21. _parse_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_parse_markdown_success(mock_env_vars):
    """
    Given: 有効なMarkdown形式のテキスト
    When: _parse_markdownメソッドを呼び出す
    Then: 論文レコードのリストが生成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        markdown = """# arXiv 論文要約 (2024-01-01)

## [Test Paper 1](http://arxiv.org/abs/2301.00001)

**abstract**:
Abstract 1

**summary**:
Summary 1

---

## [Test Paper 2](http://arxiv.org/abs/2301.00002)

**abstract**:
Abstract 2

**summary**:
Summary 2

---

"""

        # When
        result = service._parse_markdown(markdown)

        # Then
        assert len(result) == 2
        assert result[0]["title"] == "Test Paper 1"
        assert result[0]["url"] == "http://arxiv.org/abs/2301.00001"
        assert result[0]["abstract"] == "Abstract 1"
        assert result[0]["summary"] == "Summary 1"
        assert result[1]["title"] == "Test Paper 2"


@pytest.mark.unit
def test_parse_markdown_empty_text(mock_env_vars):
    """
    Given: 空のMarkdownテキスト
    When: _parse_markdownメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        markdown = ""

        # When
        result = service._parse_markdown(markdown)

        # Then
        assert result == []


@pytest.mark.unit
def test_parse_markdown_invalid_format(mock_env_vars):
    """
    Given: 不正な形式のMarkdownテキスト
    When: _parse_markdownメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        markdown = "This is not a valid markdown format for papers"

        # When
        result = service._parse_markdown(markdown)

        # Then
        assert result == []


# =============================================================================
# 22. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_method(mock_env_vars):
    """
    Given: ArxivSummarizerインスタンス
    When: runメソッドを呼び出す
    Then: asyncio.runでcollectが呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()

        with patch("asyncio.run") as mock_asyncio_run:

            # When
            service.run(limit=10)

            # Then
            mock_asyncio_run.assert_called_once()
