# TASK-070: 5chanサービス 設定とテストの拡充

## タスク概要
5chanサービスの設定ファイルを拡充し、テストケースを作成して保守性と信頼性を向上させる。

## 変更予定ファイル
- `nook/services/fivechan_explorer/boards.toml`
- `tests/services/test_fivechan_explorer.py`（新規作成）
- `nook/services/fivechan_explorer/fivechan_explorer.py`（軽微な調整）

## 前提タスク
TASK-069（アクセス制御改善完了後）

## worktree名
worktrees/TASK-070-enhance-5chan-config-tests

## 作業内容

### 1. 設定ファイルの拡充
#### boards.toml の改善
- 各板のサブドメイン情報を詳細化
- アクセス優先度の設定
- 板固有のパラメータ（リクエスト間隔等）
- フォールバックサブドメインの定義

### 2. テストケース作成
#### test_fivechan_explorer.py
- 基本的な単体テスト
- URL構築ロジックのテスト
- エラーハンドリングのテスト
- モックを使用したHTTPリクエストテスト
- 設定ファイル読み込みテスト

### 3. テスト環境整備
- pytestの設定
- モックHTTPレスポンスの準備
- テストデータの作成

### 4. 実装要件
- 設定ファイル読み込み処理の改善
- 板固有設定の活用機能
- テストカバレッジ80%以上
- CI/CDでの自動テスト実行対応

### 5. 完了条件
- [ ] boards.tomlの拡充完了
- [ ] テストケース実装（カバレッジ80%以上）
- [ ] 全テストの成功
- [ ] 設定ファイル駆動の動作確認
- [ ] 品質チェック全項目通過