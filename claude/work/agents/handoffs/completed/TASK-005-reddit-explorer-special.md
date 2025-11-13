# TASK-005: Reddit Explorerの特別対応 (asyncpraw問題解決)

## タスク概要
Reddit Explorerはasyncprawライブラリを使用しており、内部でaiohttpを使用しているため特別な対応が必要

## 変更予定ファイル
- nook/services/reddit_explorer/reddit_explorer.py

## 前提タスク
なし（他のタスクと独立して実行可能）

## worktree名
worktrees/TASK-005-reddit-asyncpraw-fix

## 作業内容

### 1. 現状の問題分析
- asyncprawは内部でaiohttpを使用
- aiohttpのセッションが適切にクローズされていない
- httpxベースの他のサービスとの競合の可能性

### 2. 解決方法の実装

#### オプション1: asyncprawの適切なクローズ（推奨）
```python
async def collect(self):
    reddit = None
    try:
        # Redditクライアントの作成
        reddit = asyncpraw.Reddit(
            client_id=self.config.REDDIT_CLIENT_ID,
            client_secret=self.config.REDDIT_CLIENT_SECRET,
            user_agent=self.config.REDDIT_USER_AGENT
        )
        
        # 既存の処理...
        
    finally:
        # HTTPクライアントのクローズ
        if self.http_client:
            await self.http_client.close()
        
        # Redditクライアントのクローズ（重要）
        if reddit:
            await reddit.close()
```

#### オプション2: コンテキストマネージャーの使用
```python
async def collect(self):
    try:
        # HTTPクライアントの初期化
        if self.http_client is None:
            from nook.common.http_client import get_http_client
            self.http_client = await get_http_client()
        
        # Redditクライアントをコンテキストマネージャーで使用
        async with asyncpraw.Reddit(
            client_id=self.config.REDDIT_CLIENT_ID,
            client_secret=self.config.REDDIT_CLIENT_SECRET,
            user_agent=self.config.REDDIT_USER_AGENT
        ) as reddit:
            # 既存の処理...
            
    finally:
        # グローバルHTTPクライアントなのでクローズ不要
        pass
```

### 3. HTTPクライアントの移行
- 他のサービスと同様にグローバルHTTPクライアントに移行
- asyncprawは独自のHTTP処理を行うため、併用可能

### 4. エラーハンドリングの強化
- aiohttpとhttpxの競合によるエラーをキャッチ
- 適切なログ出力

## テスト手順
1. Reddit Explorerを単独で実行
2. 「Unclosed client session」エラーが出ないことを確認
3. 他のサービスと同時実行してもエラーが出ないことを確認
4. Redditからのデータ取得が正常に動作することを確認

## 注意事項
- asyncprawのドキュメントを確認してクローズ方法を理解
- aiohttpのセッションが確実にクローズされることを確認
- Reddit APIのレート制限に注意