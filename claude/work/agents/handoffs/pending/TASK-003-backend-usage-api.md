# TASK-003: 使用量API エンドポイントの実装

## タスク概要
LLM API使用量データを提供するRESTful APIエンドポイントを実装する。

## 実装要件

### 1. 新規ルーターの作成
- `nook/api/routers/usage.py`
- FastAPIルーターとして実装

### 2. エンドポイント

#### 2.1 GET /api/usage/summary
使用量のサマリー情報を返す
```python
@router.get("/summary")
async def get_usage_summary():
    # 返却値の例
    return {
        "todayTokens": 125000,
        "todayCost": 0.12,
        "monthCost": 3.45,
        "totalCalls": 234
    }
```

#### 2.2 GET /api/usage/by-service
サービス別の使用量を返す
```python
@router.get("/by-service")
async def get_usage_by_service():
    # 返却値の例
    return [
        {
            "service": "tech_feed",
            "calls": 45,
            "inputTokens": 50000,
            "outputTokens": 15000,
            "cost": 0.022,
            "lastCalled": "2024-01-20T15:30:45Z"
        }
    ]
```

#### 2.3 GET /api/usage/daily
日別の使用量を返す
```python
@router.get("/daily")
async def get_daily_usage(days: int = 30):
    # 返却値の例
    return [
        {
            "date": "2024-01-20",
            "services": {
                "tech_feed": 0.05,
                "reddit_explorer": 0.03,
                "business_feed": 0.02
            },
            "totalCost": 0.10
        }
    ]
```

### 3. データ処理
- `data/api_usage/llm_usage_log.jsonl` からデータを読み込む
- 効率的な集計処理の実装
- キャッシング機能（5分間有効）

### 4. ユーティリティ関数
```python
def read_usage_logs() -> List[Dict]:
    """ログファイルからデータを読み込む"""
    
def aggregate_by_service(logs: List[Dict]) -> List[Dict]:
    """サービス別に集計"""
    
def aggregate_by_day(logs: List[Dict], days: int) -> List[Dict]:
    """日別に集計"""
    
def calculate_summary(logs: List[Dict]) -> Dict:
    """サマリー情報を計算"""
```

### 5. エラーハンドリング
- ログファイルが存在しない場合の処理
- 不正なデータ形式への対応
- 適切なHTTPステータスコードの返却

### 6. パフォーマンス最適化
- 大量のログデータに対応
- インメモリキャッシュの実装
- 必要に応じて集計結果をファイルに保存

### 7. main.pyへの追加
```python
from nook.api.routers import usage
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
```

## 完了条件
- [ ] usage.pyルーターを作成
- [ ] 3つのエンドポイントを実装
- [ ] ログファイルからのデータ読み込み機能
- [ ] 集計処理の実装
- [ ] キャッシング機能の実装
- [ ] main.pyにルーターを登録