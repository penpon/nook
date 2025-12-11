# TrendRadar 連携実装計画

## 概要

TrendRadar MCP サーバー経由で中国系プラットフォーム（知乎）のホットトピックを取得し、nook に統合する。

| 項目 | 決定事項 |
|------|---------|
| 方式 | A（TrendRadar MCP 経由） |
| 表示形式 | TrendRadar 形式 + GPT 要約 |
| グループ名 | `TrendRadar` |
| 初期スコープ | 知乎（Zhihu）のみで PoC |

---

## ⚠️ 作業ルール

- **Git Worktree**: 必ず worktree で作成したブランチ内で作業
- **TDD RGR サイクル**: Red → Green → Refactor の順で実装
- **実コストテスト除外**: OpenAPI 等の実コストが発生するテストは実装しない（モック使用）

---

## Stream A: TrendRadar MCP クライアント基盤

### 目的
TrendRadar MCP サーバーと通信するための基盤クライアントを実装する。

### 対象ファイル
- `nook/services/explorers/trendradar/__init__.py` [NEW]
- `nook/services/explorers/trendradar/trendradar_client.py` [NEW]
- `tests/services/explorers/trendradar/__init__.py` [NEW]
- `tests/services/explorers/trendradar/test_trendradar_client.py` [NEW]

### TDD タスク

#### Red: 失敗するテストを書く
```python
# tests/services/explorers/trendradar/test_trendradar_client.py
class TestTrendRadarClient:
    def test_client_initialization(self):
        """クライアントが正しく初期化できること"""
    
    def test_get_latest_news_returns_list(self):
        """get_latest_news がニュースリストを返すこと（モック使用）"""
    
    def test_get_latest_news_with_platform_filter(self):
        """プラットフォーム指定でフィルタできること"""
    
    def test_connection_error_handling(self):
        """接続エラー時に適切な例外が発生すること"""
```

#### Green: テストを通す最小実装
```python
# nook/services/explorers/trendradar/trendradar_client.py
class TrendRadarClient:
    """TrendRadar MCP サーバーへの HTTP クライアント"""
    
    def __init__(self, base_url: str = "http://localhost:3333/mcp"):
        self.base_url = base_url
    
    async def get_latest_news(self, platform: str, limit: int = 50) -> list[dict]:
        """指定プラットフォームの最新ニュースを取得"""
        pass
    
    async def health_check(self) -> bool:
        """サーバー接続確認"""
        pass
```

#### Refactor
- エラーハンドリングの共通化
- 型定義の追加

---

## Stream B: Zhihu Explorer 実装

### 目的
知乎（Zhihu）のデータを取得し、nook 形式で保存する Explorer を実装する。

### 対象ファイル
- `nook/services/explorers/trendradar/zhihu_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_zhihu_explorer.py` [NEW]

### TDD タスク

#### Red: 失敗するテストを書く
```python
# tests/services/explorers/trendradar/test_zhihu_explorer.py
class TestZhihuExplorer:
    def test_explorer_initialization(self):
        """Explorer が正しく初期化できること"""
    
    def test_collect_returns_file_paths(self):
        """collect が (json_path, md_path) のリストを返すこと（モック使用）"""
    
    def test_transform_trendradar_to_article(self):
        """TrendRadar 形式を Article に変換できること"""
    
    def test_run_calls_collect(self):
        """run が collect を呼び出すこと"""
```

#### Green: 最小実装
```python
# nook/services/explorers/trendradar/zhihu_explorer.py
class ZhihuExplorer(BaseService):
    """知乎のホットトピックを TrendRadar 経由で取得"""
    
    def __init__(self, storage_dir: str = "data"):
        super().__init__("trendradar-zhihu")
        self.client = TrendRadarClient()
    
    def run(self, days: int = 1, limit: int | None = None):
        asyncio.run(self.collect(days, limit))
    
    async def collect(self, days: int = 1, limit: int | None = None, *, target_dates=None):
        # TrendRadar からデータ取得
        # GPT 要約生成
        # JSON/MD 保存
        pass
```

#### Refactor
- BaseFeedService への統合検討
- 要約生成パイプラインの共通化

---

## Stream C: ServiceRunner への登録

### 目的
ZhihuExplorer を ServiceRunner に登録し、CLI から実行可能にする。

### 対象ファイル
- `nook/services/runner/run_services.py` [MODIFY]
- `nook/services/explorers/trendradar/__init__.py` [MODIFY]
- `tests/services/runner/test_run_services.py` [MODIFY]

### TDD タスク

#### Red: 失敗するテストを書く
```python
# tests/services/runner/test_run_services.py に追加
def test_service_runner_has_zhihu():
    """ServiceRunner に trendradar-zhihu が登録されていること"""
    runner = ServiceRunner()
    assert "trendradar-zhihu" in runner.service_classes
```

#### Green: 最小実装
```python
# run_services.py の service_classes に追加
from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer

self.service_classes = {
    ...
    "trendradar-zhihu": ZhihuExplorer,
}
```

#### Refactor
- CLI の --service 引数に trendradar-zhihu を追加

---

## Stream D: フロントエンド - Sidebar グループ化

### 目的
Sidebar に TrendRadar グループを追加し、折りたたみ可能なセクションを実装する。

### 対象ファイル
- `frontend/src/components/layout/Sidebar.tsx` [MODIFY]
- `frontend/src/config/sourceDisplayInfo.ts` [MODIFY]
- `frontend/src/App.tsx` [MODIFY]

### タスク

#### 1. sourceDisplayInfo.ts に追加
```typescript
"trendradar-zhihu": {
    title: "知乎 (Zhihu)",
    subtitle: "中国最大のQ&Aプラットフォーム",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-blue-50",
    gradientTo: "to-cyan-50",
    borderColor: "border-blue-200",
},
```

#### 2. Sidebar.tsx のグループ化
```tsx
const sourceGroups = {
    default: ["arxiv", "github", ...],
    trendradar: ["trendradar-zhihu"],
};
```

#### 3. App.tsx の sources 配列更新
```typescript
const sources = [
    ...existingSources,
    "trendradar-zhihu",
];
```

---

## Stream E: 統合テスト・検証

### 目的
全体の統合テストを実施し、動作確認を行う。

### 対象ファイル
- `tests/integration/test_trendradar_integration.py` [NEW]（オプション）

### タスク

#### 1. バックエンド手動テスト
```bash
# TrendRadar 起動確認
curl http://localhost:3333/mcp

# Explorer 単体実行
uv run python -c "
from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer
explorer = ZhihuExplorer()
explorer.run()
"
```

#### 2. ServiceRunner 経由実行
```bash
uv run python -m nook.services.runner.run_services --service trendradar-zhihu
```

#### 3. フロントエンド確認
```bash
cd frontend && npm run dev
# ブラウザで TrendRadar > 知乎 が表示されることを確認
```

---

## 前提条件

> ⚠️ **TrendRadar セットアップが必要**
>
> 各 Stream 実行前に TrendRadar が起動していること。
> ```bash
> git clone https://github.com/sansan0/TrendRadar
> cd TrendRadar
> ./setup-mac.sh
> ./start-http.sh  # localhost:3333/mcp
> ```

---

## 実行順序

```
Stream A → Stream B → Stream C → Stream D → Stream E
```

各 Stream は独立して実行可能だが、依存関係があるため順序通りに進めること。
