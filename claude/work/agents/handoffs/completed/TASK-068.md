# TASK-068: 緊急修正 - 5chanサービスURL構造修正

## タスク概要
5chanサービスが全ての板でスレッド取得に失敗している問題の緊急修正。根本原因は5chの正しいURL構造を理解せずに実装されていること。

## 変更予定ファイル
- `nook/services/fivechan_explorer/fivechan_explorer.py`
- `nook/services/fivechan_explorer/boards.toml`

## 前提タスク
なし（緊急修正）

## worktree名
worktrees/TASK-068-fix-5chan-url-structure

## 作業内容

### 1. 問題の現状
- 全24板でHTTP 403エラー発生
- 間違ったURL構造: `https://menu.5ch.net/test/read.cgi/{board_id}/`
- 正しい構造: `https://{subdomain}.5ch.net/{board_id}/`

### 2. 修正対象

#### fivechan_explorer.py (199-270行目)
- `_retrieve_ai_threads`メソッドの全面書き換え
- 正しいURL構築ロジックへの変更
- サブドメイン試行機能の修正

#### boards.toml
- 各板のサブドメイン情報追加
- URL構築に必要な追加パラメータ

### 3. 実装要件
- 5chの実際のURL構造に準拠
- サブドメイン別のフォールバック機能
- 基本的なエラーハンドリング
- リクエスト間隔を5秒に拡大

### 4. 検証方法
- サービス実行でスレッド取得成功を確認
- 複数板での動作確認
- エラーログの解消確認

### 5. 完了条件
- [ ] 少なくとも5つの主要板でスレッド取得成功
- [ ] HTTP 403エラーの解消
- [ ] ログに「見つかったスレッド数: 0」が出ない
- [ ] 品質チェック全項目通過