# テスト改善タスク - 引き継ぎドキュメント

## 📊 現状サマリー

### カバレッジ測定結果（2025-11-18実施）
- **総行数**: 4,630行
- **カバー済み**: 4,223行
- **カバレッジ率**: **89.7%** ✅ (目標80%達成)
- **総テスト数**: 1,549個

### テスト実行結果
- テスト実行: pytest-xdist使用（16並列）
- 実行時間: 約10分
- 状態: 一部失敗あり（要確認）

---

## 🎯 実施すべきタスク

### タスク1: 統合テストの追加（優先度: 🔴 最高）

**目標**: 30-50個の統合テストを追加
**所要時間**: 2-3日

#### 対象サービス（全11種類）
1. reddit_explorer
2. hacker_news
3. arxiv_summarizer
4. github_trending
5. tech_feed
6. business_feed
7. zenn_explorer
8. qiita_explorer
9. note_explorer
10. fourchan_explorer
11. fivechan_explorer

#### テンプレート

```python
# tests/services/test_{service}_integration.py

import pytest
from datetime import date
from pathlib import Path

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_{service}_to_storage(tmp_path, mock_env_vars):
    """
    Given: サービスインスタンス
    When: collect()を実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功
    """
    from nook.services.{service}.{service} import {ServiceClass}

    # 1. サービス初期化
    service = {ServiceClass}(storage_dir=str(tmp_path))

    # 2. モック設定（外部API）
    with (
        patch.object(service.http_client, 'get') as mock_get,
        patch.object(service.gpt_client, 'get_response') as mock_gpt
    ):
        # HTTPレスポンスモック
        mock_get.return_value = Mock(
            text="<html>Test content</html>",
            status_code=200
        )

        # GPT要約モック
        mock_gpt.return_value = "テスト要約"

        # 3. データ収集実行
        result = await service.collect()

        # 4. 検証: データ取得確認
        assert len(result) > 0, "データが取得できていません"
        assert result[0]["title"] is not None

        # 5. 検証: GPT要約確認
        assert result[0]["summary"] is not None
        assert result[0]["summary"] == "テスト要約"

        # 6. 検証: Storage保存確認
        saved_data = await service.storage.load(date.today())
        assert len(saved_data) == len(result)
        assert saved_data[0]["title"] == result[0]["title"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_{service}(tmp_path, mock_env_vars):
    """
    Given: ネットワークエラーが発生する状況
    When: collect()を実行
    Then: 適切なエラーハンドリングがされる
    """
    from nook.services.{service}.{service} import {ServiceClass}

    service = {ServiceClass}(storage_dir=str(tmp_path))

    with patch.object(service.http_client, 'get') as mock_get:
        # ネットワークエラーをシミュレート
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        # エラーハンドリング確認
        with pytest.raises(ServiceException):
            await service.collect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_{service}(tmp_path, mock_env_vars):
    """
    Given: GPT APIエラーが発生する状況
    When: collect()を実行
    Then: フォールバック処理が動作
    """
    from nook.services.{service}.{service} import {ServiceClass}

    service = {ServiceClass}(storage_dir=str(tmp_path))

    with (
        patch.object(service.http_client, 'get') as mock_get,
        patch.object(service.gpt_client, 'get_response') as mock_gpt
    ):
        mock_get.return_value = Mock(text="<html>Test</html>", status_code=200)

        # GPT APIエラーをシミュレート
        mock_gpt.side_effect = Exception("API rate limit exceeded")

        # フォールバック動作確認
        result = await service.collect()

        # 要約なしでもデータは取得されるべき
        assert len(result) > 0
        # summaryはNoneまたはエラーメッセージ
```

#### 実装手順

1. **Phase 1**: 主要3サービスで実装・検証
   - reddit_explorer
   - hacker_news
   - fivechan_explorer

2. **Phase 2**: 残り8サービスに展開

3. **Phase 3**: 共通モジュールの統合テスト
   - base_service.py
   - gpt_client.py
   - storage.py

---

### タスク2: E2Eテストの追加（優先度: 🟡 高）

**目標**: 15-20個のE2Eテストを追加
**所要時間**: 1-2日

#### テンプレート

```python
# tests/e2e/test_api_endpoints.py

import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_to_frontend_reddit_explorer(test_client: AsyncClient):
    """
    Given: Redditデータが保存されている
    When: /api/content/reddit_explorerにアクセス
    Then: フロントエンド表示用の正しいJSONが返る
    """
    # API呼び出し
    response = await test_client.get("/api/content/reddit_explorer")

    # ステータス確認
    assert response.status_code == 200

    # レスポンス形式確認
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

    # フロントエンド表示に必要なフィールド確認
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "title" in item
        assert "url" in item
        assert "summary" in item
        assert "published_at" in item


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_all_sources_endpoint(test_client: AsyncClient):
    """
    Given: 複数ソースのデータ
    When: /api/content/allにアクセス
    Then: 全ソースのデータが統合されて返る
    """
    response = await test_client.get("/api/content/all")

    assert response.status_code == 200
    data = response.json()

    # 全11サービスのデータが含まれる
    assert len(data["items"]) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_error_handling_invalid_source(test_client: AsyncClient):
    """
    Given: 存在しないソース名
    When: APIにアクセス
    Then: 404エラーが返る
    """
    response = await test_client.get("/api/content/invalid_source")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
```

---

### タスク3: パフォーマンステストの標準化（優先度: 🟢 中）

**目標**: 5chanのベストプラクティスを他サービスに適用
**所要時間**: 1日

#### 5chanのベストプラクティス

```python
# tests/services/test_fivechan_explorer.py より抜粋

# パフォーマンス制約定数
MAX_RESPONSE_SIZE_MB = 10
MAX_PROCESSING_TIME_SECONDS = 1.0
MAX_MEMORY_USAGE_MB = 50

@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_efficiency_large_dataset(mock_env_vars):
    """メモリ使用量が制限内であることを確認"""
    import tracemalloc

    tracemalloc.start()

    # 大量データ処理
    service = FiveChanExplorer()
    await service.collect()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 50MB以内
    assert peak < MAX_MEMORY_USAGE_MB * 1024 * 1024


@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_timeout_handling(mock_env_vars):
    """ネットワークタイムアウトが適切に処理される"""
    service = FiveChanExplorer()

    with patch.object(service.http_client, 'get') as mock_get:
        mock_get.side_effect = asyncio.TimeoutError()

        with pytest.raises(ServiceException):
            await service.collect()
```

#### 適用対象サービス
- arxiv_summarizer（大容量PDF処理）
- github_trending（大量リポジトリ処理）
- note_explorer（大量記事処理）

---

### タスク4: テストの整理（優先度: 🟢 中）

**目標**: テストマーカーの統一と遅いテストの分離
**所要時間**: 半日

#### pytest.ini設定

```ini
# pytest.ini または pyproject.toml

[tool.pytest.ini_options]
markers = [
    "unit: 単体テスト（高速）",
    "integration: 統合テスト（中速）",
    "e2e: E2Eテスト（低速）",
    "slow: 遅いテスト（5秒以上）",
    "security: セキュリティテスト",
    "performance: パフォーマンステスト",
]

# デフォルトでは遅いテストをスキップ
addopts = """
    -v
    --tb=short
    -m "not slow"
"""
```

#### マーカー追加作業

```bash
# 既存テストにマーカーを追加
# 1. 単体テスト（既存のほとんど）
@pytest.mark.unit

# 2. 遅いテスト（5秒以上）
@pytest.mark.slow

# 3. セキュリティテスト（5chanのDoS/XSS等）
@pytest.mark.security

# 4. パフォーマンステスト
@pytest.mark.performance
```

#### 実行例

```bash
# 高速テストのみ実行（CI用）
pytest -m "unit"

# 統合テストのみ実行
pytest -m "integration"

# 遅いテストを含めて全実行
pytest -m ""

# セキュリティテストのみ
pytest -m "security"
```

---

### タスク5: モックの活用（優先度: 🟢 中）

**目標**: 外部API呼び出しのモック化でテスト高速化
**所要時間**: 1日

#### モック化対象

1. **OpenAI API (gpt_client.py)**
   ```python
   @pytest.fixture
   def mock_gpt_response():
       return "これはテスト用の要約です"

   @pytest.fixture(autouse=True)
   def mock_gpt_client(mock_gpt_response):
       with patch('nook.common.gpt_client.GPTClient.get_response') as mock:
           mock.return_value = mock_gpt_response
           yield mock
   ```

2. **Reddit API (reddit_explorer)**
   ```python
   @pytest.fixture
   def mock_reddit_api():
       with patch('asyncpraw.Reddit') as mock:
           # モックデータ返却
           yield mock
   ```

3. **HTTP requests (http_client.py)**
   ```python
   @pytest.fixture
   def mock_http_client():
       with patch('httpx.AsyncClient.get') as mock:
           mock.return_value = Mock(
               text="<html>Test</html>",
               status_code=200
           )
           yield mock
   ```

---

## 📁 ファイル構成

### 新規作成ファイル

```
tests/
├── e2e/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_api_endpoints.py       # NEW: E2Eテスト
│
├── integration/
│   ├── __init__.py
│   ├── conftest.py                 # NEW: 統合テスト用fixture
│   └── test_services_integration.py # NEW: サービス統合テスト
│
└── services/
    ├── test_reddit_explorer_integration.py   # NEW
    ├── test_hacker_news_integration.py       # NEW
    ├── test_arxiv_integration.py             # NEW
    ... (各サービスごと)
```

### 更新ファイル

```
tests/
├── conftest.py                     # UPDATE: グローバルfixture追加
└── pytest.ini                      # UPDATE: マーカー設定
```

---

## 🔧 必要な依存関係

```toml
# pyproject.toml
[tool.uv.dev-dependencies]
pytest = "^9.0.1"
pytest-asyncio = "^1.3.0"
pytest-cov = "^7.0.0"
pytest-xdist = "^3.8.0"
pytest-mock = "^3.15.1"
pytest-timeout = "^2.4.0"
httpx = "^0.24.0"
respx = "^0.22.0"  # HTTPモック用
```

---

## ✅ 検証基準

### テスト追加後の目標

1. **統合テストカバレッジ**
   - 全11サービス × 3テスト = 33個以上

2. **E2Eテストカバレッジ**
   - 全APIエンドポイント網羅: 15個以上

3. **総合カバレッジ**
   - 維持: 89%以上

4. **CI/CD統合**
   - GitHub Actionsで自動実行
   - PR時に統合テスト必須

---

## 📝 注意事項

### テスト失敗について
現在のテスト実行で一部失敗がありますが、以下を確認してください：

```bash
# 失敗テストの詳細確認
source .venv/bin/activate
python -m pytest tests/ -v --tb=long | grep FAILED
```

### モック使用時の注意
- 外部API依存を減らすため、できるだけモックを使用
- ただし、統合テストでは一部実際のAPIも使用（環境変数で切り替え）

### パフォーマンステスト実行
```bash
# メモリプロファイリング有効化
python -m pytest tests/ -v -m "performance" --tb=short
```

---

## 🚀 次のセッション開始プロンプト

次のセッションで以下のプロンプトを使用してください：

```
以下のテスト改善タスクを実施します。

前回の調査結果:
- 現在のカバレッジ: 89.7%（4,223/4,630行）
- 総テスト数: 1,549個
- 問題: 統合テスト/E2Eテストが不足

実施タスク:
1. 統合テストを30-50個追加（優先度: 最高）
2. E2Eテストを15-20個追加（優先度: 高）
3. パフォーマンステストの標準化（優先度: 中）
4. テストマーカーの整理（優先度: 中）
5. モックの活用（優先度: 中）

引き継ぎドキュメント: docs/TEST_IMPROVEMENT_HANDOFF.md

Phase 1として、まず主要3サービス（reddit_explorer, hacker_news, fivechan_explorer）の統合テストを実装してください。

テンプレートは引き継ぎドキュメントを参照してください。
```

---

**作成日**: 2025-11-18
**作成者**: Claude Code (テストカバレッジ調査)
**カバレッジ測定日**: 2025-11-18
