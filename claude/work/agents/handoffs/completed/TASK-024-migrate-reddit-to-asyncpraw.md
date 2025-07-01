# TASK-024: RedditサービスをAsync PRAWに移行

## タスク概要: 同期版のPRAWから非同期版のAsync PRAWに移行し、警告メッセージを解消する

## 変更予定ファイル:
- nook/services/reddit_explorer/reddit_explorer.py
- pyproject.toml または requirements.txt（依存関係の更新）

## 前提タスク: なし

## worktree名: worktrees/TASK-024-asyncpraw

## 作業内容:

### 1. 依存関係の更新
- `praw`を`asyncpraw`に置き換え
- `uv pip install asyncpraw`を実行

### 2. RedditExplorerクラスの修正

#### インポートの変更
```python
# 変更前
import praw
from praw.models import Submission

# 変更後
import asyncpraw
from asyncpraw.models import Submission
```

#### 初期化の修正
```python
# 変更前
self.reddit = praw.Reddit(
    client_id=self.client_id,
    client_secret=self.client_secret,
    user_agent=self.user_agent
)

# 変更後
self.reddit = asyncpraw.Reddit(
    client_id=self.client_id,
    client_secret=self.client_secret,
    user_agent=self.user_agent
)
```

#### 非同期メソッドの修正
- `subreddit.hot()`を`await subreddit.hot()`に変更
- `self.reddit.subreddit()`を`await self.reddit.subreddit()`に変更
- `self.reddit.submission()`を`await self.reddit.submission()`に変更
- その他のReddit APIコールをすべて非同期化

#### リソース管理の追加
- `__aenter__`と`__aexit__`メソッドを追加してRedditクライアントを適切に管理
- `collect()`メソッドの最後で`await self.reddit.close()`を呼び出し

### 3. エラーハンドリングの改善
- 非同期版特有のエラーに対応
- 接続エラー時の適切なリトライ処理

### 4. テストの実行
- 移行後、実際にRedditサービスを実行して警告が消えることを確認
- データが正しく取得できることを確認

## 期待される効果:
- 警告メッセージの完全な除去
- 真の非同期処理によるパフォーマンス向上
- より適切なリソース管理
- コードの一貫性向上