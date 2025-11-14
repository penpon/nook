"""
ArxivSummarizer - ストレージ・ID管理 のテスト

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
from unittest.mock import AsyncMock, patch

import pytest

# ArxivSummarizer関連のインポート

# =============================================================================
# 17. _get_processed_ids メソッドのテスト（パラメータ化）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("storage_return_value", "expected_ids"),
    [
        # ファイルが存在し、IDが含まれている
        (
            "2301.00001\n2301.00002\n2301.00003\n",
            ["2301.00001", "2301.00002", "2301.00003"],
        ),
        # ファイルが空
        ("", []),
        # ファイルが存在しない
        (None, []),
    ],
    ids=["success_with_ids", "empty_file", "file_not_found"],
)
async def test_get_processed_ids(
    arxiv_service, test_date, storage_return_value, expected_ids
):
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
        arxiv_service.storage,
        "load",
        new_callable=AsyncMock,
        return_value=markdown_content,
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
    ), patch.object(
        arxiv_service.storage, "load", new_callable=AsyncMock, return_value=None
    ):
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
    with patch.object(
        arxiv_service.storage, "load", new_callable=AsyncMock, return_value=""
    ):
        # When
        result = await arxiv_service._load_ids_from_file("arxiv_ids-2024-01-01.txt")

        # Then
        assert result == []
