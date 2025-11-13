# TASK-012: FourChanExplorer collectメソッド実装

## タスク概要
FourChanExplorerサービスにBaseService継承とcollectメソッドを実装し、非同期実行を可能にする

## 変更予定ファイル
- nook/services/fourchan_explorer/fourchan_explorer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-012-4chan-explorer-collect

## 作業内容

### 1. BaseService継承の追加
- `from nook.common.base_service import BaseService`を追加
- `class FourChanExplorer(BaseService):`に変更
- `super().__init__("4chan")`を`__init__`に追加

### 2. 非同期HTTPクライアントの導入
- `from nook.common.http_client import AsyncHTTPClient`を追加
- `requests`の代わりに`AsyncHTTPClient`を使用

### 3. collectメソッドの実装
- 既存の`run`メソッドロジックを非同期化
- `async def collect(self, boards: List[str] = None, limit: int = 30) -> None:`を実装
- 4chan API要求を非同期化

### 4. runメソッドの修正
- `asyncio.run(self.collect(boards, limit))`のラッパーに変更

### 5. エラーハンドリングの統一
- BaseServiceのロガーを使用
- 統一されたエラーハンドリング

### 注意事項
- 4chan API仕様を維持
- レート制限の考慮（4chan は厳格）
- 既存のフィルタリングロジック保持
- コンテンツフィルタリング機能を維持