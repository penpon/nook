# TASK-002: グループ1サービスの移行 (hacker_news, github_trending, arxiv_summarizer)

## タスク概要
現在close()処理が実装されていない3つのサービスをグローバルHTTPクライアントに移行する

## 変更予定ファイル
- nook/services/hacker_news/hacker_news.py
- nook/services/github_trending/github_trending.py
- nook/services/arxiv_summarizer/arxiv_summarizer.py

## 前提タスク
TASK-001（BaseServiceクラスの修正）

## worktree名
worktrees/TASK-002-group1-http-migration

## 作業内容

### 1. 各サービスの__init__メソッドを修正

#### 現在のコード（例：hacker_news.py）
```python
def __init__(self):
    super().__init__("hacker_news")
    self.http_client = AsyncHTTPClient()
```

#### 修正後のコード
```python
def __init__(self):
    super().__init__("hacker_news")
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
    
    # 既存の処理...
```

### 4. close処理の削除
- これらのサービスにはclose処理がないため、追加不要
- グローバルクライアントなのでサービス側でのクローズは不要

## テスト手順
1. 各サービスを個別に実行
2. データ収集が正常に動作することを確認
3. HTTPクライアントのリソースリークがないことを確認

## 注意事項
- 非同期初期化パターンに注意
- エラーハンドリングを適切に実装
- 既存の機能を壊さないよう慎重に作業