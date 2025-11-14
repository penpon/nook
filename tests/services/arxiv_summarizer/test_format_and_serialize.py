"""
ArxivSummarizer - フォーマット・シリアライズ のテスト

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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

# ArxivSummarizer関連のインポート
from nook.services.arxiv_summarizer.arxiv_summarizer import (
    PaperInfo,
    remove_outer_markdown_markers,
    remove_outer_singlequotes,
    remove_tex_backticks,
)

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
