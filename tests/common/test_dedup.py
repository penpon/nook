from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.dedup import (
    TitleNormalizer,
    DedupTracker,
    load_existing_titles_from_storage,
)


def _create_storage(
    *,
    load_return=None,
    load_side_effect=None,
    markdown_return="",
    markdown_side_effect=None,
):
    storage = AsyncMock()
    if load_side_effect is not None:
        storage.load.side_effect = load_side_effect
    elif load_return is not None:
        storage.load.return_value = load_return
    storage.load_markdown = MagicMock(return_value=markdown_return)
    if markdown_side_effect is not None:
        storage.load_markdown.side_effect = markdown_side_effect
    return storage


class TestTitleNormalizer:
    """TitleNormalizerのテスト"""

    def test_normalize_empty_string(self):
        """空文字列の正規化テスト"""
        result = TitleNormalizer.normalize("")
        assert result == ""

        result = TitleNormalizer.normalize(None)
        assert result == ""

    def test_normalize_basic_functionality(self):
        """基本的な正規化機能テスト"""
        # Unicode正規化とcasefold
        result = TitleNormalizer.normalize("ＡＢＣ１２３")
        assert result == "abc123"

        # 大文字小文字の無視
        result = TitleNormalizer.normalize("Hello World")
        assert result == "hello world"

    def test_normalize_whitespace_handling(self):
        """空白文字の処理テスト"""
        # 余分な空白の圧縮
        result = TitleNormalizer.normalize("Hello    World")
        assert result == "hello world"

        # 先頭末尾の空白除去
        result = TitleNormalizer.normalize("   Hello World   ")
        assert result == "hello world"

        # タブと改行の処理
        result = TitleNormalizer.normalize("Hello\t\nWorld")
        assert result == "hello world"

    def test_normalize_decoration_removal(self):
        """装飾記号の除去テスト"""
        # 先頭の【】
        result = TitleNormalizer.normalize("【重要】Hello World")
        assert result == "hello world"

        # 末尾の【】
        result = TitleNormalizer.normalize("Hello World【重要】")
        assert result == "hello world"

        # 先頭の「」
        result = TitleNormalizer.normalize("「注目」Hello World")
        assert result == "hello world"

        # 先頭の『』
        result = TitleNormalizer.normalize("『必読』Hello World")
        assert result == "hello world"

    def test_normalize_symbol_normalization(self):
        """記号の正規化テスト"""
        # 連続する感嘆符
        result = TitleNormalizer.normalize("Hello!!! World")
        assert result == "hello! world"

        # 連続する疑問符
        result = TitleNormalizer.normalize("Hello??? World")
        assert result == "hello? world"

        # 連続するチルダ
        result = TitleNormalizer.normalize("Hello~~~ World")
        assert result == "hello~ world"

        # 全角記号
        result = TitleNormalizer.normalize("Hello！！ World")
        assert result == "hello! world"

    def test_are_duplicates_basic(self):
        """基本的な重複判定テスト"""
        assert TitleNormalizer.are_duplicates("Hello World", "hello world")
        assert TitleNormalizer.are_duplicates("Ｈｅｌｌｏ　Ｗｏｒｌｄ", "hello world")
        assert TitleNormalizer.are_duplicates("【重要】Hello World", "hello world")

        assert not TitleNormalizer.are_duplicates("Hello World", "Goodbye World")
        assert not TitleNormalizer.are_duplicates("Hello World", "")

    def test_are_duplicates_edge_cases(self):
        """境界値の重複判定テスト"""
        # 空文字列
        assert TitleNormalizer.are_duplicates("", "")
        assert TitleNormalizer.are_duplicates(None, "")
        assert TitleNormalizer.are_duplicates("", None)

        # 記号の違い
        assert TitleNormalizer.are_duplicates("Hello!!!", "hello!")
        assert TitleNormalizer.are_duplicates("Hello???", "hello?")


class TestDedupTracker:
    """DedupTrackerのテスト"""

    def test_init(self):
        """初期化テスト"""
        tracker = DedupTracker()
        assert len(tracker.seen_normalized_titles) == 0
        assert len(tracker.title_mapping) == 0

    def test_is_duplicate_and_add(self):
        """重複チェックと追加のテスト"""
        tracker = DedupTracker()

        # 最初のタイトルは重複でない
        is_dup, normalized = tracker.is_duplicate("Hello World")
        assert is_dup is False
        assert normalized == "hello world"

        # 追加する
        added_normalized = tracker.add("Hello World")
        assert added_normalized == normalized
        assert len(tracker.seen_normalized_titles) == 1
        assert tracker.title_mapping[normalized] == "Hello World"

        # 同じタイトルは重複と判定される
        is_dup, normalized2 = tracker.is_duplicate("hello world")
        assert is_dup is True
        assert normalized2 == normalized

    def test_add_multiple_titles(self):
        """複数タイトルの追加テスト"""
        tracker = DedupTracker()

        titles = ["Hello World", "Goodbye World", "【重要】Hello World"]
        for title in titles:
            tracker.add(title)

        assert tracker.count() == 2  # "Hello World"と"【重要】Hello World"は重複

        # 重複チェック
        assert tracker.is_duplicate("Hello World")[0] is True
        assert tracker.is_duplicate("Goodbye World")[0] is True
        assert tracker.is_duplicate("New Title")[0] is False

    def test_get_original_title(self):
        """元タイトル取得テスト"""
        tracker = DedupTracker()

        normalized = tracker.add("Original Title")

        # 存在するタイトル
        original = tracker.get_original_title(normalized)
        assert original == "Original Title"

        # 存在しないタイトル
        original = tracker.get_original_title("nonexistent")
        assert original is None

    def test_count(self):
        """カウントテスト"""
        tracker = DedupTracker()

        assert tracker.count() == 0

        tracker.add("Title 1")
        assert tracker.count() == 1

        tracker.add("Title 2")
        assert tracker.count() == 2

        # 重複タイトルはカウントしない
        tracker.add("title 1")
        assert tracker.count() == 2

    def test_title_mapping_updates(self):
        """タイトルマッピングの更新テスト"""
        tracker = DedupTracker()

        # 同じ正規化タイトルで異なる元タイトルを追加
        normalized1 = tracker.add("Hello World")
        normalized2 = tracker.add("hello world")

        assert normalized1 == normalized2
        # 最初のタイトルが保持される
        assert tracker.get_original_title(normalized1) == "Hello World"


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_json_success():
    """JSONファイルからのタイトル読み込み成功テスト"""
    # モックストレージの準備
    mock_storage = _create_storage(
        load_return=json.dumps(
            [
                {"title": "Article 1", "content": "Content 1"},
                {"title": "Article 2", "content": "Content 2"},
                {"title": "Article 3", "content": "Content 3"},
            ]
        )
    )

    target_dates = {date(2024, 1, 1), date(2024, 1, 2)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 3
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True
    assert tracker.is_duplicate("Article 3")[0] is True
    assert tracker.is_duplicate("New Article")[0] is False


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_file_not_found():
    """ファイルが存在しない場合のテスト"""
    mock_storage = _create_storage()
    mock_storage.load.side_effect = FileNotFoundError("File not found")

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_json_decode_error():
    """JSONデコードエラーのテスト"""
    mock_storage = AsyncMock()
    mock_storage.load.return_value = "invalid json"
    mock_storage.load_markdown = MagicMock(return_value="")

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_general_error():
    """一般エラーのテスト"""
    mock_storage = AsyncMock()
    mock_storage.load.side_effect = Exception("General error")
    mock_storage.load_markdown = MagicMock(return_value="")

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_with_markdown_fallback():
    """Markdownフォールバックのテスト"""
    mock_storage = AsyncMock()

    # JSONは空で、Markdownから読み込むケース
    mock_storage.load.return_value = None
    mock_storage.load_markdown = MagicMock(
        return_value="""# Test Markdown

### [Article 1](http://example.com/1)
Content of article 1

### [Article 2](http://example.com/2)
Content of article 2
"""
    )

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 2
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True

    # 呼び出しを検証
    mock_storage.load.assert_called_with("2024-01-01.json")
    mock_storage.load_markdown.assert_called_with(
        "", datetime.combine(date(2024, 1, 1), time.min)
    )


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_markdown_error():
    """Markdown読み込みエラーのテスト"""
    mock_storage = AsyncMock()
    mock_storage.load.return_value = None
    mock_storage.load_markdown = MagicMock(side_effect=Exception("Markdown error"))

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_file_not_found_logs_debug():
    """ファイル未検出時のデバッグログテスト"""
    mock_storage = _create_storage(
        load_side_effect=FileNotFoundError("File not found"), markdown_return=""
    )

    mock_logger = MagicMock()
    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(
        mock_storage, target_dates, mock_logger
    )

    assert tracker.count() == 0
    mock_logger.debug.assert_any_call("📂 ファイル未検出: 2024-01-01.json")


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_json_decode_error_logs_warning():
    """JSON解析エラー時の警告ログテスト"""
    mock_storage = _create_storage(
        load_side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
    )

    mock_logger = MagicMock()
    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(
        mock_storage, target_dates, mock_logger
    )

    assert tracker.count() == 0
    mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_general_error_logs_debug():
    """一般エラー時のデバッグログテスト"""
    mock_storage = _create_storage(load_side_effect=Exception("General error"))

    mock_logger = MagicMock()
    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(
        mock_storage, target_dates, mock_logger
    )

    assert tracker.count() == 0
    mock_logger.debug.assert_called()


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_markdown_fallback_with_titles():
    """Markdownフォールバックでタイトルを抽出するテスト"""
    mock_storage = AsyncMock()

    # JSONは空で、Markdownから読み込むケース
    mock_storage.load.return_value = None
    mock_storage.load_markdown = MagicMock(
        return_value="""# Test Markdown

### [Article 1](http://example.com/1)
Content of article 1

### [Article 2](http://example.com/2)
Content of article 2

### [Article 3](http://example.com/3)
Content of article 3
"""
    )

    mock_logger = MagicMock()
    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(
        mock_storage, target_dates, mock_logger
    )

    assert tracker.count() == 3
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True
    assert tracker.is_duplicate("Article 3")[0] is True

    # Markdown読み込みログが呼ばれたことを確認
    mock_logger.debug.assert_any_call("📂 既存記事読み込み: 2024-01-01.md")


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_markdown_title_extraction():
    """Markdownからのタイトル抽出詳細テスト"""
    mock_storage = AsyncMock()

    mock_storage.load.return_value = None
    mock_storage.load_markdown = MagicMock(
        return_value="""# Test

### [First Article](url)
Content

### [Second Article](url)
Content

### [Third Article](url)
Content
"""
    )

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 3

    # タイトルが正しく正規化されて追加されることを確認
    assert tracker.is_duplicate("First Article")[0] is True
    assert tracker.is_duplicate("Second Article")[0] is True
    assert tracker.is_duplicate("Third Article")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_with_logger():
    """ロガー付きのテスト"""
    mock_storage = AsyncMock()
    mock_storage.load.return_value = json.dumps([{"title": "Test Article"}])
    mock_storage.load_markdown = MagicMock(return_value="")

    mock_logger = MagicMock()
    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(
        mock_storage, target_dates, mock_logger
    )

    assert tracker.count() == 1
    # デバッグログが呼ばれたことを確認
    mock_logger.debug.assert_called()


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_empty_articles():
    """空の記事リストのテスト"""
    mock_storage = AsyncMock()
    mock_storage.load.return_value = json.dumps([])
    mock_storage.load_markdown = MagicMock(return_value="")

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_articles_without_titles():
    """タイトルなし記事のテスト"""
    mock_storage = AsyncMock()
    mock_storage.load_markdown = MagicMock(return_value="")
    mock_storage.load.return_value = json.dumps(
        [
            {"content": "Content without title"},
            {"title": "", "content": "Empty title"},
            {"title": "Valid Title", "content": "Valid content"},
        ]
    )

    target_dates = {date(2024, 1, 1)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 1
    assert tracker.is_duplicate("Valid Title")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_from_storage_multiple_dates():
    """複数日付のテスト"""
    mock_storage = AsyncMock()

    def load_side_effect(filename):
        if "2024-01-01" in filename:
            return json.dumps([{"title": "Article 1"}])
        elif "2024-01-02" in filename:
            return json.dumps([{"title": "Article 2"}])
        return None

    mock_storage.load.side_effect = load_side_effect
    mock_storage.load_markdown = MagicMock(return_value="")

    target_dates = {date(2024, 1, 1), date(2024, 1, 2)}

    tracker = await load_existing_titles_from_storage(mock_storage, target_dates)

    assert tracker.count() == 2
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True
