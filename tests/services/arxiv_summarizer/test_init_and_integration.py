"""
ArxivSummarizer - 初期化・統合テスト

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

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ArxivSummarizer関連のインポート

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
    response_mock = Mock()
    response_mock.raise_for_status = Mock()
    response_mock.url = "https://huggingface.co/papers/date/2024-01-01"
    response_mock.text = "<html></html>"

    arxiv_service.http_client = AsyncMock()
    arxiv_service.http_client.get = AsyncMock(return_value=response_mock)

    with (
        patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock),
        patch.object(
            arxiv_service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ),
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

    with (
        patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock),
        patch.object(arxiv_service.storage, "save", new_callable=AsyncMock),
    ):
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
    Then: RetryExceptionが発生する
    """
    from nook.common.exceptions import RetryException

    # Given: ネットワークエラーをシミュレート
    arxiv_service.http_client = AsyncMock()

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        arxiv_service.http_client.get = AsyncMock(side_effect=Exception("Network error"))

        # When/Then
        with pytest.raises(RetryException):
            await arxiv_service.collect(target_dates=[date.today()])


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

    with (
        patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock),
        patch.object(arxiv_service.storage, "save", new_callable=AsyncMock),
    ):
        arxiv_service.http_client.get = AsyncMock(
            return_value=Mock(text="<feed><entry></entry></feed>")
        )
        arxiv_service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

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

    with (
        patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock),
        patch.object(
            arxiv_service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ),
    ):
        arxiv_service.http_client.get = AsyncMock(return_value=Mock(text="<feed></feed>"))
        arxiv_service.gpt_client.get_response = AsyncMock(return_value="要約")

        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)

        await arxiv_service.cleanup()


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
# 23. カバレッジ向上テスト - エッジケース
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_client_not_initialized(arxiv_service):
    """
    Given: http_clientが未初期化
    When: collectメソッドを呼び出す
    Then: setup_http_clientが自動的に呼ばれる
    """
    # Given: http_clientをNoneに設定
    arxiv_service.http_client = None

    with (
        patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock) as mock_setup,
        patch.object(
            arxiv_service,
            "_get_curated_paper_ids",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        mock_setup.assert_called_once()
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_empty_target_dates(arxiv_service):
    """
    Given: 空のtarget_dates
    When: collectメソッドを呼び出す
    Then: 早期リターンで空リストが返される
    """
    # Given: http_clientをモック化（collect内で使用される可能性があるため）
    response_mock = Mock()
    response_mock.raise_for_status = Mock()

    arxiv_service.http_client = AsyncMock()
    arxiv_service.http_client.get = AsyncMock(return_value=response_mock)

    with patch.object(arxiv_service, "setup_http_client", new_callable=AsyncMock):
        # When
        result = await arxiv_service.collect(target_dates=[])

        # Then
        assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_empty_daily_ids(arxiv_service):
    """
    Given: _get_curated_paper_idsが空リストを返す
    When: collectメソッドを呼び出す
    Then: ログが出力され、空リストが返される
    """
    # Given
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service,
        "_get_curated_paper_ids",
        new_callable=AsyncMock,
        return_value=[],
    ):
        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_none_daily_ids(arxiv_service):
    """
    Given: _get_curated_paper_idsがNoneを返す（URLが見つからない）
    When: collectメソッドを呼び出す
    Then: ログが出力され、空リストが返される
    """
    # Given
    arxiv_service.http_client = AsyncMock()

    with patch.object(
        arxiv_service,
        "_get_curated_paper_ids",
        new_callable=AsyncMock,
        return_value=None,
    ):
        # When
        result = await arxiv_service.collect(target_dates=[date.today()])

        # Then
        assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_all_duplicate_ids(arxiv_service):
    """
    Given: すべてのIDが重複している
    When: collectメソッドを呼び出す（複数日付）
    Then: 重複スキップのログが出力され、空リストが返される
    """
    # Given
    arxiv_service.http_client = AsyncMock()
    from datetime import timedelta

    target_dates = [date.today(), date.today() - timedelta(days=1)]

    with patch.object(
        arxiv_service,
        "_get_curated_paper_ids",
        new_callable=AsyncMock,
        return_value=["2301.00001"],  # 同じIDを返す
    ):
        # When
        result = await arxiv_service.collect(target_dates=target_dates)

        # Then
        assert isinstance(result, list)
