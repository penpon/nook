"""
ArxivSummarizer - テキスト抽出・変換 のテスト

このファイルは元々 test_arxiv_summarizer.py の一部でしたが、
保守性向上のため機能別に分割されました。

関連ファイル:
- test_init_and_integration.py: 初期化・統合テスト
- test_fetch_and_retrieve.py: データ取得・ダウンロード
- test_extract_and_transform.py: テキスト抽出・変換
- test_format_and_serialize.py: フォーマット・シリアライズ
- test_storage_and_ids.py: ストレージ・ID管理
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

# ArxivSummarizer関連のインポート
from nook.services.arxiv_summarizer.arxiv_summarizer import (
    ArxivSummarizer,
)

# =============================================================================
# 7. _extract_from_pdf メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_success(arxiv_service, arxiv_helper):
    """
    Given: 有効なPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: テキストが正常に抽出される
    """
    # Given: モックPDF
    mock_pdf = arxiv_helper.create_mock_pdf(
        "This is a test paper content. " * 10  # 十分な長さ
    )

    # モックHTTPレスポンス
    mock_response = arxiv_helper.create_mock_pdf_response()

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", return_value=mock_pdf):
        # When
        result = await arxiv_service._extract_from_pdf(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert isinstance(result, str)
        assert len(result) > 0
        assert "test paper content" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_empty_content(arxiv_service, arxiv_helper):
    """
    Given: 空のPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 空のHTTPレスポンス
    mock_response = arxiv_helper.create_mock_pdf_response(content=b"")

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        # When
        result = await arxiv_service._extract_from_pdf(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_corrupted(arxiv_service, arxiv_helper):
    """
    Given: 破損したPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 破損したPDFデータ
    mock_response = arxiv_helper.create_mock_pdf_response(content=b"corrupted data")

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", side_effect=Exception("Corrupted PDF")):
        # When
        result = await arxiv_service._extract_from_pdf(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_download_error(arxiv_service, arxiv_helper):
    """
    Given: PDFダウンロードがエラー
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: ダウンロードエラーをモック
    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        side_effect=Exception("Download error"),
    ):
        # When
        result = await arxiv_service._extract_from_pdf(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_filters_short_lines(arxiv_service, arxiv_helper):
    """
    Given: 短い行を含むPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 短い行がフィルタリングされる
    """
    # Given: 短い行と長い行が混在するPDF
    pdf_text = f"""Short
1
arXiv:{arxiv_helper.DEFAULT_ARXIV_ID}
This is a long enough line that should be kept in the extracted text because it meets the minimum length requirement.
References
Another long enough line that should be kept because it is sufficiently long.
12345"""

    mock_pdf = arxiv_helper.create_mock_pdf(pdf_text)
    mock_response = arxiv_helper.create_mock_pdf_response()

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", return_value=mock_pdf):
        # When
        result = await arxiv_service._extract_from_pdf(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert isinstance(result, str)
        # 短い行（Short, 1, arXiv:, 12345）が除外されていることを確認
        assert "Short" not in result
        assert "arXiv:" not in result
        # 長い行は含まれている
        assert "long enough line" in result


# =============================================================================
# 12. _extract_from_html メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_success(arxiv_service, arxiv_helper):
    """
    Given: 有効なHTML
    When: _extract_from_htmlメソッドを呼び出す
    Then: テキストが正常に抽出される
    """
    # Given: モックHTML
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
        arxiv_service,
        "_download_html_without_retry",
        new_callable=AsyncMock,
        return_value=mock_html,
    ):
        # When
        result = await arxiv_service._extract_from_html(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert isinstance(result, str)
        assert len(result) > 0
        # ヘッダーやフッターは除外される
        assert "Header content" not in result
        assert "Navigation" not in result
        assert "Footer content" not in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_404_error(arxiv_service):
    """
    Given: HTML URLが404エラーを返す
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 404エラーをモック
    with patch.object(
        arxiv_service, "_download_html_without_retry", new_callable=AsyncMock, return_value=""
    ):
        # When
        result = await arxiv_service._extract_from_html("2301.00001")

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_empty_body(arxiv_service):
    """
    Given: 空のHTML
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 空のHTML
    mock_html = "<html><body></body></html>"

    with patch.object(
        arxiv_service,
        "_download_html_without_retry",
        new_callable=AsyncMock,
        return_value=mock_html,
    ):
        # When
        result = await arxiv_service._extract_from_html("2301.00001")

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_download_error(arxiv_service):
    """
    Given: HTMLダウンロードがエラー
    When: _extract_from_htmlメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: ダウンロードエラーをモック
    with patch.object(
        arxiv_service,
        "_download_html_without_retry",
        new_callable=AsyncMock,
        side_effect=Exception("Download error"),
    ):
        # When
        result = await arxiv_service._extract_from_html("2301.00001")

        # Then
        assert result == ""


# =============================================================================
# 14. _extract_body_text メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_from_html(arxiv_service):
    """
    Given: HTMLが利用可能
    When: _extract_body_textメソッドを呼び出す
    Then: HTMLからテキストが抽出される
    """
    # Given: HTMLからの抽出が成功
    with patch.object(
        arxiv_service,
        "_extract_from_html",
        new_callable=AsyncMock,
        return_value="HTML extracted text",
    ):
        # When
        result = await arxiv_service._extract_body_text("2301.00001")

        # Then
        assert result == "HTML extracted text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_fallback_to_pdf(arxiv_service):
    """
    Given: HTML抽出が失敗し、PDF抽出が成功
    When: _extract_body_textメソッドを呼び出す
    Then: PDFからテキストが抽出される
    """
    # Given: HTML抽出は空、PDF抽出は成功
    with patch.object(
        arxiv_service, "_extract_from_html", new_callable=AsyncMock, return_value=""
    ), patch.object(
        arxiv_service,
        "_extract_from_pdf",
        new_callable=AsyncMock,
        return_value="PDF extracted text",
    ):
        # When
        result = await arxiv_service._extract_body_text("2301.00001")

        # Then
        assert result == "PDF extracted text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_body_text_both_fail(arxiv_service):
    """
    Given: HTMLとPDFの両方の抽出が失敗
    When: _extract_body_textメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: HTML、PDF両方とも空
    with patch.object(
        arxiv_service, "_extract_from_html", new_callable=AsyncMock, return_value=""
    ), patch.object(
        arxiv_service, "_extract_from_pdf", new_callable=AsyncMock, return_value=""
    ):
        # When
        result = await arxiv_service._extract_body_text("2301.00001")

        # Then
        assert result == ""


# =============================================================================
# 15. _is_valid_body_line メソッドのテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "line,expected_result",
    [
        # 有効な本文行: 十分な長さ、ピリオドあり
        ("This is a valid body line with sufficient length and proper sentence structure.", True),
        # 短すぎる行
        ("Short line.", False),
        # メールアドレスを含む行
        ("Contact us at test@example.com for more information about this research paper.", False),
        # 'university'を含む行
        ("Department of Computer Science, Stanford University, California, USA contact information.", False),
        # ピリオドを含まない行
        ("This is a line without proper punctuation but with sufficient length to pass", False),
    ],
    ids=["valid_line", "too_short", "with_email", "with_university", "no_period"],
)
def test_is_valid_body_line(arxiv_service, arxiv_helper, line, expected_result):
    """
    Given: 様々な条件の本文行
    When: _is_valid_body_lineメソッドを呼び出す
    Then: 適切な検証結果が返される
    """
    # When: 定数を使用してmin_lengthを指定
    result = arxiv_service._is_valid_body_line(
        line, min_length=arxiv_helper.DEFAULT_MIN_LINE_LENGTH
    )

    # Then
    assert result is expected_result


# =============================================================================
# 8. _translate_to_japanese メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_success(arxiv_service):
    """
    Given: 有効な英語テキスト
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 日本語に翻訳される
    """
    # Given: GPTクライアントをモック
    arxiv_service.gpt_client.generate_async = AsyncMock(
        return_value="これはテスト翻訳です。"
    )

    with patch.object(arxiv_service, "rate_limit", new_callable=AsyncMock):
        # When
        result = await arxiv_service._translate_to_japanese("This is a test.")

        # Then
        assert result == "これはテスト翻訳です。"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_gpt_error(arxiv_service):
    """
    Given: GPT APIがエラーを返す
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 原文が返される
    """
    # Given: GPT APIエラーをモック
    arxiv_service.gpt_client.generate_async = AsyncMock(
        side_effect=Exception("API Error")
    )

    # When
    result = await arxiv_service._translate_to_japanese("This is a test.")

    # Then
    assert result == "This is a test."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_empty_text(arxiv_service):
    """
    Given: 空のテキスト
    When: _translate_to_japaneseメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 空文字列を返すGPTクライアント
    arxiv_service.gpt_client.generate_async = AsyncMock(return_value="")

    with patch.object(arxiv_service, "rate_limit", new_callable=AsyncMock):
        # When
        result = await arxiv_service._translate_to_japanese("")

        # Then
        assert result == ""
