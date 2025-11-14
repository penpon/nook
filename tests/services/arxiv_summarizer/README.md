# ArxivSummarizer テスト分割計画

## 現状の問題

**test_arxiv_summarizer.py**: 2377行、26セクション
- 1ファイルが大きすぎて保守困難
- 関連するテストがグループ化されていない
- 特定機能のテスト追加時に全体を読む必要がある

## 分割戦略

機能別に5ファイルに分割し、保守性と可読性を向上。

---

## 📁 分割後のファイル構成

### 1. `test_init_and_integration.py` (~300行)
**責務**: 初期化・統合テスト

テストセクション:
- ✅ 1. `__init__` メソッド
- ✅ 2-3. `collect` メソッド（正常系・異常系）
- ✅ 4. エラーハンドリング統合テスト
- ✅ 22. `run` メソッド

**テスト数**: ~10個

---

### 2. `test_fetch_and_retrieve.py` (~600行)
**責務**: データ取得・ダウンロード

テストセクション:
- ✅ 5. `_get_curated_paper_ids`
- ✅ 24. `_get_curated_paper_ids` 追加パターン
- ✅ 6. `_download_pdf_without_retry`
- ✅ 13. `_download_html_without_retry`
- ✅ 10. `_retrieve_paper_info` (arxiv.Search)
- ✅ 11. `_get_paper_date`

**テスト数**: ~25個

---

### 3. `test_extract_and_transform.py` (~600行)
**責務**: テキスト抽出・変換

テストセクション:
- ✅ 7. `_extract_from_pdf`
- ✅ 12. `_extract_from_html`
- ✅ 14. `_extract_body_text`
- ✅ 15. `_is_valid_body_line` (パラメータ化)
- ✅ 8. `_translate_to_japanese`

**テスト数**: ~20個

---

### 4. `test_format_and_serialize.py` (~500行)
**責務**: フォーマット・シリアライズ

テストセクション:
- ✅ 9. ユーティリティ関数 (パラメータ化)
- ✅ 16. `_summarize_paper_info`
- ✅ 18. `_serialize_papers`
- ✅ 19. `_paper_sort_key` (パラメータ化)
- ✅ 20. `_render_markdown`
- ✅ 21. `_parse_markdown` (パラメータ化)

**テスト数**: ~15個

---

### 5. `test_storage_and_ids.py` (~400行)
**責務**: ストレージ・ID管理

テストセクション:
- ✅ 17. `_get_processed_ids` (パラメータ化)
- ✅ 23. `_save_processed_ids_by_date`
- ✅ 25. `_load_existing_papers`
- ✅ 26. `_load_ids_from_file`

**テスト数**: ~10個

---

## 📊 分割のメリット

### 可読性
- **Before**: 2377行の巨大ファイル
- **After**: 平均480行の5ファイル（75%削減）
- ファイル名で機能が即座に理解可能

### 保守性
- 特定機能のテスト修正時に関連ファイルのみ開けばOK
- コンフリクト発生率の低減（複数人での並行作業）
- テスト追加時の適切なファイル選択が明確

### テスト実行速度
- 特定機能のテストのみ実行可能
- 並列実行の最適化（ファイル単位で分散）

---

## 🔧 実装方針

### 共通ヘッダー
全ファイルに以下を含む：
```python
"""
ArxivSummarizer - {機能名} のテスト

このファイルは元々 test_arxiv_summarizer.py の一部でしたが、
保守性向上のため機能別に分割されました。

関連ファイル:
- test_init_and_integration.py
- test_fetch_and_retrieve.py
- test_extract_and_transform.py
- test_format_and_serialize.py
- test_storage_and_ids.py
"""
```

### フィクスチャ
- conftest.pyの共通フィクスチャを活用
- ファイル固有のフィクスチャは各ファイル内に定義

### インポート
- 必要最小限のインポートのみ
- 共通のインポートパターンを統一

---

## ✅ 完了基準

1. ✅ 5つのファイルに分割完了
2. ✅ 全テストがpytest実行可能
3. ✅ テスト総数80個を維持
4. ✅ フィクスチャが正常動作
5. ✅ 元ファイルをバックアップ

---

## 📝 移行手順

1. バックアップ作成: `test_arxiv_summarizer.py.bak`
2. ディレクトリ作成: `tests/services/arxiv_summarizer/`
3. 5ファイル作成と内容移行
4. pytest実行確認
5. 元ファイル削除（バックアップ保持）
6. コミット・プッシュ

---

**作成日**: 2024-11-14
**ステータス**: 🟡 計画段階
