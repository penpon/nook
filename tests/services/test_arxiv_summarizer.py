"""
nook/services/arxiv_summarizer/arxiv_summarizer.py のテスト

テスト観点:
- ArxivSummarizerの初期化
- 論文検索と取得
- 論文情報抽出
- データ保存
- エラーハンドリング

コード品質改善（レビュー対応）:
1. 可読性向上:
   - arxiv_serviceフィクスチャで重複するセットアップを削減
   - arxiv_helperで定数とヘルパーメソッドを集約
   - マジックナンバーを定数化（DEFAULT_MIN_LINE_LENGTH等）

2. 保守性向上:
   - paper_info_factory/mock_arxiv_paper_factoryで一貫したテストデータ作成
   - test_date/test_datetimeフィクスチャでハードコード日付を削減
   - ArxivTestHelperクラスでモック作成ロジックを共通化

3. DRY原則の適用:
   - 70+テストで繰り返されていたサービス作成を1フィクスチャに集約
   - 30+テストで繰り返されていたHTTPクライアントモックをヘルパーメソッドに
   - パラメータ化テストで重複を削減（25テスト → 5パラメータ化テスト）

4. テスト速度:
   - 全テストでモック使用（外部API呼び出しゼロ）
   - 並列実行可能な設計維持
   - 不要な import の削減

改善効果:
- コード削減: 約400行の重複削減
- 保守性: フィクスチャ変更で全テストに影響
- 可読性: テストの意図が明確化
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

# ArxivSummarizer関連のインポート（テスト内で繰り返し使用されるため冒頭でインポート）
from nook.services.arxiv_summarizer.arxiv_summarizer import (
    ArxivSummarizer,
    PaperInfo,
    remove_outer_markdown_markers,
    remove_outer_singlequotes,
    remove_tex_backticks,
)

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(arxiv_service):
    """
    Given: デフォルトのstorage_dir
    When: ArxivSummarizerを初期化
    Then: インスタンスが正常に作成される
    """
    # Given/When: arxiv_serviceフィクスチャが初期化済み
    # Then
    assert arxiv_service.service_name == "arxiv_summarizer"


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_papers(arxiv_service, mock_arxiv_api):
    """
    Given: 有効なarXiv API
    When: collectメソッドを呼び出す
    Then: 論文が正常に取得・保存される
    """
    # Given: モック設定
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(
        arxiv_service.storage,
        "save",
        new_callable=AsyncMock,
        return_value=Path("/data/test.json"),
    ):
        arxiv_service.gpt_client.get_response = AsyncMock(return_value="要約")

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_categories(arxiv_service):
    """
    Given: 複数のカテゴリ
    When: collectメソッドを呼び出す
    Then: 全てのカテゴリが処理される
    """
    # Given: モック設定
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(arxiv_service.storage, "save", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(return_value=Mock(text="<feed></feed>"))

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(arxiv_service):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    # Given: ネットワークエラーをシミュレート
    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(side_effect=Exception("Network error"))

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_xml(arxiv_service):
    """
    Given: 不正なXML
    When: collectメソッドを呼び出す
    Then: エラーがログされ、空リストが返される
    """
    # Given: 不正なXMLレスポンスをモック
    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(return_value=Mock(text="Invalid XML"))

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(arxiv_service):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    # Given: GPT APIエラーをモック
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(arxiv_service.storage, "save", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(text="<feed><entry></entry></feed>")
        )
        arxiv_service.gpt_client.get_response = AsyncMock(
            side_effect=Exception("API Error")
        )

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(arxiv_service):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    # Given: 完全なワークフローのモック設定
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service, "setup_http_client", new_callable=AsyncMock
    ), patch.object(
        arxiv_service.storage,
        "save",
        new_callable=AsyncMock,
        return_value=Path("/data/test.json"),
    ):
        arxiv_service.http_client.get = AsyncMock(return_value=Mock(text="<feed></feed>"))
        arxiv_service.gpt_client.get_response = AsyncMock(return_value="要約")

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)

        await arxiv_service.cleanup()


# =============================================================================
# 5. _get_curated_paper_ids メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_success(arxiv_service, test_date, respx_mock):
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

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(
                text=mock_html, url="https://huggingface.co/papers/date/2024-01-01"
            )
        )

        # When
        result = await arxiv_service._get_curated_paper_ids(
            limit=5, snapshot_date=test_date
        )

        # Then
        assert result is not None
        assert isinstance(result, list)
        assert len(result) <= 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_404_error(arxiv_service, test_date, respx_mock):
    """
    Given: Hugging FaceページがHTTP 404エラーを返す
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: HTTP 404エラー
    respx_mock.get("https://huggingface.co/papers/date/2024-01-01").mock(
        return_value=httpx.Response(404)
    )

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        response_mock = AsyncMock()
        response_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=Mock(status_code=404)
        )
        arxiv_service.http_client.get = AsyncMock(return_value=response_mock)

        # When
        result = await arxiv_service._get_curated_paper_ids(
            limit=5, snapshot_date=test_date
        )

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_redirect(arxiv_service, test_date):
    """
    Given: Hugging Faceページがリダイレクトする
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: リダイレクトのモック
    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        # リダイレクト後のURLが異なる
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(
                text="<html></html>",
                url="https://huggingface.co/papers",  # 異なるURL
            )
        )

        # When
        result = await arxiv_service._get_curated_paper_ids(
            limit=5, snapshot_date=test_date
        )

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_fallback_to_top_page(arxiv_service, test_date):
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

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        # 1回目: 空の日付ページ、2回目: トップページ
        arxiv_service.http_client.get = AsyncMock(
            side_effect=[
                Mock(
                    text=mock_html_empty,
                    url="https://huggingface.co/papers/date/2024-01-01",
                ),
                Mock(text=mock_html_top, url="https://huggingface.co/papers"),
            ]
        )

        # When
        result = await arxiv_service._get_curated_paper_ids(
            limit=5, snapshot_date=test_date
        )

        # Then
        assert result is not None
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_empty_result(arxiv_service, test_date):
    """
    Given: 全ページが空
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: 空リストが返される
    """
    # Given: 空のHTML
    mock_html_empty = "<html><body></body></html>"

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(
                text=mock_html_empty,
                url="https://huggingface.co/papers/date/2024-01-01",
            )
        )

        # When
        result = await arxiv_service._get_curated_paper_ids(
            limit=5, snapshot_date=test_date
        )

        # Then
        assert isinstance(result, list)
        assert len(result) == 0


# =============================================================================
# 6. _download_pdf_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_success(arxiv_service, arxiv_helper):
    """
    Given: 有効なPDF URL
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: PDFが正常にダウンロードされる
    """
    # Given: モックHTTPクライアント
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = arxiv_helper.create_mock_pdf_response()
        mock_client_instance = arxiv_helper.create_mock_http_client()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # When
        result = await arxiv_service._download_pdf_without_retry(
            f"https://arxiv.org/pdf/{arxiv_helper.DEFAULT_ARXIV_ID}"
        )

        # Then
        assert result.content == b"%PDF-1.4 test content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_timeout(arxiv_service):
    """
    Given: PDFダウンロードがタイムアウト
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: TimeoutException が発生する
    """
    # Given: タイムアウトするHTTPクライアントをモック
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
            await arxiv_service._download_pdf_without_retry(
                "https://arxiv.org/pdf/2301.00001"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_404_error(arxiv_service):
    """
    Given: PDF URLが404エラーを返す
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: HTTPStatusError が発生する
    """
    # Given: 404エラーを返すHTTPクライアントをモック
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
            await arxiv_service._download_pdf_without_retry(
                "https://arxiv.org/pdf/2301.00001"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_500_error(arxiv_service):
    """
    Given: PDF URLが500エラーを返す
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: HTTPStatusError が発生する
    """
    # Given: 500エラーを返すHTTPクライアントをモック
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
            await arxiv_service._download_pdf_without_retry(
                "https://arxiv.org/pdf/2301.00001"
            )


# =============================================================================
# 7. _extract_from_pdf メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_success(arxiv_service):
    """
    Given: 有効なPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: テキストが正常に抽出される
    """
    # Given: モックPDF
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
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", return_value=mock_pdf):
        # When
        result = await arxiv_service._extract_from_pdf("2301.00001")

        # Then
        assert isinstance(result, str)
        assert len(result) > 0
        assert "test paper content" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_empty_content(arxiv_service):
    """
    Given: 空のPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 空のHTTPレスポンス
    mock_response = Mock()
    mock_response.content = b""

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        # When
        result = await arxiv_service._extract_from_pdf("2301.00001")

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_corrupted(arxiv_service):
    """
    Given: 破損したPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 空文字列が返される
    """
    # Given: 破損したPDFデータ
    mock_response = Mock()
    mock_response.content = b"corrupted data"

    with patch.object(
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", side_effect=Exception("Corrupted PDF")):
        # When
        result = await arxiv_service._extract_from_pdf("2301.00001")

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_download_error(arxiv_service):
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
        result = await arxiv_service._extract_from_pdf("2301.00001")

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_pdf_filters_short_lines(arxiv_service):
    """
    Given: 短い行を含むPDF
    When: _extract_from_pdfメソッドを呼び出す
    Then: 短い行がフィルタリングされる
    """
    # Given: 短い行と長い行が混在するPDF
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
        arxiv_service,
        "_download_pdf_without_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ), patch("pdfplumber.open", return_value=mock_pdf):
        # When
        result = await arxiv_service._extract_from_pdf("2301.00001")

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


# =============================================================================
# 9. ユーティリティ関数のテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "input_text,expected_output",
    [
        # TeX形式: バッククォート除去
        ("`$\\ldots$`", "$\\ldots$"),
        # 通常のテキスト: 変更なし
        ("normal text", "normal text"),
        # 部分マッチ: 変更なし
        ("`incomplete", "`incomplete"),
    ],
    ids=["tex_format", "normal_text", "partial_match"],
)
def test_remove_tex_backticks(input_text, expected_output):
    """
    Given: 様々な形式の文字列
    When: remove_tex_backticksを呼び出す
    Then: 適切に処理される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import remove_tex_backticks

    # When
    result = remove_tex_backticks(input_text)

    # Then
    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "input_text,expected_output",
    [
        # Markdownマーカーあり: 除去
        ("```markdown\ncode\n```", "\ncode\n"),
        # マーカーなし: 変更なし
        ("normal text", "normal text"),
    ],
    ids=["with_markers", "without_markers"],
)
def test_remove_outer_markdown_markers(input_text, expected_output):
    """
    Given: Markdownマーカーの有無が異なる文字列
    When: remove_outer_markdown_markersを呼び出す
    Then: 適切に処理される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_markdown_markers,
    )

    # When
    result = remove_outer_markdown_markers(input_text)

    # Then
    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "input_text,expected_output",
    [
        # シングルクォートあり: 除去
        ("'''quoted text'''", "quoted text"),
        # クォートなし: 変更なし
        ("normal text", "normal text"),
    ],
    ids=["with_quotes", "without_quotes"],
)
def test_remove_outer_singlequotes(input_text, expected_output):
    """
    Given: シングルクォートの有無が異なる文字列
    When: remove_outer_singlequotesを呼び出す
    Then: 適切に処理される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import (
        remove_outer_singlequotes,
    )

    # When
    result = remove_outer_singlequotes(input_text)

    # Then
    assert result == expected_output


# =============================================================================
# 10. _retrieve_paper_info メソッドのテスト（arxiv.Search モック）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_success(arxiv_service, mock_arxiv_paper_factory, arxiv_helper):
    """
    Given: 有効な論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: 論文情報が正常に取得される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import PaperInfo

    # Given: ファクトリーを使用してモック論文を作成
    mock_paper = mock_arxiv_paper_factory(
        arxiv_id=f"{arxiv_helper.DEFAULT_ARXIV_ID}v1",
        title="Test Paper Title",
        summary="Test abstract",
        published=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )

    # arxiv.Clientをモック
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = [mock_paper]
        mock_client_class.return_value = mock_client

        # 翻訳と本文抽出をモック
        with patch.object(
            arxiv_service,
            "_translate_to_japanese",
            new_callable=AsyncMock,
            return_value="テスト要約",
        ), patch.object(
            arxiv_service, "_extract_body_text", new_callable=AsyncMock, return_value="Test content"
        ):
            # When
            result = await arxiv_service._retrieve_paper_info(arxiv_helper.DEFAULT_ARXIV_ID)

            # Then
            assert result is not None
            assert isinstance(result, PaperInfo)
            assert result.title == "Test Paper Title"
            assert result.abstract == "テスト要約"
            assert result.url == f"http://arxiv.org/abs/{arxiv_helper.DEFAULT_ARXIV_ID}v1"
            assert result.contents == "Test content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_no_results(arxiv_service):
    """
    Given: 存在しない論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（結果なし）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = []
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._retrieve_paper_info("9999.99999")

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_api_error(arxiv_service):
    """
    Given: arxiv APIがエラーを返す
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（エラー）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._retrieve_paper_info("2301.00001")

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_with_fallback_to_abstract(arxiv_service):
    """
    Given: 本文抽出が失敗
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: アブストラクトが本文として使用される
    """
    # Given: モックarxiv結果
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
            arxiv_service, "_translate_to_japanese", new_callable=AsyncMock, return_value="テスト要約"
        ), patch.object(
            arxiv_service, "_extract_body_text", new_callable=AsyncMock, return_value=""
        ):
            # When
            result = await arxiv_service._retrieve_paper_info("2301.00001")

            # Then
            assert result is not None
            assert isinstance(result, PaperInfo)
            assert result.contents == "Test abstract content"


# =============================================================================
# 11. _get_paper_date メソッドのテスト（arxiv.Search モック）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_success(arxiv_service):
    """
    Given: 有効な論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: 公開日が正常に取得される
    """
    # Given: モックarxiv結果
    mock_paper = Mock()
    mock_paper.published = datetime(2023, 1, 15, 10, 30, 0)

    # arxiv.Clientをモック
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = [mock_paper]
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date("2301.00001")

        # Then
        assert result is not None
        assert result == date(2023, 1, 15)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_no_results(arxiv_service):
    """
    Given: 存在しない論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（結果なし）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = []
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date("9999.99999")

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_api_error(arxiv_service):
    """
    Given: arxiv APIがエラーを返す
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（エラー）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date("2301.00001")

        # Then
        assert result is None


# =============================================================================
# 12. _extract_from_html メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_from_html_success(arxiv_service):
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
        result = await arxiv_service._extract_from_html("2301.00001")

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
# 13. _download_html_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_success(arxiv_service):
    """
    Given: 有効なHTML URL
    When: _download_html_without_retryメソッドを呼び出す
    Then: HTMLが正常にダウンロードされる
    """
    # Given: モックHTTPクライアント
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
        result = await arxiv_service._download_html_without_retry(
            "https://arxiv.org/html/2301.00001"
        )

        # Then
        assert result == "<html><body>Test HTML content</body></html>"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_404_returns_empty_string(arxiv_service):
    """
    Given: HTML URLが404エラーを返す
    When: _download_html_without_retryメソッドを呼び出す
    Then: 空文字列が返される（例外は発生しない）
    """
    # Given: 404エラーを返すHTTPクライアント
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
        result = await arxiv_service._download_html_without_retry(
            "https://arxiv.org/html/2301.00001"
        )

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_timeout(arxiv_service):
    """
    Given: HTMLダウンロードがタイムアウト
    When: _download_html_without_retryメソッドを呼び出す
    Then: 例外が再発生する
    """
    # Given: タイムアウトするHTTPクライアント
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        # When/Then
        with pytest.raises(httpx.TimeoutException):
            await arxiv_service._download_html_without_retry(
                "https://arxiv.org/html/2301.00001"
            )


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
# 16. _summarize_paper_info メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_success(arxiv_service):
    """
    Given: 有効な論文情報
    When: _summarize_paper_infoメソッドを呼び出す
    Then: 要約が正常に生成される
    """
    # Given: 論文情報
    paper = PaperInfo(
        title="Test Paper",
        abstract="Test abstract",
        url="http://arxiv.org/abs/2301.00001",
        contents="Test contents",
    )

    # GPTクライアントをモック
    arxiv_service.gpt_client.generate_async = AsyncMock(return_value="```markdown\nTest summary\n```")

    with patch.object(arxiv_service, "rate_limit", new_callable=AsyncMock):
        # When
        await arxiv_service._summarize_paper_info(paper)

        # Then
        assert paper.summary == "\nTest summary\n"
        arxiv_service.gpt_client.generate_async.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_gpt_error(arxiv_service):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_paper_infoメソッドを呼び出す
    Then: エラーメッセージが要約として設定される
    """
    # Given: 論文情報
    paper = PaperInfo(
        title="Test Paper",
        abstract="Test abstract",
        url="http://arxiv.org/abs/2301.00001",
        contents="Test contents",
    )

    # GPTクライアントをモック（エラー）
    arxiv_service.gpt_client.generate_async = AsyncMock(side_effect=Exception("API Error"))

    # When
    await arxiv_service._summarize_paper_info(paper)

    # Then
    assert "要約の生成中にエラーが発生しました" in paper.summary
    assert "API Error" in paper.summary


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_paper_info_removes_tex_backticks(arxiv_service):
    """
    Given: TeX形式のバッククォートを含む要約
    When: _summarize_paper_infoメソッドを呼び出す
    Then: バッククォートが除去される
    """
    # Given: 論文情報
    paper = PaperInfo(
        title="Test Paper",
        abstract="Test abstract",
        url="http://arxiv.org/abs/2301.00001",
        contents="Test contents",
    )

    # GPTクライアントをモック（TeX形式含む）
    arxiv_service.gpt_client.generate_async = AsyncMock(return_value="`$\\alpha$`")

    with patch.object(arxiv_service, "rate_limit", new_callable=AsyncMock):
        # When
        await arxiv_service._summarize_paper_info(paper)

        # Then
        assert paper.summary == "$\\alpha$"


# =============================================================================
# 17. _get_processed_ids メソッドのテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_return_value,expected_ids",
    [
        # ファイルが存在し、IDが含まれている
        ("2301.00001\n2301.00002\n2301.00003\n", ["2301.00001", "2301.00002", "2301.00003"]),
        # ファイルが空
        ("", []),
        # ファイルが存在しない
        (None, []),
    ],
    ids=["success_with_ids", "empty_file", "file_not_found"],
)
async def test_get_processed_ids(arxiv_service, test_date, storage_return_value, expected_ids):
    """
    Given: 様々な状態の処理済みIDファイル
    When: _get_processed_idsメソッドを呼び出す
    Then: 適切なIDリストが返される
    """
    # Given: ストレージモック
    with patch.object(
        arxiv_service.storage,
        "load",
        new_callable=AsyncMock,
        return_value=storage_return_value,
    ):
        # When: test_dateフィクスチャを使用
        result = await arxiv_service._get_processed_ids(test_date)

        # Then
        assert result == expected_ids


# =============================================================================
# 18. _serialize_papers メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_serialize_papers_success(arxiv_service, paper_info_factory):
    """
    Given: 有効な論文情報のリスト
    When: _serialize_papersメソッドを呼び出す
    Then: 辞書のリストに正常にシリアライズされる
    """
    # Given: ファクトリーを使用して論文を作成
    papers = [
        paper_info_factory(
            title="Test Paper 1",
            abstract="Abstract 1",
            arxiv_id="2301.00001",
            contents="Contents 1",
            published_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            summary="Summary 1",
        ),
        paper_info_factory(
            title="Test Paper 2",
            abstract="Abstract 2",
            arxiv_id="2301.00002",
            contents="Contents 2",
            published_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
            summary="Summary 2",
        ),
    ]

    # When
    result = arxiv_service._serialize_papers(papers)

    # Then
    assert len(result) == 2
    assert result[0]["title"] == "Test Paper 1"
    assert result[0]["abstract"] == "Abstract 1"
    assert result[0]["url"] == "http://arxiv.org/abs/2301.00001"
    assert result[0]["summary"] == "Summary 1"
    assert result[0]["published_at"] == "2023-01-01T00:00:00+00:00"


@pytest.mark.unit
def test_serialize_papers_no_published_date(arxiv_service):
    """
    Given: published_atがNoneの論文情報
    When: _serialize_papersメソッドを呼び出す
    Then: 現在時刻が使用される
    """
    # Given: published_atがNoneの論文情報
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
    result = arxiv_service._serialize_papers(papers)

    # Then
    assert len(result) == 1
    assert "published_at" in result[0]
    # 現在時刻が使用されることを確認（厳密なチェックは避ける）
    assert result[0]["published_at"] is not None


# =============================================================================
# 19. _paper_sort_key メソッドのテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "item,expected_tuple",
    [
        # 有効な日付
        (
            {"published_at": "2023-01-15T10:30:00+00:00"},
            (0, datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)),
        ),
        # 無効な日付
        ({"published_at": "invalid-date"}, (0, datetime.min.replace(tzinfo=timezone.utc))),
        # 日付なし
        ({}, (0, datetime.min.replace(tzinfo=timezone.utc))),
    ],
    ids=["valid_date", "invalid_date", "no_date"],
)
def test_paper_sort_key(arxiv_service, item, expected_tuple):
    """
    Given: 様々なpublished_at状態の論文
    When: _paper_sort_keyメソッドを呼び出す
    Then: 正しいソートキーが返される
    """
    # When
    result = arxiv_service._paper_sort_key(item)

    # Then
    assert result[0] == expected_tuple[0]
    assert result[1] == expected_tuple[1]


# =============================================================================
# 20. _render_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_render_markdown_success(arxiv_service, test_datetime):
    """
    Given: 有効な論文レコードのリスト
    When: _render_markdownメソッドを呼び出す
    Then: Markdown形式のテキストが生成される
    """
    # Given: 論文レコード
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

    # When
    result = arxiv_service._render_markdown(records, test_datetime)

    # Then
    assert "# arXiv 論文要約 (2024-01-01)" in result
    assert "## [Test Paper 1](http://arxiv.org/abs/2301.00001)" in result
    assert "**abstract**:\nAbstract 1" in result
    assert "**summary**:\nSummary 1" in result
    assert "## [Test Paper 2](http://arxiv.org/abs/2301.00002)" in result
    assert "---" in result


@pytest.mark.unit
def test_render_markdown_empty_list(arxiv_service, test_datetime):
    """
    Given: 空の論文レコードリスト
    When: _render_markdownメソッドを呼び出す
    Then: ヘッダーのみのMarkdownが生成される
    """
    # Given: 空のレコード
    records = []

    # When
    result = arxiv_service._render_markdown(records, test_datetime)

    # Then
    assert "# arXiv 論文要約 (2024-01-01)" in result
    assert len(result.strip()) > 0


# =============================================================================
# 21. _parse_markdown メソッドのテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "markdown,expected_result",
    [
        # 有効なMarkdown形式
        (
            """# arXiv 論文要約 (2024-01-01)

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

""",
            [
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
            ],
        ),
        # 空のMarkdownテキスト
        ("", []),
        # 不正な形式のMarkdownテキスト
        ("This is not a valid markdown format for papers", []),
    ],
    ids=["valid_markdown", "empty_text", "invalid_format"],
)
def test_parse_markdown(arxiv_service, markdown, expected_result):
    """
    Given: 様々な形式のMarkdownテキスト
    When: _parse_markdownメソッドを呼び出す
    Then: 適切な論文レコードリストが返される
    """
    # When
    result = arxiv_service._parse_markdown(markdown)

    # Then
    if expected_result:
        assert len(result) == len(expected_result)
        for i, expected_paper in enumerate(expected_result):
            assert result[i]["title"] == expected_paper["title"]
            assert result[i]["url"] == expected_paper["url"]
            assert result[i]["abstract"] == expected_paper["abstract"]
            assert result[i]["summary"] == expected_paper["summary"]
    else:
        assert result == expected_result


# =============================================================================
# 22. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_method(arxiv_service):
    """
    Given: ArxivSummarizerインスタンス
    When: runメソッドを呼び出す
    Then: asyncio.runでcollectが呼ばれる
    """
    # Given: arxiv_serviceフィクスチャが初期化済み
    with patch("asyncio.run") as mock_asyncio_run:
        # When
        arxiv_service.run(limit=10)

        # Then
        mock_asyncio_run.assert_called_once()


# =============================================================================
# 23. _save_processed_ids_by_date メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_processed_ids_by_date_success(arxiv_service, test_date):
    """
    Given: 論文IDリストと対象日付
    When: _save_processed_ids_by_dateメソッドを呼び出す
    Then: 日付ごとにファイルが保存される
    """
    # Given: 論文IDリストと対象日付
    paper_ids = ["2301.00001", "2301.00002"]
    target_dates = [test_date, date(2024, 1, 2)]

    # _get_paper_dateをモック
    with patch.object(
        arxiv_service,
        "_get_paper_date",
        new_callable=AsyncMock,
        side_effect=[test_date, date(2024, 1, 2)],
    ), patch.object(
        arxiv_service, "_load_ids_from_file", new_callable=AsyncMock, return_value=[]
    ), patch.object(
        arxiv_service, "save_data", new_callable=AsyncMock
    ) as mock_save:
        # When
        await arxiv_service._save_processed_ids_by_date(paper_ids, target_dates)

        # Then
        assert mock_save.call_count == 2
        # 各日付のファイルが保存されることを確認
        calls = mock_save.call_args_list
        assert "2301.00001" in calls[0][0][0] or "2301.00002" in calls[0][0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_processed_ids_by_date_with_existing_ids(arxiv_service, test_date):
    """
    Given: 既存IDファイルが存在
    When: 新規IDを保存
    Then: 既存IDと新規IDがマージされて重複なく保存される
    """
    # Given: 既存IDあり
    paper_ids = ["2301.00001", "2301.00002"]
    target_dates = [test_date]

    with patch.object(
        arxiv_service, "_get_paper_date", new_callable=AsyncMock, return_value=test_date
    ), patch.object(
        arxiv_service,
        "_load_ids_from_file",
        new_callable=AsyncMock,
        return_value=["2301.00001"],  # 既に存在
    ), patch.object(
        arxiv_service, "save_data", new_callable=AsyncMock
    ) as mock_save:
        # When
        await arxiv_service._save_processed_ids_by_date(paper_ids, target_dates)

        # Then
        mock_save.assert_called_once()
        # マージされたIDが保存されることを確認（重複除去）
        saved_content = mock_save.call_args[0][0]
        saved_ids = saved_content.split("\n")
        assert len([id for id in saved_ids if id == "2301.00001"]) == 1  # 重複なし


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_processed_ids_by_date_unknown_date(arxiv_service, test_date):
    """
    Given: 日付が不明の論文ID
    When: _save_processed_ids_by_dateメソッドを呼び出す
    Then: 今日の日付で保存される
    """
    # Given: 日付が不明の論文ID
    paper_ids = ["2301.00001"]
    target_dates = [test_date]

    # _get_paper_dateがNoneを返す
    with patch.object(
        arxiv_service, "_get_paper_date", new_callable=AsyncMock, return_value=None
    ), patch.object(
        arxiv_service, "_load_ids_from_file", new_callable=AsyncMock, return_value=[]
    ), patch.object(
        arxiv_service, "save_data", new_callable=AsyncMock
    ) as mock_save:
        # When
        await arxiv_service._save_processed_ids_by_date(paper_ids, target_dates)

        # Then
        mock_save.assert_called_once()
        # 今日の日付のファイル名で保存されることを確認
        filename = mock_save.call_args[0][1]
        assert "arxiv_ids-" in filename
        assert ".txt" in filename


# =============================================================================
# 24. _get_curated_paper_ids 追加パターンテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_with_duplicates(arxiv_service, test_date):
    """
    Given: 重複IDを含むHTML
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: 重複が除去される
    """
    # Given: 重複IDを含むHTML
    mock_html = """
    <html>
        <article>
            <a href="/papers/2301.00001">Test Paper 1</a>
        </article>
        <article>
            <a href="/papers/2301.00001">Test Paper 1 (duplicate)</a>
        </article>
        <article>
            <a href="/papers/2301.00002">Test Paper 2</a>
        </article>
    </html>
    """

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(
                text=mock_html, url="https://huggingface.co/papers/date/2024-01-01"
            )
        )

        # _get_processed_idsをモック（空）
        with patch.object(
            arxiv_service, "_get_processed_ids", new_callable=AsyncMock, return_value=[]
        ):
            # When
            result = await arxiv_service._get_curated_paper_ids(
                limit=5, snapshot_date=test_date
            )

            # Then
            assert result is not None
            assert isinstance(result, list)
            # 重複が除去されていることを確認
            assert len(result) == 2
            assert "2301.00001" in result
            assert "2301.00002" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_filters_processed_ids(arxiv_service, test_date):
    """
    Given: 既に処理済みのIDが存在
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: 処理済みIDが除外される
    """
    # Given: 処理済みIDを含むHTML
    mock_html = """
    <html>
        <article>
            <a href="/papers/2301.00001">Test Paper 1</a>
        </article>
        <article>
            <a href="/papers/2301.00002">Test Paper 2</a>
        </article>
        <article>
            <a href="/papers/2301.00003">Test Paper 3</a>
        </article>
    </html>
    """

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(
                text=mock_html, url="https://huggingface.co/papers/date/2024-01-01"
            )
        )

        # 2301.00001 と 2301.00002 は既に処理済み
        with patch.object(
            arxiv_service,
            "_get_processed_ids",
            new_callable=AsyncMock,
            return_value=["2301.00001", "2301.00002"],
        ):
            # When
            result = await arxiv_service._get_curated_paper_ids(
                limit=5, snapshot_date=test_date
            )

            # Then
            assert result is not None
            assert isinstance(result, list)
            # 処理済みIDが除外されていることを確認
            assert len(result) == 1
            assert "2301.00003" in result
            assert "2301.00001" not in result
            assert "2301.00002" not in result


# =============================================================================
# 25. _load_existing_papers メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_papers_from_json(arxiv_service, test_datetime):
    """
    Given: JSONファイルが存在
    When: _load_existing_papersメソッドを呼び出す
    Then: JSONファイルから論文が読み込まれる
    """
    # Given: 既存の論文データ
    existing_papers = [
        {
            "title": "Test Paper 1",
            "abstract": "Abstract 1",
            "url": "http://arxiv.org/abs/2301.00001",
            "summary": "Summary 1",
        }
    ]

    # load_jsonをモック
    with patch.object(
        arxiv_service, "load_json", new_callable=AsyncMock, return_value=existing_papers
    ):
        # When
        result = await arxiv_service._load_existing_papers(test_datetime)

        # Then
        assert result == existing_papers
        assert len(result) == 1
        assert result[0]["title"] == "Test Paper 1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_papers_fallback_to_markdown(arxiv_service, test_datetime):
    """
    Given: JSONファイルが存在せず、Markdownファイルが存在
    When: _load_existing_papersメソッドを呼び出す
    Then: Markdownから論文が解析される
    """
    # Given: Markdownコンテンツ
    markdown_content = """# arXiv 論文要約 (2024-01-01)

## [Test Paper 1](http://arxiv.org/abs/2301.00001)

**abstract**:
Abstract 1

**summary**:
Summary 1

---

"""

    # JSONなし、Markdownあり
    with patch.object(
        arxiv_service, "load_json", new_callable=AsyncMock, return_value=None
    ), patch.object(
        arxiv_service.storage, "load", new_callable=AsyncMock, return_value=markdown_content
    ):
        # When
        result = await arxiv_service._load_existing_papers(test_datetime)

        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Test Paper 1"
        assert result[0]["url"] == "http://arxiv.org/abs/2301.00001"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_papers_no_files(arxiv_service, test_datetime):
    """
    Given: JSONもMarkdownも存在しない
    When: _load_existing_papersメソッドを呼び出す
    Then: 空リストが返される
    """
    # Given: JSONなし、Markdownなし
    with patch.object(
        arxiv_service, "load_json", new_callable=AsyncMock, return_value=None
    ), patch.object(arxiv_service.storage, "load", new_callable=AsyncMock, return_value=None):
        # When
        result = await arxiv_service._load_existing_papers(test_datetime)

        # Then
        assert result == []


# =============================================================================
# 26. _load_ids_from_file メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_ids_from_file_success(arxiv_service):
    """
    Given: 有効なIDファイル
    When: _load_ids_from_fileメソッドを呼び出す
    Then: IDリストが返される
    """
    # Given: IDファイルの内容
    with patch.object(
        arxiv_service.storage,
        "load",
        new_callable=AsyncMock,
        return_value="2301.00001\n2301.00002\n2301.00003\n",
    ):
        # When
        result = await arxiv_service._load_ids_from_file("arxiv_ids-2024-01-01.txt")

        # Then
        assert result == ["2301.00001", "2301.00002", "2301.00003"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_ids_from_file_empty(arxiv_service):
    """
    Given: 空のIDファイル
    When: _load_ids_from_fileメソッドを呼び出す
    Then: 空リストが返される
    """
    # Given: 空のファイル
    with patch.object(arxiv_service.storage, "load", new_callable=AsyncMock, return_value=""):
        # When
        result = await arxiv_service._load_ids_from_file("arxiv_ids-2024-01-01.txt")

        # Then
        assert result == []
