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

from datetime import date
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
