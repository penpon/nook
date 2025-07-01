# TASK-007: BusinessFeed collectメソッド実装

## タスク概要
BusinessFeedサービスにBaseService継承とcollectメソッドを実装し、非同期実行を可能にする

## 変更予定ファイル
- nook/services/business_feed/business_feed.py

## 前提タスク
なし

## worktree名
worktrees/TASK-007-business-feed-collect

## 作業内容

### 1. BaseService継承の追加
- `from nook.common.base_service import BaseService`を追加
- `class BusinessFeed(BaseService):`に変更
- `super().__init__("business_feed")`を`__init__`に追加

### 2. 非同期HTTPクライアントの導入
- `from nook.common.http_client import AsyncHTTPClient`を追加
- `requests`の代わりに`AsyncHTTPClient`を使用

### 3. collectメソッドの実装
- 既存の`run`メソッドロジックを非同期化
- `async def collect(self, days: int = 1, limit: int = 30) -> None:`を実装
- HTTP要求を非同期化（`requests.get` → `self.http_client.get`）

### 4. runメソッドの修正
- `asyncio.run(self.collect(days, limit))`のラッパーに変更

### 5. エラーハンドリングの統一
- BaseServiceのロガーを使用
- 統一されたエラーハンドリング

### 注意事項
- 既存の機能を維持する
- 設定ファイル（feed.toml）の読み込みを保持
- GPTClientの使用を維持
- 日本語検出ロジックを保持