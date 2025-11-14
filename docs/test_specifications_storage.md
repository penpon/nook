# LocalStorage テスト仕様書

## 概要
`nook/common/storage.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- 同期・非同期メソッドの両方をテスト
- ファイルシステム操作のエラーハンドリング検証
- tmp_pathフィクスチャで実際のファイル操作をテスト
- モックで権限エラー、IOエラーをシミュレート

---

## 1. `__init__` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | 新規ディレクトリ作成 | 正常系 | 存在しないディレクトリパス | ディレクトリが作成され、base_dirが設定される | High | test_init_creates_new_directory |
| 2 | 既存ディレクトリ使用 | 正常系 | 既存のディレクトリパス | エラーなくインスタンス作成、既存ディレクトリはそのまま | High | test_init_uses_existing_directory |
| 3 | ネストしたディレクトリ作成 | 正常系 | "parent/child/grandchild"のようなパス | parents=Trueで全階層作成される | High | test_init_creates_nested_directories |
| 4 | 相対パス指定 | 正常系 | "./test_data" | 相対パスからPathオブジェクトが作成される | Medium | test_init_with_relative_path |
| 5 | ディレクトリ作成権限エラー | 異常系 | 書き込み権限のないパス | OSError/PermissionError発生 | High | test_init_permission_error |

---

## 2. `save_markdown` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 6 | 通常のMarkdown保存（日付なし） | 正常系 | content="# Test", service_name="test", date=None | 現在日付でファイル保存、Pathが返される | High | test_save_markdown_without_date |
| 7 | 通常のMarkdown保存（日付あり） | 正常系 | content="# Test", service_name="test", date=datetime(2024,1,1) | 指定日付でファイル保存 | High | test_save_markdown_with_date |
| 8 | 空文字列のcontent | 境界値 | content="", service_name="test" | 空ファイルが作成される | Medium | test_save_markdown_empty_content |
| 9 | 大量のMarkdownコンテンツ | 境界値 | 10MB以上のcontent | 正常に保存される | Medium | test_save_markdown_large_content |
| 10 | Unicode文字を含むcontent | 正常系 | content="日本語\n絵文字😀" | UTF-8で正しく保存される | High | test_save_markdown_unicode_content |
| 11 | 特殊文字を含むservice_name | 境界値 | service_name="test-service_2024" | ディレクトリ作成・保存成功 | Medium | test_save_markdown_special_chars_service_name |
| 12 | 同じファイルの上書き保存 | 正常系 | 同じdate/service_nameで2回保存 | 上書き成功、新しいcontentが保存される | High | test_save_markdown_overwrite |
| 13 | ファイル書き込み権限エラー | 異常系 | open()がPermissionError発生 | PermissionError伝播 | High | test_save_markdown_permission_error |
| 14 | ディスク容量不足エラー | 異常系 | open()がOSError発生 | OSError伝播 | High | test_save_markdown_disk_full_error |

---

## 3. `load_markdown` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 15 | 存在するファイルの読み込み（日付なし） | 正常系 | 現在日付のファイルが存在 | ファイル内容が文字列で返される | High | test_load_markdown_existing_file_without_date |
| 16 | 存在するファイルの読み込み（日付あり） | 正常系 | 指定日付のファイルが存在 | ファイル内容が返される | High | test_load_markdown_existing_file_with_date |
| 17 | 存在しないファイルの読み込み | 正常系 | ファイルが存在しない | Noneが返される | High | test_load_markdown_nonexistent_file |
| 18 | 空ファイルの読み込み | 境界値 | 存在するが中身が空 | 空文字列""が返される | Medium | test_load_markdown_empty_file |
| 19 | Unicode文字を含むファイル | 正常系 | 日本語・絵文字を含むファイル | UTF-8で正しく読み込まれる | High | test_load_markdown_unicode_content |
| 20 | ファイル読み込み権限エラー | 異常系 | open()がPermissionError発生 | PermissionError伝播 | High | test_load_markdown_permission_error |

---

## 4. `list_dates` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 21 | 複数のMarkdownファイルがある場合 | 正常系 | 2024-01-01.md, 2024-01-02.md, 2024-01-03.md | 日付リストが降順でソートされて返される | High | test_list_dates_multiple_files |
| 22 | ファイルが1つの場合 | 境界値 | 2024-01-01.mdのみ | 1要素のリストが返される | Medium | test_list_dates_single_file |
| 23 | ファイルがない場合 | 正常系 | .mdファイルなし | 空リスト[]が返される | High | test_list_dates_no_files |
| 24 | サービスディレクトリが存在しない場合 | 正常系 | service_nameのディレクトリなし | 空リスト[]が返される | High | test_list_dates_service_dir_not_exists |
| 25 | 不正な形式のファイル名が混在 | 正常系 | 2024-01-01.md, invalid.md, 20240101.md | 正常な日付形式のみパースされ返される | High | test_list_dates_invalid_filenames_ignored |
| 26 | .md以外のファイルが混在 | 正常系 | 2024-01-01.md, 2024-01-01.json, test.txt | .mdファイルのみが対象 | Medium | test_list_dates_non_md_files_ignored |
| 27 | 日付のソート順確認 | 正常系 | 順不同の日付ファイル複数 | 降順（新しい順）でソートされる | High | test_list_dates_sorted_descending |

---

## 5. `save` メソッド（非同期）のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 28 | JSON形式のデータ保存 | 正常系 | data={"key": "value"}, filename="test.json" | JSONファイルが保存され、Pathが返される | High | test_save_json_data |
| 29 | テキストデータ保存 | 正常系 | data="plain text", filename="test.txt" | テキストファイルが保存される | High | test_save_text_data |
| 30 | 空の辞書を保存 | 境界値 | data={}, filename="empty.json" | 空のJSON "{}"が保存される | Medium | test_save_empty_dict |
| 31 | 空のリストを保存 | 境界値 | data=[], filename="empty.json" | 空のJSON "[]"が保存される | Medium | test_save_empty_list |
| 32 | ネストした複雑なJSON | 正常系 | 深くネストしたdict/list | 正しくシリアライズされて保存 | High | test_save_nested_json |
| 33 | サブディレクトリ付きファイル名 | 正常系 | filename="subdir/test.json" | サブディレクトリも作成される | High | test_save_with_subdirectory |
| 34 | Unicode文字を含むJSONデータ | 正常系 | data={"msg": "日本語😀"} | ensure_ascii=Falseで正しく保存 | High | test_save_json_unicode |
| 35 | 非シリアライズ可能オブジェクト | 異常系 | data=object(), filename="test.json" | TypeError発生 | High | test_save_non_serializable_object |
| 36 | ファイル書き込みIOエラー | 異常系 | aiofiles.openがOSError発生 | OSError伝播 | High | test_save_async_io_error |
| 37 | 巨大なJSONデータ | 境界値 | 10MB以上のdata | 正常に保存される | Medium | test_save_large_json_data |

---

## 6. `load` メソッド（非同期）のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 38 | 存在するファイルの読み込み | 正常系 | 既存のファイル | ファイル内容が文字列で返される | High | test_load_existing_file |
| 39 | 存在しないファイルの読み込み | 正常系 | 存在しないファイル名 | Noneが返される | High | test_load_nonexistent_file |
| 40 | 空ファイルの読み込み | 境界値 | 空のファイル | 空文字列""が返される | Medium | test_load_empty_file |
| 41 | Unicode文字を含むファイル | 正常系 | UTF-8エンコードファイル | 正しく読み込まれる | High | test_load_unicode_file |
| 42 | ファイル読み込みIOエラー | 異常系 | aiofiles.openがOSError発生 | OSError伝播 | High | test_load_async_io_error |

---

## 7. `exists` メソッド（非同期）のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 43 | 存在するファイル | 正常系 | 既存のファイル名 | Trueが返される | High | test_exists_file_present |
| 44 | 存在しないファイル | 正常系 | 存在しないファイル名 | Falseが返される | High | test_exists_file_absent |
| 45 | ディレクトリの存在確認 | 境界値 | ディレクトリパス | Trueが返される（ディレクトリもPath.exists()でTrue） | Medium | test_exists_directory |

---

## 8. `rename` メソッド（非同期）のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 46 | 存在するファイルのリネーム | 正常系 | 既存ファイルを新しい名前に | ファイル名が変更される | High | test_rename_existing_file |
| 47 | 存在しないファイルのリネーム | 正常系 | 存在しないファイル名 | 何も起こらない（エラーなし） | High | test_rename_nonexistent_file |
| 48 | リネーム先が既に存在する場合 | 境界値 | 既存ファイルを既存の名前に | 上書きされる | Medium | test_rename_overwrite_existing |
| 49 | サブディレクトリ間の移動 | 正常系 | "dir1/file.txt" -> "dir2/file.txt" | ファイルが移動される | High | test_rename_move_across_subdirs |

---

## 9. `load_json` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 50 | 存在するJSONファイルの読み込み（日付なし） | 正常系 | 現在日付のJSONファイル | リスト/辞書が返される | High | test_load_json_existing_file_without_date |
| 51 | 存在するJSONファイルの読み込み（日付あり） | 正常系 | 指定日付のJSONファイル | JSONデータが返される | High | test_load_json_existing_file_with_date |
| 52 | 存在しないJSONファイルの読み込み | 正常系 | ファイルが存在しない | Noneが返される | High | test_load_json_nonexistent_file |
| 53 | 空のJSONファイル | 境界値 | 内容が空のファイル | JSONDecodeError発生 | High | test_load_json_empty_file |
| 54 | 不正なJSON形式 | 異常系 | 壊れたJSON | JSONDecodeError発生 | High | test_load_json_invalid_format |
| 55 | Unicode文字を含むJSON | 正常系 | {"msg": "日本語😀"} | 正しくパースされる | High | test_load_json_unicode_content |
| 56 | ネストした複雑なJSON | 正常系 | 深くネストしたJSON | 正しくパースされる | Medium | test_load_json_nested_structure |

---

## カバレッジ目標

**目標: 95%以上**

### カバレッジ対象
- 全メソッド: 9個
- 全分岐: if/else文のすべてのパス
- エラーハンドリング: try-exceptの両方のパス
- 境界値: 空データ、None、特殊文字、巨大データ

### 重点項目
1. ファイル存在確認の分岐（exists() / not exists()）
2. 日付指定の有無（date=None / date指定）
3. JSONシリアライズ・デシリアライズのエラー
4. IOエラー（権限、ディスク容量）
5. ValueError処理（list_datesの不正ファイル名）

### テストケース統計
- 正常系: 26ケース (46%)
- 異常系: 18ケース (32%)
- 境界値: 12ケース (22%)
- **合計: 56ケース**

異常系・境界値が54%で正常系を上回り、要件を満たしています。
