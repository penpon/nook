# TASK-004: グループ3サービスの移行 (zenn_explorer, qiita_explorer, fourchan_explorer, fivechan_explorer)

## タスク概要
既にclose()処理が実装されている4つのサービスをグローバルHTTPクライアントに移行する

## 変更予定ファイル
- nook/services/zenn_explorer/zenn_explorer.py
- nook/services/qiita_explorer/qiita_explorer.py
- nook/services/fourchan_explorer/fourchan_explorer.py
- nook/services/fivechan_explorer/fivechan_explorer.py

## 前提タスク
TASK-001（BaseServiceクラスの修正）

## worktree名
worktrees/TASK-004-group3-http-migration

## 作業内容

### 1. 各サービスの__init__メソッドを修正

#### 現在のコード（例：zenn_explorer.py）
```python
def __init__(self):
    super().__init__("zenn_explorer")
    self.http_client = AsyncHTTPClient()
```

#### 修正後のコード
```python
def __init__(self):
    super().__init__("zenn_explorer")
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
- 各サービスのfinallyブロックからHTTPクライアントのclose処理を削除
- 他の必要なクリーンアップ処理は維持

### 5. 4chan/5chanサービスの特殊対応
- これらのサービスは特殊な文字エンコーディングを扱う可能性
- HTTPクライアントの動作に影響がないか確認

## テスト手順
1. 各サービスを個別に実行
2. 日本語コンテンツの取得が正常に動作することを確認
3. 文字化けが発生していないことを確認
4. リソースリークがないことを確認

## 注意事項
- 文字エンコーディングの問題に注意
- 4chan/5chanの特殊なレスポンス形式に対応
- 既存の機能を維持しながら移行