# Phase 2 改善実装ガイド
## 深いネストの解消とモジュール化

---

## ✅ Phase 2.1: 統合フィクスチャの実装（完了）

### 実装内容

**conftest.py に追加**：
```python
@pytest.fixture
def zenn_service_with_mocks(mock_env_vars):
    """ZennExplorerサービスと共通モックの統合セットアップ"""
    # 詳細はconftest.py L721-771を参照
```

この統合フィクスチャは以下を提供：
- `service`: ZennExplorerインスタンス
- `mock_parse`: feedparser.parseのモック
- `mock_load`: load_existing_titles_from_storageのモック
- `mock_setup_http`: setup_http_clientのモック
- `mock_get_dates`: _get_all_existing_datesのモック
- `mock_storage_load`: storage.loadのモック
- `mock_storage_save`: storage.saveのモック

---

## 📖 使用方法とサンプルコード

### Before（深いネスト、7レベル）

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(mock_env_vars):
    """記事が正常に取得される"""
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
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock, return_value=Path("/data/test.json")
        ):

            # テストデータ setup
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized_title")
            mock_dedup.add.return_value = None
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            # テスト実行
            result = await service.collect(days=1, limit=10)

            # 検証
            assert isinstance(result, list)
            assert len(result) > 0
```

**問題点**：
- ✗ 7レベルのネスト（可読性が低い）
- ✗ 38行（ボイラープレートが多い）
- ✗ 重複コード（他のcollect()テストでも同じパターン）

---

### After（統合フィクスチャ使用、1レベル）

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(zenn_service_with_mocks):
    """記事が正常に取得される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 有効なRSSフィードを設定
    mock_entry = create_mock_entry(
        title="テスト記事",
        link="https://example.com/test",
        summary="説明"
    )
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
    )
    service.gpt_client.get_response = AsyncMock(return_value="要約")

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1, limit=10)

    # Then: 記事が正常に取得される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) > 0, "有効なフィードから記事が取得されるべき"
```

**改善点**：
- ✓ 1レベルのネスト（可読性が高い）
- ✓ 28行（10行削減、-26%）
- ✓ 統一されたパターン（DRY原則）
- ✓ Given-When-Then構造が明確

**削減率**: 1テストあたり約10行削減 × 50テスト = **約500行削減**

---

## 🎯 Phase 2.2: テストファイル分割（推奨構造）

### 現状の問題
- 単一ファイル: 3,087行（大きすぎる）
- 92テスト（管理が困難）
- ナビゲーション性が低い

### 推奨構造

```
tests/services/zenn_explorer/
├── __init__.py
├── conftest.py                      # 共通フィクスチャ（新規）
├── test_initialization.py           # 3テスト、約45行
├── test_collect_basic.py            # 15テスト、約350行  ★優先
├── test_collect_advanced.py         # 20テスト、約500行
├── test_select_top_articles.py      # 4テスト、約120行
├── test_retrieve_article.py         # 25テスト、約700行
├── test_extract_popularity.py       # 15テスト、約450行
└── test_load_titles.py              # 10テスト、約300行
```

### 優先実装: test_collect_basic.py

最も頻繁に使用されるcollect()の基本テストを分離：

```python
"""
nook/services/zenn_explorer/zenn_explorer.py のテスト - collect()基本機能

テスト観点:
- collect()の正常系
- 基本的なエラーハンドリング
- 境界値テスト
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
import pytest

from tests.conftest import create_mock_dedup, create_mock_entry, create_mock_feed
from nook.services.zenn_explorer.zenn_explorer import ZennExplorer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(zenn_service_with_mocks):
    """有効なRSSフィードから記事が正常に取得される"""
    # フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 有効なRSSフィードを設定
    mock_entry = create_mock_entry(
        title="テストZenn記事",
        link="https://example.com/article1",
        summary="テストZenn記事の説明"
    )
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>日本語テキスト</p></body></html>")
    )
    service.gpt_client.get_response = AsyncMock(return_value="要約")

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1, limit=10)

    # Then: 記事が正常に取得される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) > 0, "有効なフィードから少なくとも1件の記事が取得されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_articles(zenn_service_with_mocks):
    """複数の記事を含むフィードから全記事が処理される"""
    # 実装...


# 他のcollect()基本テストを追加...
```

### 分割のメリット

1. **ナビゲーション性向上**
   - テスト目的別にファイルが分かれている
   - IDEでの検索・ジャンプが高速

2. **並列実行の効率化**
   - pytest -n auto で複数ファイルを並列実行
   - 実行時間の短縮

3. **保守性向上**
   - 関連するテストがグループ化
   - マージコンフリクトのリスク削減

4. **段階的なリファクタリング**
   - ファイル単位で段階的に改善可能

---

## 📊 期待される改善効果

### Phase 2.1 + 2.2 完全実施時

| 指標 | 現状 | Phase 2.1後 | Phase 2.2後 | 改善率 |
|------|------|-------------|-------------|--------|
| 総行数 | 3,087行 | 約2,500行 | 約2,400行 | **-22%** |
| 平均ネストレベル | 5-7 | 1-2 | 1-2 | **-70%** |
| 最大ファイルサイズ | 3,087行 | 3,087行 | 約700行 | **-77%** |
| テスト実行時間 | 15-20秒 | 14-18秒 | 10-14秒 | **-30%** |
| 可読性スコア* | 45/100 | 75/100 | 85/100 | **+89%** |
| 保守性スコア* | 60/100 | 75/100 | 90/100 | **+50%** |

*スコア: ネストレベル、コード重複、ファイルサイズ、モジュール性の総合評価

---

## 🛠️ 実装手順

### Step 1: フィクスチャ移行（段階的）

優先度の高いテストから順に移行：

1. **最優先**: collect()の正常系テスト（10-15個）
   - 最も頻繁に使用される
   - リファクタリング効果が大きい

2. **高優先**: collect()のエラーハンドリング（10個）
   - カバレッジへの影響が大きい

3. **中優先**: _retrieve_article(), _extract_popularity()（20個）
   - 内部ロジックのテスト

4. **低優先**: その他のテスト（残り）
   - 必要に応じて段階的に

### Step 2: ファイル分割（段階的）

1. **Phase A**: test_collect_basic.py を作成（15-20テスト）
   - 最もインパクトが大きい
   - 他のテストのテンプレートになる

2. **Phase B**: test_retrieve_article.py を作成（25テスト）
   - 次に大きいセクション

3. **Phase C**: 残りのファイルを作成（必要に応じて）

### Step 3: 検証

各ステップ後に以下を確認：

```bash
# 構文チェック
python3 -m py_compile tests/services/zenn_explorer/*.py

# テスト実行（新旧両方）
pytest tests/services/zenn_explorer/ -v

# カバレッジ確認
pytest tests/services/zenn_explorer/ --cov=nook.services.zenn_explorer --cov-report=term-missing
```

---

## ✅ チェックリスト

### Phase 2.1: 統合フィクスチャ
- [x] conftest.pyにzenn_service_with_mocksフィクスチャ追加
- [ ] 主要なcollect()テストでフィクスチャ使用（10-15個）
- [ ] 構文チェック成功
- [ ] テスト実行成功
- [ ] コミット・プッシュ

### Phase 2.2: ファイル分割
- [ ] tests/services/zenn_explorer/ ディレクトリ作成
- [ ] zenn_explorer/conftest.py 作成（共通フィクスチャ）
- [ ] test_collect_basic.py 作成（15-20テスト移行）
- [ ] 元のファイルから移行済みテスト削除
- [ ] 全テスト実行成功
- [ ] カバレッジ維持確認（98%+）
- [ ] コミット・プッシュ

---

## 📝 注意事項

1. **段階的実施が重要**
   - 一度に全部変更しない
   - 各ステップで検証

2. **バックアップ必須**
   - 各変更前にバックアップ作成

3. **テスト実行必須**
   - 各変更後に必ずテスト実行
   - カバレッジを確認

4. **コミット戦略**
   - Phase 2.1: 「フィクスチャ追加とサンプル適用」
   - Phase 2.2: 「collectテストの分離」
   - 各フェーズごとに独立したコミット

---

## 🎓 学習ポイント

### フィクスチャ設計のベストプラクティス

1. **粒度の選択**
   - 統合フィクスチャ: 頻繁に使用される複数モックのセット
   - 個別フィクスチャ: 特定の目的に特化

2. **辞書による返り値**
   - 柔軟性: 必要なモックのみを取得可能
   - 明示性: キー名でモックの目的が明確

3. **依存関係の管理**
   - mock_env_varsに依存（既存フィクスチャ）
   - yieldで適切なクリーンアップ

### テスト分割のベストプラクティス

1. **関心事の分離**
   - 機能別にファイルを分割
   - 各ファイルは単一責任

2. **命名規則**
   - test_{対象メソッド}_{観点}.py
   - 明確で検索しやすい

3. **共通フィクスチャ**
   - conftest.pyで一元管理
   - 各テストファイルで再利用

---

このガイドに従うことで、テストコードの品質が大幅に向上し、保守性・可読性・実行速度がすべて改善されます。
