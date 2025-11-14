"""nook/common/dedup.py のテスト"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.dedup import (
    DedupTracker,
    TitleNormalizer,
    load_existing_titles_from_storage,
)

# ================================================================================
# 1. TitleNormalizer.normalize メソッドのテスト
# ================================================================================

# 1.1 基本的な正規化


@pytest.mark.unit
def test_normalize_basic_title():
    """
    Given: 通常のタイトル
    When: normalizeを呼び出す
    Then: 小文字に変換される
    """
    result = TitleNormalizer.normalize("Test Article Title")
    assert result == "test article title"


@pytest.mark.unit
def test_normalize_empty_string():
    """
    Given: 空文字列
    When: normalizeを呼び出す
    Then: 空文字列が返される
    """
    result = TitleNormalizer.normalize("")
    assert result == ""


@pytest.mark.unit
def test_normalize_whitespace_only():
    """
    Given: 空白のみ
    When: normalizeを呼び出す
    Then: 空文字列が返される
    """
    result = TitleNormalizer.normalize("   ")
    assert result == ""


@pytest.mark.unit
def test_normalize_none_input():
    """
    Given: None入力
    When: normalizeを呼び出す
    Then: 空文字列が返される
    """
    result = TitleNormalizer.normalize(None)
    assert result == ""


# 1.2 Unicode正規化（NFKC）


@pytest.mark.unit
def test_normalize_fullwidth_to_halfwidth():
    """
    Given: 全角英数字
    When: normalizeを呼び出す
    Then: 半角に変換される
    """
    result = TitleNormalizer.normalize("ＡＢＣＤ１２３４")
    assert result == "abcd1234"


@pytest.mark.unit
def test_normalize_halfwidth_kana():
    """
    Given: 半角カナ
    When: normalizeを呼び出す
    Then: 全角カナに変換される
    """
    result = TitleNormalizer.normalize("ﾃｽﾄ")
    expected = "テスト".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_composed_characters():
    """
    Given: 合成文字（濁点分離）
    When: normalizeを呼び出す
    Then: 合成される
    """
    result = TitleNormalizer.normalize("カ\u3099")  # カ + 濁点
    expected = "ガ".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_variant_forms():
    """
    Given: 異体字
    When: normalizeを呼び出す
    Then: 統一される
    """
    # 葛（異体字）
    result = TitleNormalizer.normalize("葛")
    expected = "葛".casefold()
    assert result == expected


# 1.3 大文字小文字の無視（casefold）


@pytest.mark.unit
def test_normalize_uppercase_to_lowercase():
    """
    Given: 英大文字
    When: normalizeを呼び出す
    Then: 小文字に変換される
    """
    result = TitleNormalizer.normalize("HELLO WORLD")
    assert result == "hello world"


@pytest.mark.unit
def test_normalize_mixed_case():
    """
    Given: 混在ケース
    When: normalizeを呼び出す
    Then: すべて小文字に変換される
    """
    result = TitleNormalizer.normalize("HeLLo WoRLd")
    assert result == "hello world"


@pytest.mark.unit
def test_normalize_german_eszett():
    """
    Given: ドイツ語ß
    When: normalizeを呼び出す
    Then: ssに変換される
    """
    result = TitleNormalizer.normalize("Straße")
    assert result == "strasse"


@pytest.mark.unit
def test_normalize_turkish_i():
    """
    Given: トルコ語İ
    When: normalizeを呼び出す
    Then: casefold結果になる
    """
    result = TitleNormalizer.normalize("İSTANBUL")
    expected = "İSTANBUL".casefold()
    assert result == expected


# 1.4 空白の正規化


@pytest.mark.unit
def test_normalize_multiple_spaces():
    """
    Given: 連続空白
    When: normalizeを呼び出す
    Then: 1つの空白に圧縮される
    """
    result = TitleNormalizer.normalize("hello    world")
    assert result == "hello world"


@pytest.mark.unit
def test_normalize_newlines_tabs():
    """
    Given: 改行・タブ
    When: normalizeを呼び出す
    Then: 空白に変換される
    """
    result = TitleNormalizer.normalize("hello\n\tworld")
    assert result == "hello world"


@pytest.mark.unit
def test_normalize_trim_whitespace():
    """
    Given: 先頭・末尾の空白
    When: normalizeを呼び出す
    Then: 削除される
    """
    result = TitleNormalizer.normalize("  hello world  ")
    assert result == "hello world"


@pytest.mark.unit
def test_normalize_fullwidth_space():
    """
    Given: 全角空白
    When: normalizeを呼び出す
    Then: 半角空白に変換される
    """
    result = TitleNormalizer.normalize("hello　world")
    assert result == "hello world"


# 1.5 装飾記号の除去


@pytest.mark.unit
def test_normalize_remove_leading_brackets_kakko():
    """
    Given: 先頭の【】
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("【重要】ニュース")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_trailing_brackets_kakko():
    """
    Given: 末尾の【】
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("ニュース【速報】")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_leading_quotes_kagikakko():
    """
    Given: 先頭の「」
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("「速報」ニュース")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_trailing_quotes_kagikakko():
    """
    Given: 末尾の「」
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("ニュース「速報」")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_leading_quotes_nijukagikakko():
    """
    Given: 先頭の『』
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("『速報』ニュース")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_trailing_quotes_nijukagikakko():
    """
    Given: 末尾の『』
    When: normalizeを呼び出す
    Then: 除去される
    """
    result = TitleNormalizer.normalize("ニュース『速報』")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_remove_multiple_decorations():
    """
    Given: 複数装飾の連続
    When: normalizeを呼び出す
    Then: すべて除去される
    """
    result = TitleNormalizer.normalize("【重要】「速報」ニュース『最新』")
    expected = "ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_decorations_only():
    """
    Given: 装飾のみのタイトル
    When: normalizeを呼び出す
    Then: 空文字列が返される
    """
    result = TitleNormalizer.normalize("【速報】")
    assert result == ""


# 1.6 記号の正規化


@pytest.mark.unit
def test_normalize_multiple_exclamations():
    """
    Given: 連続感嘆符
    When: normalizeを呼び出す
    Then: 1つに圧縮される
    """
    result = TitleNormalizer.normalize("すごい!!!")
    expected = "すごい!".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_fullwidth_exclamations():
    """
    Given: 全角感嘆符
    When: normalizeを呼び出す
    Then: 半角1つに圧縮される
    """
    result = TitleNormalizer.normalize("すごい！！！")
    expected = "すごい!".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_multiple_questions():
    """
    Given: 連続疑問符
    When: normalizeを呼び出す
    Then: 1つに圧縮される
    """
    result = TitleNormalizer.normalize("なぜ???")
    expected = "なぜ?".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_fullwidth_questions():
    """
    Given: 全角疑問符
    When: normalizeを呼び出す
    Then: 半角1つに圧縮される
    """
    result = TitleNormalizer.normalize("なぜ？？？")
    expected = "なぜ?".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_multiple_tildes():
    """
    Given: 連続チルダ
    When: normalizeを呼び出す
    Then: 1つに圧縮される
    """
    result = TitleNormalizer.normalize("やった~~~")
    expected = "やった~".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_fullwidth_tildes():
    """
    Given: 全角チルダ
    When: normalizeを呼び出す
    Then: 半角1つに圧縮される
    """
    result = TitleNormalizer.normalize("やった～～～")
    expected = "やった~".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_mixed_symbols():
    """
    Given: 混在記号
    When: normalizeを呼び出す
    Then: それぞれ正規化される
    """
    result = TitleNormalizer.normalize("すごい!？～")
    expected = "すごい!?~".casefold()
    assert result == expected


# 1.7 複雑なケース


@pytest.mark.unit
def test_normalize_japanese_title():
    """
    Given: 日本語タイトル
    When: normalizeを呼び出す
    Then: 正規化される
    """
    result = TitleNormalizer.normalize("最新ニュース")
    expected = "最新ニュース".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_mixed_languages():
    """
    Given: 英日混在
    When: normalizeを呼び出す
    Then: 正規化される
    """
    result = TitleNormalizer.normalize("Apple新製品発表")
    expected = "apple新製品発表".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_with_emojis():
    """
    Given: 絵文字を含む
    When: normalizeを呼び出す
    Then: 絵文字も含めて正規化される
    """
    result = TitleNormalizer.normalize("ニュース😀🎉")
    expected = "ニュース😀🎉".casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_very_long_title():
    """
    Given: 超長文タイトル
    When: normalizeを呼び出す
    Then: 正規化される
    """
    long_title = "あ" * 1000
    result = TitleNormalizer.normalize(long_title)
    expected = long_title.casefold()
    assert result == expected


@pytest.mark.unit
def test_normalize_zero_width_characters():
    """
    Given: ゼロ幅文字を含む
    When: normalizeを呼び出す
    Then: 正規化される
    """
    result = TitleNormalizer.normalize("Test\u200b\u200c\u200dTitle")
    # ゼロ幅文字はNFKCで除去される可能性がある
    assert "test" in result
    assert "title" in result


# ================================================================================
# 2. TitleNormalizer.are_duplicates メソッドのテスト
# ================================================================================


@pytest.mark.unit
def test_are_duplicates_exact_match():
    """
    Given: 完全一致のタイトル
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("Test", "Test")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_case_difference():
    """
    Given: 大文字小文字の違いのみ
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("Test", "test")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_whitespace_difference():
    """
    Given: 空白の違いのみ
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("Test  Title", "Test Title")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_decoration_difference():
    """
    Given: 装飾の違いのみ
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("【重要】Test", "Test")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_symbol_difference():
    """
    Given: 記号の違いのみ
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("Test!!!", "Test!")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_different_titles():
    """
    Given: 全く異なるタイトル
    When: are_duplicatesを呼び出す
    Then: Falseが返される
    """
    result = TitleNormalizer.are_duplicates("Test A", "Test B")
    assert result is False


@pytest.mark.unit
def test_are_duplicates_empty_strings():
    """
    Given: 空文字列同士
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates("", "")
    assert result is True


@pytest.mark.unit
def test_are_duplicates_one_empty():
    """
    Given: 片方が空文字列
    When: are_duplicatesを呼び出す
    Then: Falseが返される
    """
    result = TitleNormalizer.are_duplicates("Test", "")
    assert result is False


@pytest.mark.unit
def test_are_duplicates_both_none():
    """
    Given: None同士
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates(None, None)
    assert result is True


@pytest.mark.unit
def test_are_duplicates_one_none():
    """
    Given: 片方がNone
    When: are_duplicatesを呼び出す
    Then: Falseが返される
    """
    result = TitleNormalizer.are_duplicates("Test", None)
    assert result is False


@pytest.mark.unit
def test_are_duplicates_complex_japanese():
    """
    Given: 複雑な日本語の重複
    When: are_duplicatesを呼び出す
    Then: Trueが返される
    """
    result = TitleNormalizer.are_duplicates(
        "【速報】最新ニュース！！！", "最新ニュース!"
    )
    assert result is True


# ================================================================================
# 3. DedupTracker クラスのテスト
# ================================================================================

# 3.1 __init__ メソッド


@pytest.mark.unit
def test_dedup_tracker_init():
    """
    Given: DedupTracker初期化
    When: インスタンス作成
    Then: seen_normalized_titles=set(), title_mapping={}
    """
    tracker = DedupTracker()
    assert tracker.seen_normalized_titles == set()
    assert tracker.title_mapping == {}


# 3.2 is_duplicate メソッド


@pytest.mark.unit
def test_is_duplicate_new_title():
    """
    Given: 新規タイトル
    When: is_duplicateを呼び出す
    Then: (False, 正規化タイトル)が返される
    """
    tracker = DedupTracker()
    is_dup, normalized = tracker.is_duplicate("Test Title")
    assert is_dup is False
    assert normalized == "test title"


@pytest.mark.unit
def test_is_duplicate_existing_title():
    """
    Given: 既存タイトル（重複）
    When: is_duplicateを呼び出す
    Then: (True, 正規化タイトル)が返される
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    is_dup, normalized = tracker.is_duplicate("Test Title")
    assert is_dup is True
    assert normalized == "test title"


@pytest.mark.unit
def test_is_duplicate_case_difference():
    """
    Given: 大文字小文字違いで重複
    When: is_duplicateを呼び出す
    Then: (True, 正規化タイトル)が返される
    """
    tracker = DedupTracker()
    tracker.add("Test")
    is_dup, normalized = tracker.is_duplicate("test")
    assert is_dup is True
    assert normalized == "test"


@pytest.mark.unit
def test_is_duplicate_decoration_difference():
    """
    Given: 装飾違いで重複
    When: is_duplicateを呼び出す
    Then: (True, 正規化タイトル)が返される
    """
    tracker = DedupTracker()
    tracker.add("Test")
    is_dup, normalized = tracker.is_duplicate("【重要】Test")
    assert is_dup is True
    assert normalized == "test"


@pytest.mark.unit
def test_is_duplicate_empty_string():
    """
    Given: 空文字列
    When: is_duplicateを呼び出す
    Then: (False, "")が返される
    """
    tracker = DedupTracker()
    is_dup, normalized = tracker.is_duplicate("")
    assert is_dup is False
    assert normalized == ""


@pytest.mark.unit
def test_is_duplicate_none_input():
    """
    Given: None入力
    When: is_duplicateを呼び出す
    Then: (False, "")が返される
    """
    tracker = DedupTracker()
    is_dup, normalized = tracker.is_duplicate(None)
    assert is_dup is False
    assert normalized == ""


# 3.3 add メソッド


@pytest.mark.unit
def test_add_new_title():
    """
    Given: 新規タイトル
    When: addを呼び出す
    Then: 正規化タイトルが返され、setに追加される
    """
    tracker = DedupTracker()
    normalized = tracker.add("Test Title")
    assert normalized == "test title"
    assert "test title" in tracker.seen_normalized_titles


@pytest.mark.unit
def test_add_duplicate_title():
    """
    Given: 重複タイトル
    When: addを呼び出す
    Then: 正規化タイトルが返され、setは変わらず
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    initial_count = len(tracker.seen_normalized_titles)
    normalized = tracker.add("test title")
    assert normalized == "test title"
    assert len(tracker.seen_normalized_titles) == initial_count


@pytest.mark.unit
def test_add_updates_title_mapping():
    """
    Given: 初回タイトル追加
    When: addを呼び出す
    Then: title_mappingに記録される
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    assert tracker.title_mapping["test title"] == "Test Title"


@pytest.mark.unit
def test_add_preserves_original_title_mapping():
    """
    Given: 同じ正規化タイトルで2回追加
    When: addを呼び出す
    Then: 最初の元タイトルが保持される
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    tracker.add("test title")
    assert tracker.title_mapping["test title"] == "Test Title"


@pytest.mark.unit
def test_add_empty_string():
    """
    Given: 空文字列追加
    When: addを呼び出す
    Then: ""が返される
    """
    tracker = DedupTracker()
    normalized = tracker.add("")
    assert normalized == ""


@pytest.mark.unit
def test_add_none():
    """
    Given: None追加
    When: addを呼び出す
    Then: ""が返される
    """
    tracker = DedupTracker()
    normalized = tracker.add(None)
    assert normalized == ""


# 3.4 get_original_title メソッド


@pytest.mark.unit
def test_get_original_title_existing():
    """
    Given: 存在する正規化タイトル
    When: get_original_titleを呼び出す
    Then: 元のタイトルが返される
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    original = tracker.get_original_title("test title")
    assert original == "Test Title"


@pytest.mark.unit
def test_get_original_title_nonexistent():
    """
    Given: 存在しない正規化タイトル
    When: get_original_titleを呼び出す
    Then: Noneが返される
    """
    tracker = DedupTracker()
    original = tracker.get_original_title("nonexistent")
    assert original is None


@pytest.mark.unit
def test_get_original_title_empty_string():
    """
    Given: 空文字列
    When: get_original_titleを呼び出す
    Then: Noneが返される（または追加時の元タイトル）
    """
    tracker = DedupTracker()
    original = tracker.get_original_title("")
    assert original is None


# 3.5 count メソッド


@pytest.mark.unit
def test_count_initial_state():
    """
    Given: 初期化直後
    When: countを呼び出す
    Then: 0が返される
    """
    tracker = DedupTracker()
    assert tracker.count() == 0


@pytest.mark.unit
def test_count_after_additions():
    """
    Given: add()を複数回実行
    When: countを呼び出す
    Then: 追加した重複排除後の数が返される
    """
    tracker = DedupTracker()
    tracker.add("Title 1")
    tracker.add("Title 2")
    tracker.add("Title 3")
    assert tracker.count() == 3


@pytest.mark.unit
def test_count_after_duplicate_additions():
    """
    Given: 同じタイトルを複数回add
    When: countを呼び出す
    Then: カウントは増えない
    """
    tracker = DedupTracker()
    tracker.add("Test Title")
    tracker.add("test title")
    tracker.add("【重要】Test Title")
    assert tracker.count() == 1


# ================================================================================
# 4. load_existing_titles_from_storage 関数のテスト
# ================================================================================

# 4.1 JSONファイル読み込み


@pytest.mark.asyncio
async def test_load_existing_titles_from_json():
    """
    Given: 正常なJSONファイル
    When: load_existing_titles_from_storageを呼び出す
    Then: DedupTrackerにタイトルが登録される
    """
    target_dates = {date(2024, 1, 15)}
    articles = [
        {"title": "Article 1", "url": "http://example.com/1"},
        {"title": "Article 2", "url": "http://example.com/2"},
    ]

    storage = AsyncMock()
    storage.load = AsyncMock(return_value=json.dumps(articles))
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 2
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_multiple_dates():
    """
    Given: 複数target_dates
    When: load_existing_titles_from_storageを呼び出す
    Then: すべての日付のJSONが読み込まれる
    """
    target_dates = {date(2024, 1, 15), date(2024, 1, 16)}

    async def load_side_effect(filename):
        if "2024-01-15" in filename:
            return json.dumps([{"title": "Article 1"}])
        elif "2024-01-16" in filename:
            return json.dumps([{"title": "Article 2"}])
        raise FileNotFoundError()

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=load_side_effect)
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 2


@pytest.mark.asyncio
async def test_load_existing_titles_json_not_found():
    """
    Given: JSONファイルが存在しない
    When: load_existing_titles_from_storageを呼び出す
    Then: 空のDedupTrackerが返される
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_json_decode_error():
    """
    Given: 不正なJSON
    When: load_existing_titles_from_storageを呼び出す
    Then: JSONDecodeErrorをキャッチ、継続
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(return_value="invalid json")
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    # エラーをキャッチして空のtrackerが返される
    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_empty_json_array():
    """
    Given: 空のJSON配列
    When: load_existing_titles_from_storageを呼び出す
    Then: DedupTrackerのカウント=0
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(return_value="[]")
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_no_title_field():
    """
    Given: titleフィールドがない記事
    When: load_existing_titles_from_storageを呼び出す
    Then: titleがスキップされる
    """
    target_dates = {date(2024, 1, 15)}
    articles = [
        {"url": "http://example.com/1"},  # titleなし
        {"title": "Article 2", "url": "http://example.com/2"},
    ]

    storage = AsyncMock()
    storage.load = AsyncMock(return_value=json.dumps(articles))
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 1
    assert tracker.is_duplicate("Article 2")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_empty_title():
    """
    Given: titleが空文字列
    When: load_existing_titles_from_storageを呼び出す
    Then: スキップされる
    """
    target_dates = {date(2024, 1, 15)}
    articles = [
        {"title": "", "url": "http://example.com/1"},
        {"title": "Article 2", "url": "http://example.com/2"},
    ]

    storage = AsyncMock()
    storage.load = AsyncMock(return_value=json.dumps(articles))
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    # 空文字列はスキップされる（if title:）
    assert tracker.count() == 1


# 4.2 Markdownファイル読み込み


@pytest.mark.asyncio
async def test_load_existing_titles_from_markdown():
    """
    Given: Markdown形式の記事
    When: load_existing_titles_from_storageを呼び出す
    Then: タイトルが抽出されて追加される
    """
    target_dates = {date(2024, 1, 15)}
    markdown_content = """
### [Article 1](http://example.com/1)
Content here.

### [Article 2](http://example.com/2)
More content.
"""

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(return_value=markdown_content)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 2
    assert tracker.is_duplicate("Article 1")[0] is True
    assert tracker.is_duplicate("Article 2")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_multiple_markdown_entries():
    """
    Given: 複数記事のMarkdown
    When: load_existing_titles_from_storageを呼び出す
    Then: すべてのタイトルが抽出される
    """
    target_dates = {date(2024, 1, 15)}
    markdown_content = """
### [Title 1](http://url1.com)
### [Title 2](http://url2.com)
### [Title 3](http://url3.com)
"""

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(return_value=markdown_content)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 3


@pytest.mark.asyncio
async def test_load_existing_titles_markdown_not_found():
    """
    Given: Markdownファイルが存在しない
    When: load_existing_titles_from_storageを呼び出す
    Then: エラーをキャッチ、継続
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_invalid_markdown_format():
    """
    Given: 不正なMarkdown形式（リンクなし）
    When: load_existing_titles_from_storageを呼び出す
    Then: マッチしない、スキップ
    """
    target_dates = {date(2024, 1, 15)}
    markdown_content = """
### Title without link
Some content.
"""

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(return_value=markdown_content)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 0


# 4.3 統合・その他


@pytest.mark.asyncio
async def test_load_existing_titles_json_and_markdown():
    """
    Given: JSON + Markdown両方のファイルが存在
    When: load_existing_titles_from_storageを呼び出す
    Then: 両方のタイトルが統合される
    """
    target_dates = {date(2024, 1, 15)}
    json_articles = [{"title": "JSON Article"}]
    markdown_content = "### [Markdown Article](http://example.com)"

    storage = AsyncMock()
    storage.load = AsyncMock(return_value=json.dumps(json_articles))
    storage.load_markdown = Mock(return_value=markdown_content)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 2
    assert tracker.is_duplicate("JSON Article")[0] is True
    assert tracker.is_duplicate("Markdown Article")[0] is True


@pytest.mark.asyncio
async def test_load_existing_titles_empty_target_dates():
    """
    Given: 空のtarget_dates
    When: load_existing_titles_from_storageを呼び出す
    Then: 空のDedupTrackerが返される
    """
    target_dates = set()

    storage = AsyncMock()

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_with_logger():
    """
    Given: logger引数を渡す
    When: load_existing_titles_from_storageを呼び出す
    Then: ログ出力される
    """
    target_dates = {date(2024, 1, 15)}
    articles = [{"title": "Article 1"}]

    storage = AsyncMock()
    storage.load = AsyncMock(return_value=json.dumps(articles))
    storage.load_markdown = Mock(return_value="### [Article 2](http://example.com)")

    logger = Mock()

    tracker = await load_existing_titles_from_storage(
        storage, target_dates, logger=logger
    )

    # ログが呼ばれたことを確認
    assert logger.debug.called
    assert tracker.count() == 2


@pytest.mark.asyncio
async def test_load_existing_titles_without_logger():
    """
    Given: logger=None
    When: load_existing_titles_from_storageを呼び出す
    Then: エラーなく動作
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(return_value="[]")
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(
        storage, target_dates, logger=None
    )

    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_io_error():
    """
    Given: storage.load()が例外を投げる
    When: load_existing_titles_from_storageを呼び出す
    Then: 例外をキャッチ、継続
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=OSError("Disk error"))
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    tracker = await load_existing_titles_from_storage(storage, target_dates)

    # エラーをキャッチして空のtrackerが返される
    assert tracker.count() == 0


@pytest.mark.asyncio
async def test_load_existing_titles_with_logger_file_not_found():
    """
    Given: logger引数ありでFileNotFoundError発生
    When: load_existing_titles_from_storageを呼び出す
    Then: logger.debugが呼ばれる（行226）
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=FileNotFoundError)
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    logger = Mock()

    tracker = await load_existing_titles_from_storage(
        storage, target_dates, logger=logger
    )

    # logger.debugが呼ばれたことを確認（行226, 252）
    assert logger.debug.called


@pytest.mark.asyncio
async def test_load_existing_titles_with_logger_json_decode_error():
    """
    Given: logger引数ありでJSONDecodeError発生
    When: load_existing_titles_from_storageを呼び出す
    Then: logger.warningが呼ばれる（行229）
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(return_value="invalid json")
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    logger = Mock()

    tracker = await load_existing_titles_from_storage(
        storage, target_dates, logger=logger
    )

    # logger.warningが呼ばれたことを確認（行229）
    assert logger.warning.called


@pytest.mark.asyncio
async def test_load_existing_titles_with_logger_io_error():
    """
    Given: logger引数ありでIOError発生
    When: load_existing_titles_from_storageを呼び出す
    Then: logger.debugが呼ばれる（行232）
    """
    target_dates = {date(2024, 1, 15)}

    storage = AsyncMock()
    storage.load = AsyncMock(side_effect=OSError("Disk error"))
    storage.load_markdown = Mock(side_effect=FileNotFoundError)

    logger = Mock()

    tracker = await load_existing_titles_from_storage(
        storage, target_dates, logger=logger
    )

    # logger.debugが呼ばれたことを確認（行232）
    assert logger.debug.called
