# TASK-003: グループ2サービスの移行 (tech_feed, business_feed, note_explorer)

## タスク概要
既にclose()処理が実装されている3つのサービスをグローバルHTTPクライアントに移行する

## 変更予定ファイル
- nook/services/tech_feed/tech_feed.py
- nook/services/business_feed/business_feed.py
- nook/services/note_explorer/note_explorer.py

## 前提タスク
TASK-001（BaseServiceクラスの修正）

## worktree名
worktrees/TASK-003-group2-http-migration

## 作業内容

### 1. 各サービスの__init__メソッドを修正

#### 現在のコード（例：tech_feed.py）
```python
def __init__(self):
    super().__init__("tech_feed")
    self.http_client = AsyncHTTPClient()
```

#### 修正後のコード
```python
def __init__(self):
    super().__init__("tech_feed")
    self.http_client = None  # setup_http_clientで初期化
```

### 2. 非同期初期化メソッドの追加
```python
async def setup_http_client(self):
    """グローバルHTTPクライアントをセットアップ"""
    from nook.common.http_client import get_http_client
    self.http_client = await get_http_client()
```

### 3. collect/runメソッドの修正
```python
async def collect(self):
    # HTTPクライアントの初期化を確認
    if self.http_client is None:
        await self.setup_http_client()
    
    try:
        # 既存の処理...
    finally:
        # close処理を削除（グローバルクライアントなので不要）
        pass
```

### 4. 既存のclose処理の削除
```python
# 削除するコード
finally:
    await self.http_client.close()
```

### 5. finallyブロックの整理
- HTTPクライアントのclose処理を削除
- 他の必要なクリーンアップ処理は維持

## テスト手順
1. 各サービスを個別に実行
2. フィード収集が正常に動作することを確認
3. 複数回実行してもリソースリークがないことを確認

## 注意事項
- finallyブロックの他の処理を誤って削除しないよう注意
- 非同期初期化パターンを正しく実装
- エラーハンドリングを維持