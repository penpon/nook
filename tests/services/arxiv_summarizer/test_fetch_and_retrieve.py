"""ArxivSummarizer - データ取得・ダウンロード のテスト

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

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

# ArxivSummarizer関連のインポート
from nook.services.arxiv_summarizer.arxiv_summarizer import PaperInfo

# =============================================================================
# 5. _get_curated_paper_ids メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_success(arxiv_service, test_date, respx_mock):
    """Given: 有効なHugging Faceページ
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
            return_value=Mock(text=mock_html, url="https://huggingface.co/papers/date/2024-01-01")
        )

        # When
        result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

        # Then
        assert result is not None
        assert isinstance(result, list)
        assert len(result) <= 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_404_error(arxiv_service, test_date, respx_mock):
    """Given: Hugging FaceページがHTTP 404エラーを返す
    When: _get_curated_paper_idsメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: HTTP 404エラー
    respx_mock.get("https://huggingface.co/papers/date/2024-01-01").mock(
        return_value=httpx.Response(404)
    )

    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        response_mock = Mock()
        response_mock.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=Mock(status_code=404)
            )
        )
        arxiv_service.http_client.get = AsyncMock(return_value=response_mock)

        # When
        result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_redirect(arxiv_service, test_date):
    """Given: Hugging Faceページがリダイレクトする
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
        result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_fallback_to_top_page(arxiv_service, test_date):
    """Given: 日付ページが空でトップページにフォールバック
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
        result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

        # Then
        assert result is not None
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_empty_result(arxiv_service, test_date):
    """Given: 全ページが空
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
        result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

        # Then
        assert isinstance(result, list)
        assert len(result) == 0


# =============================================================================
# 24. _get_curated_paper_ids 追加パターンテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_curated_paper_ids_with_duplicates(arxiv_service, test_date):
    """Given: 重複IDを含むHTML
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
            return_value=Mock(text=mock_html, url="https://huggingface.co/papers/date/2024-01-01")
        )

        # _get_processed_idsをモック（空）
        with patch.object(
            arxiv_service, "_get_processed_ids", new_callable=AsyncMock, return_value=[]
        ):
            # When
            result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

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
    """Given: 既に処理済みのIDが存在
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
            return_value=Mock(text=mock_html, url="https://huggingface.co/papers/date/2024-01-01")
        )

        # 2301.00001 と 2301.00002 は既に処理済み
        with patch.object(
            arxiv_service,
            "_get_processed_ids",
            new_callable=AsyncMock,
            return_value=["2301.00001", "2301.00002"],
        ):
            # When
            result = await arxiv_service._get_curated_paper_ids(limit=5, snapshot_date=test_date)

            # Then
            assert result is not None
            assert isinstance(result, list)
            # 処理済みIDが除外されていることを確認
            assert len(result) == 1
            assert "2301.00003" in result
            assert "2301.00001" not in result
            assert "2301.00002" not in result


# =============================================================================
# 6. _download_pdf_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_success(arxiv_service, arxiv_helper):
    """Given: 有効なPDF URL
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
async def test_download_pdf_timeout(arxiv_service, arxiv_helper):
    """Given: PDFダウンロードがタイムアウト
    When: _download_pdf_without_retryメソッドを呼び出す
    Then: TimeoutException が発生する
    """
    # Given: タイムアウトするHTTPクライアントをモック
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = arxiv_helper.create_mock_http_client()
        mock_client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.return_value = mock_client_instance

        # When/Then
        with pytest.raises(httpx.TimeoutException):
            await arxiv_service._download_pdf_without_retry(
                f"https://arxiv.org/pdf/{arxiv_helper.DEFAULT_ARXIV_ID}"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_404_error(arxiv_service, arxiv_helper):
    """Given: PDF URLが404エラーを返す
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

        mock_client_instance = arxiv_helper.create_mock_http_client()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # When/Then
        with pytest.raises(httpx.HTTPStatusError):
            await arxiv_service._download_pdf_without_retry(
                f"https://arxiv.org/pdf/{arxiv_helper.DEFAULT_ARXIV_ID}"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_pdf_500_error(arxiv_service, arxiv_helper):
    """Given: PDF URLが500エラーを返す
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

        mock_client_instance = arxiv_helper.create_mock_http_client()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # When/Then
        with pytest.raises(httpx.HTTPStatusError):
            await arxiv_service._download_pdf_without_retry(
                f"https://arxiv.org/pdf/{arxiv_helper.DEFAULT_ARXIV_ID}"
            )


# =============================================================================
# 13. _download_html_without_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_success(arxiv_service, arxiv_helper):
    """Given: 有効なHTML URL
    When: _download_html_without_retryメソッドを呼び出す
    Then: HTMLが正常にダウンロードされる
    """
    # Given: モックHTTPクライアント
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = arxiv_helper.create_mock_html_response(
            "<html><body>Test HTML content</body></html>"
        )

        mock_client = arxiv_helper.create_mock_http_client()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._download_html_without_retry(
            f"https://arxiv.org/html/{arxiv_helper.DEFAULT_ARXIV_ID}"
        )

        # Then
        assert result == "<html><body>Test HTML content</body></html>"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_404_returns_empty_string(arxiv_service, arxiv_helper):
    """Given: HTML URLが404エラーを返す
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

        mock_client = arxiv_helper.create_mock_http_client()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._download_html_without_retry(
            f"https://arxiv.org/html/{arxiv_helper.DEFAULT_ARXIV_ID}"
        )

        # Then
        assert result == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_html_timeout(arxiv_service, arxiv_helper):
    """Given: HTMLダウンロードがタイムアウト
    When: _download_html_without_retryメソッドを呼び出す
    Then: 例外が再発生する
    """
    # Given: タイムアウトするHTTPクライアント
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = arxiv_helper.create_mock_http_client()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_class.return_value = mock_client

        # When/Then
        with pytest.raises(httpx.TimeoutException):
            await arxiv_service._download_html_without_retry(
                f"https://arxiv.org/html/{arxiv_helper.DEFAULT_ARXIV_ID}"
            )


# =============================================================================
# 10. _retrieve_paper_info メソッドのテスト（arxiv.Search モック）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_success(arxiv_service, mock_arxiv_paper_factory, arxiv_helper):
    """Given: 有効な論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: 論文情報が正常に取得される
    """
    from nook.services.arxiv_summarizer.arxiv_summarizer import PaperInfo

    # Given: ファクトリーを使用してモック論文を作成
    mock_paper = mock_arxiv_paper_factory(
        arxiv_id=f"{arxiv_helper.DEFAULT_ARXIV_ID}v1",
        title="Test Paper Title",
        summary="Test abstract",
        published=datetime(2023, 1, 1, tzinfo=UTC),
    )

    # arxiv.Clientをモック
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = [mock_paper]
        mock_client_class.return_value = mock_client

        # 翻訳と本文抽出をモック
        with (
            patch.object(
                arxiv_service,
                "_translate_to_japanese",
                new_callable=AsyncMock,
                return_value="テスト要約",
            ),
            patch.object(
                arxiv_service,
                "_extract_body_text",
                new_callable=AsyncMock,
                return_value="Test content",
            ),
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
async def test_retrieve_paper_info_no_results(arxiv_service, arxiv_helper):
    """Given: 存在しない論文ID
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（結果なし）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = arxiv_helper.create_mock_arxiv_client(results=[])
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._retrieve_paper_info("9999.99999")

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_api_error(arxiv_service, arxiv_helper):
    """Given: arxiv APIがエラーを返す
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（エラー）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = arxiv_helper.create_mock_arxiv_client()
        mock_client.results.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._retrieve_paper_info(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_paper_info_with_fallback_to_abstract(arxiv_service):
    """Given: 本文抽出が失敗
    When: _retrieve_paper_infoメソッドを呼び出す
    Then: アブストラクトが本文として使用される
    """
    # Given: モックarxiv結果
    mock_paper = Mock()
    mock_paper.entry_id = "http://arxiv.org/abs/2301.00001v1"
    mock_paper.title = "Test Paper Title"
    mock_paper.summary = "Test abstract content"
    mock_paper.published = datetime(2023, 1, 1, tzinfo=UTC)

    # arxiv.Clientをモック
    with patch("arxiv.Client") as mock_client_class:
        mock_client = Mock()
        mock_client.results.return_value = [mock_paper]
        mock_client_class.return_value = mock_client

        # 翻訳をモック、本文抽出は空文字列を返す
        with (
            patch.object(
                arxiv_service,
                "_translate_to_japanese",
                new_callable=AsyncMock,
                return_value="テスト要約",
            ),
            patch.object(
                arxiv_service,
                "_extract_body_text",
                new_callable=AsyncMock,
                return_value="",
            ),
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
async def test_get_paper_date_success(arxiv_service, arxiv_helper):
    """Given: 有効な論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: 公開日が正常に取得される
    """
    # Given: モックarxiv結果
    mock_paper = Mock()
    mock_paper.published = datetime(2023, 1, 15, 10, 30, 0)

    # arxiv.Clientをモック
    with patch("arxiv.Client") as mock_client_class:
        mock_client = arxiv_helper.create_mock_arxiv_client(results=[mock_paper])
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result is not None
        assert result == date(2023, 1, 15)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_no_results(arxiv_service, arxiv_helper):
    """Given: 存在しない論文ID
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（結果なし）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = arxiv_helper.create_mock_arxiv_client(results=[])
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date("9999.99999")

        # Then
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_paper_date_api_error(arxiv_service, arxiv_helper):
    """Given: arxiv APIがエラーを返す
    When: _get_paper_dateメソッドを呼び出す
    Then: Noneが返される
    """
    # Given: arxiv.Clientをモック（エラー）
    with patch("arxiv.Client") as mock_client_class:
        mock_client = arxiv_helper.create_mock_arxiv_client()
        mock_client.results.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        # When
        result = await arxiv_service._get_paper_date(arxiv_helper.DEFAULT_ARXIV_ID)

        # Then
        assert result is None
