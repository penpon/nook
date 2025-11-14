# dedup テスト仕様書

## 概要
`nook/common/dedup.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- 日本語、特殊文字、装飾記号の正規化を網羅
- 空文字列、長文、Unicode正規化のエッジケース
- 重複検出ロジックの境界値テスト

---

## 1. TitleNormalizer.normalize メソッドのテスト

### 1.1 基本的な正規化

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | 通常のタイトル | 正常系 | "Test Article Title" | "test article title" | High | test_normalize_basic_title |
| 2 | 空文字列 | 境界値 | "" | "" | High | test_normalize_empty_string |
| 3 | 空白のみ | 境界値 | "   " | "" | High | test_normalize_whitespace_only |
| 4 | None入力 | 境界値 | None | "" | High | test_normalize_none_input |

### 1.2 Unicode正規化（NFKC）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 5 | 全角英数字→半角 | 正常系 | "ＡＢＣＤ１２３４" | "abcd1234" | High | test_normalize_fullwidth_to_halfwidth |
| 6 | 半角カナ→全角カナ | 正常系 | "ﾃｽﾄ" | "テスト".casefold() | High | test_normalize_halfwidth_kana |
| 7 | 合成文字の正規化 | 正常系 | "カ\u3099" (濁点分離) | "ガ".casefold() | Medium | test_normalize_composed_characters |
| 8 | 異体字の統一 | 正常系 | "葛󠄀" (異体字) | "葛".casefold() | Medium | test_normalize_variant_forms |

### 1.3 大文字小文字の無視（casefold）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 9 | 英大文字→小文字 | 正常系 | "HELLO WORLD" | "hello world" | High | test_normalize_uppercase_to_lowercase |
| 10 | 混在ケース | 正常系 | "HeLLo WoRLd" | "hello world" | High | test_normalize_mixed_case |
| 11 | ドイツ語ß | 正常系 | "Straße" | "strasse" | Medium | test_normalize_german_eszett |
| 12 | トルコ語İ | 正常系 | "İSTANBUL" | casefold結果 | Medium | test_normalize_turkish_i |

### 1.4 空白の正規化

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 13 | 連続空白の圧縮 | 正常系 | "hello    world" | "hello world" | High | test_normalize_multiple_spaces |
| 14 | 改行・タブの空白化 | 正常系 | "hello\n\tworld" | "hello world" | High | test_normalize_newlines_tabs |
| 15 | 先頭・末尾の空白削除 | 正常系 | "  hello world  " | "hello world" | High | test_normalize_trim_whitespace |
| 16 | 全角空白 | 正常系 | "hello　world" | "hello world" | High | test_normalize_fullwidth_space |

### 1.5 装飾記号の除去

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 17 | 先頭の【】除去 | 正常系 | "【重要】ニュース" | "ニュース".casefold() | High | test_normalize_remove_leading_brackets_kakko |
| 18 | 末尾の【】除去 | 正常系 | "ニュース【速報】" | "ニュース".casefold() | High | test_normalize_remove_trailing_brackets_kakko |
| 19 | 先頭の「」除去 | 正常系 | "「速報」ニュース" | "ニュース".casefold() | High | test_normalize_remove_leading_quotes_kagikakko |
| 20 | 末尾の「」除去 | 正常系 | "ニュース「速報」" | "ニュース".casefold() | High | test_normalize_remove_trailing_quotes_kagikakko |
| 21 | 先頭の『』除去 | 正常系 | "『速報』ニュース" | "ニュース".casefold() | Medium | test_normalize_remove_leading_quotes_nijukagikakko |
| 22 | 末尾の『』除去 | 正常系 | "ニュース『速報』" | "ニュース".casefold() | Medium | test_normalize_remove_trailing_quotes_nijukagikakko |
| 23 | 複数装飾の連続除去 | 正常系 | "【重要】「速報」ニュース『最新』" | "ニュース".casefold() | High | test_normalize_remove_multiple_decorations |
| 24 | 装飾のみのタイトル | 境界値 | "【速報】" | "" | High | test_normalize_decorations_only |

### 1.6 記号の正規化

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 25 | 連続感嘆符の圧縮 | 正常系 | "すごい!!!" | "すごい!".casefold() | High | test_normalize_multiple_exclamations |
| 26 | 全角感嘆符 | 正常系 | "すごい！！！" | "すごい!".casefold() | High | test_normalize_fullwidth_exclamations |
| 27 | 連続疑問符の圧縮 | 正常系 | "なぜ???" | "なぜ?".casefold() | High | test_normalize_multiple_questions |
| 28 | 全角疑問符 | 正常系 | "なぜ？？？" | "なぜ?".casefold() | High | test_normalize_fullwidth_questions |
| 29 | 連続チルダの圧縮 | 正常系 | "やった~~~" | "やった~".casefold() | High | test_normalize_multiple_tildes |
| 30 | 全角チルダ | 正常系 | "やった～～～" | "やった~".casefold() | High | test_normalize_fullwidth_tildes |
| 31 | 混在記号 | 正常系 | "すごい!？～" | "すごい!?~".casefold() | Medium | test_normalize_mixed_symbols |

### 1.7 複雑なケース

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 32 | 日本語タイトル | 正常系 | "最新ニュース" | "最新ニュース".casefold() | High | test_normalize_japanese_title |
| 33 | 英日混在 | 正常系 | "Apple新製品発表" | "apple新製品発表".casefold() | High | test_normalize_mixed_languages |
| 34 | 絵文字を含む | 正常系 | "ニュース😀🎉" | "ニュース😀🎉".casefold() | Medium | test_normalize_with_emojis |
| 35 | 超長文タイトル | 境界値 | 1000文字以上 | 正規化された結果 | Medium | test_normalize_very_long_title |
| 36 | 特殊Unicode文字 | 正常系 | "Test\u200B\u200C\u200D" (ゼロ幅文字) | 正規化結果 | Medium | test_normalize_zero_width_characters |

---

## 2. TitleNormalizer.are_duplicates メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 37 | 完全一致 | 正常系 | "Test", "Test" | True | High | test_are_duplicates_exact_match |
| 38 | 大文字小文字の違い | 正常系 | "Test", "test" | True | High | test_are_duplicates_case_difference |
| 39 | 空白の違い | 正常系 | "Test  Title", "Test Title" | True | High | test_are_duplicates_whitespace_difference |
| 40 | 装飾の違い | 正常系 | "【重要】Test", "Test" | True | High | test_are_duplicates_decoration_difference |
| 41 | 記号の違い | 正常系 | "Test!!!", "Test!" | True | High | test_are_duplicates_symbol_difference |
| 42 | 全く異なるタイトル | 正常系 | "Test A", "Test B" | False | High | test_are_duplicates_different_titles |
| 43 | 空文字列同士 | 境界値 | "", "" | True | High | test_are_duplicates_empty_strings |
| 44 | 片方が空文字列 | 境界値 | "Test", "" | False | High | test_are_duplicates_one_empty |
| 45 | None同士 | 境界値 | None, None | True | Medium | test_are_duplicates_both_none |
| 46 | 片方がNone | 境界値 | "Test", None | False | Medium | test_are_duplicates_one_none |
| 47 | 複雑な日本語の重複 | 正常系 | "【速報】最新ニュース！！！", "最新ニュース!" | True | High | test_are_duplicates_complex_japanese |

---

## 3. DedupTracker クラスのテスト

### 3.1 __init__ メソッド

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 48 | 初期化 | 正常系 | DedupTracker() | seen_normalized_titles=set(), title_mapping={} | High | test_dedup_tracker_init |

### 3.2 is_duplicate メソッド

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 49 | 新規タイトル | 正常系 | "Test Title" | (False, 正規化タイトル) | High | test_is_duplicate_new_title |
| 50 | 既存タイトル（重複） | 正常系 | add後に同じタイトル | (True, 正規化タイトル) | High | test_is_duplicate_existing_title |
| 51 | 大文字小文字違いで重複 | 正常系 | "Test"追加後に"test" | (True, 正規化タイトル) | High | test_is_duplicate_case_difference |
| 52 | 装飾違いで重複 | 正常系 | "Test"追加後に"【重要】Test" | (True, 正規化タイトル) | High | test_is_duplicate_decoration_difference |
| 53 | 空文字列 | 境界値 | "" | (False, "") | Medium | test_is_duplicate_empty_string |
| 54 | None入力 | 境界値 | None | (False, "") | Medium | test_is_duplicate_none_input |

### 3.3 add メソッド

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 55 | 新規タイトル追加 | 正常系 | "Test Title" | 正規化タイトルが返され、setに追加される | High | test_add_new_title |
| 56 | 重複タイトル追加 | 正常系 | 同じタイトルを2回 | 正規化タイトルが返され、setは変わらず | High | test_add_duplicate_title |
| 57 | title_mappingの更新 | 正常系 | 初回追加 | title_mappingに記録される | High | test_add_updates_title_mapping |
| 58 | title_mapping重複時は保持 | 正常系 | 同じ正規化タイトルで2回追加 | 最初の元タイトルが保持される | High | test_add_preserves_original_title_mapping |
| 59 | 空文字列追加 | 境界値 | "" | ""が返される | Medium | test_add_empty_string |
| 60 | None追加 | 境界値 | None | ""が返される | Medium | test_add_none |

### 3.4 get_original_title メソッド

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 61 | 存在する正規化タイトル | 正常系 | 追加済みの正規化タイトル | 元のタイトルが返される | High | test_get_original_title_existing |
| 62 | 存在しない正規化タイトル | 正常系 | 未追加のタイトル | Noneが返される | High | test_get_original_title_nonexistent |
| 63 | 空文字列 | 境界値 | "" | None（または""追加時の元タイトル） | Medium | test_get_original_title_empty_string |

### 3.5 count メソッド

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 64 | 初期状態 | 正常系 | 初期化直後 | 0が返される | High | test_count_initial_state |
| 65 | 追加後 | 正常系 | add()を複数回 | 追加した重複排除後の数が返される | High | test_count_after_additions |
| 66 | 重複追加後 | 正常系 | 同じタイトルを複数回add | カウントは増えない | High | test_count_after_duplicate_additions |

---

## 4. load_existing_titles_from_storage 関数のテスト

### 4.1 JSONファイル読み込み

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 67 | 正常なJSONファイル読み込み | 正常系 | 有効なJSON配列 | DedupTrackerにタイトルが登録される | High | test_load_existing_titles_from_json |
| 68 | 複数日付のJSON読み込み | 正常系 | 複数target_dates | すべての日付のJSONが読み込まれる | High | test_load_existing_titles_multiple_dates |
| 69 | JSONファイルが存在しない | 正常系 | FileNotFoundError | 空のDedupTrackerが返される | High | test_load_existing_titles_json_not_found |
| 70 | JSON解析エラー | 異常系 | 不正なJSON | JSONDecodeErrorをキャッチ、継続 | High | test_load_existing_titles_json_decode_error |
| 71 | 空のJSON配列 | 境界値 | [] | DedupTrackerのカウント=0 | Medium | test_load_existing_titles_empty_json_array |
| 72 | titleフィールドがない記事 | 正常系 | {"url": "..."} | titleがスキップされる | High | test_load_existing_titles_no_title_field |
| 73 | titleが空文字列 | 境界値 | {"title": ""} | スキップまたは空文字列として追加 | Medium | test_load_existing_titles_empty_title |

### 4.2 Markdownファイル読み込み

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 74 | Markdown形式の抽出 | 正常系 | "### [タイトル](URL)" | タイトルが抽出されて追加される | High | test_load_existing_titles_from_markdown |
| 75 | 複数記事のMarkdown | 正常系 | 複数の### [...]形式 | すべてのタイトルが抽出される | High | test_load_existing_titles_multiple_markdown_entries |
| 76 | Markdownファイルが存在しない | 正常系 | load_markdown()が例外 | エラーをキャッチ、継続 | High | test_load_existing_titles_markdown_not_found |
| 77 | 不正なMarkdown形式 | 正常系 | "### タイトル" (リンクなし) | マッチしない、スキップ | Medium | test_load_existing_titles_invalid_markdown_format |

### 4.3 統合・その他

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 78 | JSON + Markdown両方読み込み | 正常系 | 両方のファイルが存在 | 両方のタイトルが統合される | High | test_load_existing_titles_json_and_markdown |
| 79 | 空のtarget_dates | 境界値 | target_dates=set() | 空のDedupTrackerが返される | Medium | test_load_existing_titles_empty_target_dates |
| 80 | loggerあり | 正常系 | logger引数を渡す | ログ出力される | Medium | test_load_existing_titles_with_logger |
| 81 | loggerなし | 正常系 | logger=None | エラーなく動作 | Medium | test_load_existing_titles_without_logger |
| 82 | IOエラーハンドリング | 異常系 | storage.load()が例外 | 例外をキャッチ、継続 | High | test_load_existing_titles_io_error |

---

## カバレッジ目標

- **行カバレッジ**: 95%以上
- **分岐カバレッジ**: 95%以上
- **関数カバレッジ**: 100%

## テストデータ例

```python
# 正規化テスト用
test_titles = [
    ("【速報】最新ニュース！！！", "最新ニュース!"),
    ("ＨＥＬＬＯ　ＷＯＲＬＤ", "hello world"),
    ("  Test  Title  ", "test title"),
    ("「重要」ニュース『速報』", "ニュース"),
]

# DedupTracker用
sample_articles = [
    {"title": "Article 1", "url": "http://example.com/1"},
    {"title": "Article 2", "url": "http://example.com/2"},
    {"title": "【速報】Article 1", "url": "http://example.com/3"},  # 重複
]

# Markdown用
markdown_sample = """
### [Article 1](http://example.com/1)
Content here.

### [Article 2](http://example.com/2)
More content.
"""
```

## 注意事項

- Unicode正規化はNFKC形式
- casefold()で多言語対応
- エラーハンドリング時は処理を継続
- 非同期関数のテストは@pytest.mark.asyncioを使用
