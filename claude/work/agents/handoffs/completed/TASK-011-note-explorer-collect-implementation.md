# TASK-011: NoteExplorer collectメソッド実装

## タスク概要
NoteExplorerサービスにBaseService継承とcollectメソッドを実装し、非同期実行を可能にする

## 変更予定ファイル
- nook/services/note_explorer/note_explorer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-011-note-explorer-collect

## 作業内容

### 1. BaseService継承の追加
- `from nook.common.base_service import BaseService`を追加
- `class NoteExplorer(BaseService):`に変更
- `super().__init__("note")`を`__init__`に追加

### 2. 非同期HTTPクライアントの導入
- `from nook.common.http_client import AsyncHTTPClient`を追加
- `requests`の代わりに`AsyncHTTPClient`を使用

### 3. collectメソッドの実装
- 既存の`run`メソッドロジックを非同期化
- `async def collect(self, days: int = 7, limit: int = 30) -> None:`を実装
- RSS解析とHTTP要求を非同期化

### 4. runメソッドの修正
- `asyncio.run(self.collect(days, limit))`のラッパーに変更

### 5. エラーハンドリングの統一
- BaseServiceのロガーを使用
- 統一されたエラーハンドリング

### 注意事項
- Note RSS仕様を維持
- 日本語記事のフィルタリング保持
- 既存のスコアリングロジック保持