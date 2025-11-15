# テストコードリファクタリング実装ガイド

**対象ファイル**: tests/services/test_arxiv_summarizer.py
**作成日**: 2024-11-14

---

## 📋 概要

このガイドは、test_arxiv_summarizer.py の57箇所の重複コードを段階的に削減するための実装ガイドです。

**現状**:
- 全66テスト中、57テストで古いパターン使用（86%）
- フィクスチャ活用率: 14%
- 重複コード: 約313行

**目標**:
- フィクスチャ活用率: 100%
- 重複コード削減: 313行
- コード削減率: 約12%

---

## 🔧 リファクタリングパターン

### パターン1: arxiv_serviceフィクスチャの適用（57箇所）

#### Before (古いパターン)
```python
@pytest.mark.unit
async def test_example(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer
        service = ArxivSummarizer()
        # テストロジック
        result = await service.some_method()
        assert result == expected
```

#### After (新しいパターン)
```python
@pytest.mark.unit
async def test_example(arxiv_service):
    # Given: (必要に応じてモック設定)

    # When
    result = await arxiv_service.some_method()

    # Then
    assert result == expected
```

#### 変更手順
1. 関数シグネチャ: `mock_env_vars` → `arxiv_service`
2. `with patch("nook.common.base_service.setup_logger"):` 行を削除
3. `from nook...import ArxivSummarizer` 行を削除（既にファイル冒頭でインポート済み）
4. `service = ArxivSummarizer()` 行を削除
5. `service` → `arxiv_service` に置換（テストロジック内）
6. Given-When-Thenコメント追加（可読性向上）

---

### パターン2: test_dateフィクスチャの適用（32箇所）

#### Before
```python
result = await service._get_processed_ids(date(2024, 1, 1))
```

#### After
```python
async def test_example(arxiv_service, test_date):
    result = await arxiv_service._get_processed_ids(test_date)
```

#### 変更手順
1. 関数シグネチャに `test_date` 追加
2. `date(2024, 1, 1)` → `test_date` に置換
3. `datetime(2024, 1, 1, ...)` → `test_datetime` に置換（該当する場合）

---

### パターン3: paper_info_factoryの適用（25箇所）

#### Before
```python
paper = PaperInfo(
    title="Test Paper",
    abstract="Abstract",
    url="http://arxiv.org/abs/2301.00001",
    contents="Contents",
    published_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
)
paper.summary = "Summary"
```

#### After
```python
def test_example(arxiv_service, paper_info_factory):
    paper = paper_info_factory(
        title="Test Paper",
        abstract="Abstract",
        summary="Summary",
    )
```

#### 変更手順
1. 関数シグネチャに `paper_info_factory` 追加
2. 手動作成コードをファクトリー呼び出しに置換
3. デフォルト値を活用（url, published_atは省略可能）

---

### パターン4: arxiv_helperの適用（60箇所）

#### Before
```python
result = service._is_valid_body_line(line, min_length=80)
url = "https://arxiv.org/pdf/2301.00001"
```

#### After
```python
def test_example(arxiv_service, arxiv_helper):
    result = arxiv_service._is_valid_body_line(
        line,
        min_length=arxiv_helper.DEFAULT_MIN_LINE_LENGTH
    )
    url = f"https://arxiv.org/pdf/{arxiv_helper.DEFAULT_ARXIV_ID}"
```

#### 変更手順
1. 関数シグネチャに `arxiv_helper` 追加
2. マジックナンバーを定数に置換:
   - `80` → `arxiv_helper.DEFAULT_MIN_LINE_LENGTH`
   - `"2301.00001"` → `arxiv_helper.DEFAULT_ARXIV_ID`
3. モック作成を1行に簡略化:
   ```python
   # Before (3行)
   mock_client = AsyncMock()
   mock_client.__aenter__.return_value = mock_client
   mock_client.__aexit__.return_value = None

   # After (1行)
   mock_client = arxiv_helper.create_mock_http_client()
   ```

---

## 📝 セクション別適用リスト

### 優先度1（即座対応）: 高頻度使用セクション

#### ✅ 完了済み
- セクション1: `__init__` メソッド（1テスト）
- セクション6: `_download_pdf_without_retry`（1テスト）
- セクション8: `_translate_to_japanese`（1テスト）✅
- セクション10: `_retrieve_paper_info`（1テスト）
- セクション15: `_is_valid_body_line`（1テスト）
- セクション17: `_get_processed_ids`（1テスト）
- セクション18: `_serialize_papers`（1テスト）

#### 🔄 未完了（優先対応）
以下のセクションに古いパターンが残っています：

1. **セクション2-4**: collect メソッド（7テスト）
   - `test_collect_success_with_papers`
   - `test_collect_with_multiple_categories`
   - `test_collect_network_error`
   - `test_collect_invalid_xml`
   - `test_collect_gpt_api_error`
   - `test_full_workflow_collect_and_save`
   - `test_run_method`

2. **セクション5**: _get_curated_paper_ids（7テスト）
   - `test_get_curated_paper_ids_success`
   - `test_get_curated_paper_ids_404_error`
   - `test_get_curated_paper_ids_redirect`
   - `test_get_curated_paper_ids_fallback_to_top_page`
   - `test_get_curated_paper_ids_empty_result`
   - `test_get_curated_paper_ids_with_duplicates`
   - `test_get_curated_paper_ids_filters_processed_ids`

3. **セクション6**: _download_pdf_without_retry（3テスト）
   - `test_download_pdf_timeout`
   - `test_download_pdf_404_error`
   - `test_download_pdf_500_error`

4. **セクション7**: _extract_from_pdf（5テスト）
   - `test_extract_from_pdf_success`
   - `test_extract_from_pdf_empty_content`
   - `test_extract_from_pdf_corrupted`
   - `test_extract_from_pdf_download_error`
   - `test_extract_from_pdf_filters_short_lines`

5. **セクション8**: _translate_to_japanese（2テスト）
   - `test_translate_to_japanese_gpt_error`
   - `test_translate_to_japanese_empty_text`

6. **セクション9**: ユーティリティ関数（3テスト）
   - ✅ 既にパラメータ化済み（良好）

7. **セクション10**: _retrieve_paper_info（3テスト）
   - `test_retrieve_paper_info_no_results`
   - `test_retrieve_paper_info_api_error`
   - `test_retrieve_paper_info_with_fallback_to_abstract`

8. **セクション11**: _get_paper_date（3テスト）
   - `test_get_paper_date_success`
   - `test_get_paper_date_no_results`
   - `test_get_paper_date_api_error`

9. **セクション12-14**: HTML/本文抽出（10テスト）
   - 全テストで古いパターン使用

10. **セクション16**: _summarize_paper_info（3テスト）
    - 全テストで古いパターン使用

11. **セクション18-21**: シリアライズ・Markdown（5テスト）
    - 一部で古いパターン使用

12. **セクション22-26**: ストレージ・ID管理（8テスト）
    - 全テストで古いパターン使用

---

## 🎯 実装戦略

### アプローチ1: セクション単位で順次リファクタリング
**推奨**: 大規模な変更を管理しやすい単位に分割

```bash
# 例: セクション5を一括リファクタリング
1. セクション5の全7テストを修正
2. pytest実行して動作確認
3. コミット（"refactor: セクション5のフィクスチャ適用"）
4. 次のセクションへ
```

### アプローチ2: パターン単位で横断的にリファクタリング
**推奨**: 同じパターンを一度にすべて修正

```bash
# 例: パターン1（arxiv_service）を全テストに適用
1. 全57箇所でパターン1を適用
2. pytest実行
3. コミット（"refactor: arxiv_serviceフィクスチャを全テストに適用"）
```

---

## ✅ 実装チェックリスト

### Phase 1: 基礎整備
- [x] ファイル冒頭のインポート整理
- [x] レビュー報告書作成（REVIEW_REPORT_2.md）
- [x] 実装ガイド作成（本ファイル）

### Phase 2: パターン適用（セクション別）
- [x] セクション1: `__init__`（1テスト）
- [x] セクション6: `_download_pdf_without_retry`（部分）
- [x] セクション8: `_translate_to_japanese`（部分）
- [x] セクション10: `_retrieve_paper_info`（部分）
- [x] セクション15: `_is_valid_body_line`（完了）
- [x] セクション17: `_get_processed_ids`（完了）
- [x] セクション18: `_serialize_papers`（部分）
- [ ] セクション2-4: collect メソッド（7テスト）
- [ ] セクション5: _get_curated_paper_ids（7テスト）
- [ ] セクション6-7: PDF処理（8テスト）
- [ ] セクション8: 翻訳（残り2テスト）
- [ ] セクション10-11: 論文取得（6テスト）
- [ ] セクション12-14: HTML/本文（10テスト）
- [ ] セクション16: 要約（3テスト）
- [ ] セクション19-21: Markdown処理（5テスト）
- [ ] セクション22-26: ストレージ（8テスト）

### Phase 3: 最終確認
- [ ] pytest実行（全テスト合格）
- [ ] カバレッジ測定（95%以上維持）
- [ ] コードレビュー
- [ ] ドキュメント更新

---

## 🚀 クイックスタート

### 1. 単一テストの修正例
```bash
# 1. テストを特定
grep -n "def test_translate_to_japanese_gpt_error" tests/services/test_arxiv_summarizer.py

# 2. エディタで開いて修正（パターン1を適用）
# Before: async def test_translate_to_japanese_gpt_error(mock_env_vars):
# After:  async def test_translate_to_japanese_gpt_error(arxiv_service):

# 3. テスト実行
pytest tests/services/test_arxiv_summarizer.py::test_translate_to_japanese_gpt_error -v

# 4. 成功したらコミット
git add tests/services/test_arxiv_summarizer.py
git commit -m "refactor: test_translate_to_japanese_gpt_errorのフィクスチャ適用"
```

### 2. セクション一括修正例
```bash
# セクション8（3テスト）を一括修正
vim tests/services/test_arxiv_summarizer.py +776

# セクション8のみテスト実行
pytest tests/services/test_arxiv_summarizer.py -k "translate_to_japanese" -v

# コミット
git add tests/services/test_arxiv_summarizer.py
git commit -m "refactor: セクション8(_translate_to_japanese)のフィクスチャ全適用"
```

---

## 📊 進捗トラッキング

| セクション | テスト数 | 完了 | 残り | 進捗率 |
|-----------|---------|------|------|--------|
| 1. init | 1 | 1 | 0 | 100% |
| 2-4. collect | 7 | 0 | 7 | 0% |
| 5. curated_ids | 7 | 0 | 7 | 0% |
| 6. download_pdf | 4 | 1 | 3 | 25% |
| 7. extract_pdf | 5 | 0 | 5 | 0% |
| 8. translate | 3 | 1 | 2 | 33% |
| 9. utilities | 3 | 3 | 0 | 100% |
| 10. retrieve | 4 | 1 | 3 | 25% |
| 11. paper_date | 3 | 0 | 3 | 0% |
| 12-14. html/body | 10 | 0 | 10 | 0% |
| 15. valid_line | 1 | 1 | 0 | 100% |
| 16. summarize | 3 | 0 | 3 | 0% |
| 17. processed_ids | 1 | 1 | 0 | 100% |
| 18. serialize | 2 | 1 | 1 | 50% |
| 19-21. markdown | 5 | 1 | 4 | 20% |
| 22-26. storage | 8 | 0 | 8 | 0% |
| **合計** | **66** | **11** | **55** | **17%** |

---

## 💡 ヒント

### エラーハンドリング
- フィクスチャ適用後に ImportError が出た場合:
  ```python
  # ファイル冒頭のインポートを確認
  from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer
  ```

### テスト実行
```bash
# 特定テストのみ実行
pytest tests/services/test_arxiv_summarizer.py::test_名前 -v

# セクションのみ実行（キーワードマッチ）
pytest tests/services/test_arxiv_summarizer.py -k "translate" -v

# 全テスト実行（最終確認）
pytest tests/services/test_arxiv_summarizer.py -v
```

---

**次のステップ**: セクション2-4（collectメソッド7テスト）の修正から開始推奨
