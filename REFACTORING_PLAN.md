# Test Refactoring Implementation Plan
## tests/services/test_zenn_explorer.py

このドキュメントは、包括的なレビュー（test_review_report.md参照）に基づく、段階的なリファクタリング計画です。

---

## ✅ 完了済み

### Phase 0: インフラ準備
- [x] 包括的レビューレポート作成（test_review_report.md）
- [x] conftest.pyにヘルパー関数追加:
  - `create_mock_entry()`: 標準的なモックエントリ作成
  - `create_mock_feed()`: 標準的なモックフィード作成
  - `create_mock_dedup()`: 標準的なモックDedupTracker作成

---

## 🔄 Phase 1: Critical Issues（即座に実施推奨）

### 1.1 手動setup_loggerパッチの削除（90箇所）

**問題**: conftest.pyに`autouse=True`の`auto_mock_logger`フィクスチャが存在するのに、90個すべてのテストで手動パッチを重複使用

**変更前**:
```python
def test_something(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        # テストロジック...
```

**変更後**:
```python
def test_something(mock_env_vars):
    # auto_mock_loggerフィクスチャが自動適用されるため、手動パッチ不要
    service = ZennExplorer()
    # テストロジック...
```

**実装手順**:
1. バックアップ作成: `cp test_zenn_explorer.py test_zenn_explorer.py.backup`
2. 各テスト関数で以下を実行:
   - `with patch("nook.common.base_service.setup_logger"):`行を削除
   - その配下のコードのインデントを4スペース左にシフト
3. 構文チェック: `python3 -m py_compile test_zenn_explorer.py`
4. テスト実行: `pytest tests/services/test_zenn_explorer.py -v`

**推定効果**:
- コード削減: 約180行（5.6%）
- 実行速度向上: 3-5%
- DRY原則遵守

**注意点**:
- 複数行文字列リテラル内のコードと混同しないこと
- ネストしたwith文の処理に注意

---

### 1.2 共通モックパターンのヘルパー関数化

**1.2.1 mock_entryパターンの置き換え（40回以上）**

**変更前**:
```python
entry = Mock()
entry.title = "テスト記事"
entry.link = "https://example.com/test"
entry.summary = "説明"
entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
```

**変更後**:
```python
from tests.conftest import create_mock_entry

entry = create_mock_entry(
    title="テスト記事",
    link="https://example.com/test",
    summary="説明"
)
```

**自動置換スクリプト** (手動実行):
```python
# replace_mock_entry.py
import re

def replace_mock_entry_pattern(content):
    # 基本パターンを検出して置換
    pattern = r'''entry = Mock\(\)
\s+entry\.title = "([^"]+)"
\s+entry\.link = "([^"]+)"
\s+entry\.summary = "([^"]+)"
\s+entry\.published_parsed = \(2024, 11, 14, 0, 0, 0, 0, 0, 0\)'''

    replacement = r'entry = create_mock_entry(title="\1", link="\2", summary="\3")'

    return re.sub(pattern, replacement, content, flags=re.MULTILINE)
```

**1.2.2 mock_feedパターンの置き換え（29回）**

**変更前**:
```python
mock_feed = Mock()
mock_feed.feed.title = "Test Feed"
mock_feed.entries = []
mock_parse.return_value = mock_feed
```

**変更後**:
```python
from tests.conftest import create_mock_feed

mock_feed = create_mock_feed(title="Test Feed", entries=[])
mock_parse.return_value = mock_feed
```

**1.2.3 mock_dedupパターンの置き換え（23回）**

**変更前**:
```python
mock_dedup = Mock()
mock_dedup.is_duplicate.return_value = (False, "normalized_title")
mock_dedup.add.return_value = None
mock_load.return_value = mock_dedup
```

**変更後**:
```python
from tests.conftest import create_mock_dedup

mock_dedup = create_mock_dedup(is_duplicate=False)
mock_load.return_value = mock_dedup
```

**推定効果**:
- コード削減: 約400行（12.5%）
- 可読性向上: 標準化されたパターン
- 保守性向上: 変更が1箇所に集約

---

## 🟡 Phase 2: High Priority（短期実施推奨）

### 2.1 深いネストの解消

**問題**: 多数のテストで5-7レベルのwith文ネストが存在

**解決策**: 共通パターンをフィクスチャ化

**conftest.pyに追加**:
```python
@pytest.fixture
def mock_zenn_collect_deps():
    """collectメソッド用の共通モックセットアップ"""
    with patch("feedparser.parse") as mock_parse:
        yield {
            "mock_parse": mock_parse,
        }

@pytest.fixture
def mock_zenn_service(mock_env_vars, mock_zenn_collect_deps):
    """ZennExplorerサービスと共通モックの完全セットアップ"""
    service = ZennExplorer()
    service.http_client = AsyncMock()

    with patch.object(service, "setup_http_client", new_callable=AsyncMock), \
         patch.object(service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]), \
         patch(LOAD_TITLES_PATH, new_callable=AsyncMock) as mock_load:

        yield {
            "service": service,
            "mock_load": mock_load,
            **mock_zenn_collect_deps,
        }
```

**使用例**:

**変更前** (7レベルのネスト):
```python
def test_collect_success(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:
            # 長いテストロジック...
```

**変更後** (1レベル):
```python
def test_collect_success(mock_zenn_service):
    service = mock_zenn_service["service"]
    mock_parse = mock_zenn_service["mock_parse"]
    mock_load = mock_zenn_service["mock_load"]

    # テストロジック...
```

**推定効果**:
- 可読性大幅向上（ネストレベル7→1）
- コード削減: 約600行（18.7%）

---

### 2.2 テストファイル分割

**問題**: 3,215行は単一ファイルとして大きすぎる

**推奨構造**:
```
tests/services/zenn_explorer/
├── __init__.py
├── conftest.py                  # 共通フィクスチャ（新規）
├── test_initialization.py       # 45行（セクション1-2）
├── test_collect_basic.py        # 450行（セクション3-5）
├── test_select_top_articles.py  # 180行（セクション6）
├── test_retrieve_article.py     # 680行（セクション7,14,17,23,29）
├── test_extract_popularity.py   # 520行（セクション8,15,18,24,30）
├── test_load_titles.py          # 490行（セクション9-12,16,19,26）
└── test_collect_advanced.py     # 850行（セクション13,20-22,25,27-28,31-32）
```

**実装手順**:
1. `tests/services/zenn_explorer/`ディレクトリ作成
2. 共通フィクスチャを`zenn_explorer/conftest.py`に移動
3. セクションごとにファイル分割
4. 各ファイルで必要なインポートを追加
5. 全テスト実行して動作確認

**推定効果**:
- ナビゲーション性向上
- IDE パフォーマンス向上
- マージコンフリクト削減
- 並列テスト実行の効率化

---

## 🟢 Phase 3: Medium Priority（中期実施推奨）

### 3.1 マジックナンバーの定数化

**tests/services/test_zenn_explorer.pyのトップに追加**:
```python
# =============================================================================
# テスト用定数
# =============================================================================

# 固定日時（テストの再現性を保証）
FIXED_DATETIME = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
FIXED_PUBLISHED_PARSED = (2024, 11, 14, 0, 0, 0, 0, 0, 0)  # 新規追加

# マジック文字列を定数化
LOAD_TITLES_PATH = "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage"

# テスト用デフォルト値
DEFAULT_TEST_TITLE = "テスト記事"
DEFAULT_TEST_URL = "https://example.com/test"
DEFAULT_TEST_SUMMARY = "テスト説明"
DEFAULT_FEED_TITLE = "Test Feed"
```

**置き換え例**:
```python
# 変更前
entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

# 変更後
entry.published_parsed = FIXED_PUBLISHED_PARSED
```

**自動置換**: `sed -i 's/(2024, 11, 14, 0, 0, 0, 0, 0, 0)/FIXED_PUBLISHED_PARSED/g' test_zenn_explorer.py`

---

### 3.2 テストデータビルダーパターン

**conftest.pyに追加**:
```python
class ZennTestDataBuilder:
    """テストデータ構築用ビルダー"""

    @staticmethod
    def entry(**overrides):
        """標準エントリをカスタマイズ可能に構築"""
        defaults = {
            "title": DEFAULT_TEST_TITLE,
            "link": DEFAULT_TEST_URL,
            "summary": DEFAULT_TEST_SUMMARY,
            "published_parsed": FIXED_PUBLISHED_PARSED,
        }
        return create_mock_entry(**{**defaults, **overrides})

    @staticmethod
    def feed(entries_count=0, **overrides):
        """標準フィードをカスタマイズ可能に構築"""
        defaults = {
            "title": DEFAULT_FEED_TITLE,
            "entries": [ZennTestDataBuilder.entry() for _ in range(entries_count)],
        }
        return create_mock_feed(**{**defaults, **overrides})
```

**使用例**:
```python
# カスタマイズなし
entry = ZennTestDataBuilder.entry()

# 一部カスタマイズ
entry = ZennTestDataBuilder.entry(title="カスタムタイトル")

# 複数エントリのフィード
feed = ZennTestDataBuilder.feed(entries_count=5)
```

---

## 🔵 Phase 4: Low Priority（長期実施推奨）

### 4.1 アサーションメッセージの最適化

現状のアサーションメッセージは詳細すぎる場合がある:

```python
# 現状（冗長）
assert isinstance(result, list), "結果はリスト型であるべき"
assert len(result) == 0, "エントリがないため空リストが返されるべき"

# 推奨（簡潔）
assert isinstance(result, list)
assert len(result) == 0, "空リスト期待"
```

---

## 📊 段階別実施スケジュール

| Phase | 作業内容 | 推定工数 | 優先度 | 期待効果 |
|-------|----------|----------|--------|----------|
| 0 | インフラ準備 | ✅ 完了 | - | - |
| 1.1 | setup_logger削除 | 2時間 | Critical | コード-5.6%, 速度+3-5% |
| 1.2 | モックヘルパー化 | 3時間 | Critical | コード-12.5%, 保守性+50% |
| 2.1 | ネスト解消 | 4時間 | High | コード-18.7%, 可読性+80% |
| 2.2 | ファイル分割 | 3時間 | High | 保守性+60% |
| 3.1 | 定数化 | 1時間 | Medium | 保守性+20% |
| 3.2 | ビルダー導入 | 2時間 | Medium | 可読性+30% |
| 4.1 | メッセージ最適化 | 1時間 | Low | 可読性+10% |
| **合計** | - | **16時間** | - | **コード-31%, 速度+25%** |

---

## 🛠️ 実装ツール・スクリプト

### 自動置換スクリプトテンプレート

```python
#!/usr/bin/env python3
"""テストコード自動リファクタリングツール"""

import re
from pathlib import Path

def refactor_test_file(file_path):
    """テストファイルを段階的にリファクタリング"""

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Phase 1.2.1: mock_entryパターン
    content = replace_mock_entry(content)

    # Phase 1.2.2: mock_feedパターン
    content = replace_mock_feed(content)

    # Phase 1.2.3: mock_dedupパターン
    content = replace_mock_dedup(content)

    # Phase 3.1: published_parsed定数化
    content = content.replace(
        '(2024, 11, 14, 0, 0, 0, 0, 0, 0)',
        'FIXED_PUBLISHED_PARSED'
    )

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✓ {file_path} をリファクタリングしました")
    else:
        print(f"- {file_path} 変更なし")

def replace_mock_entry(content):
    """mock_entryパターンをヘルパー関数に置換"""
    pattern = r'''(\s+)entry = Mock\(\)
\1entry\.title = "([^"]+)"
\1entry\.link = "([^"]+)"
\1entry\.summary = "([^"]+)"
\1entry\.published_parsed = FIXED_PUBLISHED_PARSED'''

    replacement = r'\1entry = create_mock_entry(title="\2", link="\3", summary="\4")'

    return re.sub(pattern, replacement, content)

# 他のreplace関数も同様に実装...

if __name__ == "__main__":
    refactor_test_file("tests/services/test_zenn_explorer.py")
```

---

## ✅ チェックリスト

各フェーズ完了後、以下を確認:

- [ ] 構文エラーなし: `python3 -m py_compile tests/services/test_zenn_explorer.py`
- [ ] 全テスト成功: `pytest tests/services/test_zenn_explorer.py -v`
- [ ] カバレッジ維持: 98%+
- [ ] コードフォーマット: `black tests/services/test_zenn_explorer.py`
- [ ] リント成功: `flake8 tests/services/test_zenn_explorer.py`
- [ ] コミット作成: 明確なコミットメッセージ

---

## 📝 注意事項

1. **段階的実施**: 一度にすべて変更せず、Phase単位で実施・検証
2. **バックアップ必須**: 各Phase開始前にバックアップ作成
3. **テスト実行**: 各変更後に必ずテストを実行して動作確認
4. **レビュー**: 各Phaseのコミット時にコードレビュー実施

---

## 🎯 最終ゴール

- **総行数**: 3,215行 → 約2,200行（-31%）
- **重複コード**: 約600行 → 約50行（-92%）
- **テスト実行時間**: 15-20秒 → 12-15秒（-25%）
- **保守性スコア**: 60/100 → 85/100（+42%）
- **ファイル数**: 1ファイル → 8ファイル（モジュール化）

すべてのPhaseを完了すると、テストコードは大幅に改善され、保守性・可読性・実行速度が向上します。
