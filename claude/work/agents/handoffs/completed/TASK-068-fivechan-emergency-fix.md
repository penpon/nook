# TASK-068: 5chan Explorer 403エラー緊急修正

## タスク概要
bbsmenu.html依存による403エラーを根本解決するため、正しいURL構造への緊急修正を実施

## 変更予定ファイル
- nook/services/fivechan_explorer/fivechan_explorer.py
- nook/services/fivechan_explorer/boards.toml

## 前提タスク
なし

## worktree名
worktrees/TASK-068-fivechan-emergency-fix

## 作業内容

### 1. 根本原因の解決
- bbsmenu.html解析処理の完全除去
- 間違ったURL推測ロジックの削除
- 正しい板サーバー情報のboards.tomlへのハードコーディング

### 2. 正しいURL構造の実装
```python
# 正しい5chanURL構造例
BOARD_SERVERS = {
    "prog": "mevius.5ch.net",
    "ai": "egg.5ch.net",
    # 他の板の正確なサーバー情報を調査・追加
}
```

### 3. シンプルなHTTPアクセスへの回帰
- 複雑なHTTPクライアント機能の一時無効化
- 基本的なrequestsライブラリ使用（初期版同様）
- User-Agentローテーション等の高度機能一時停止

### 4. 最小限のテスト実行
- prog板での基本動作確認
- 1つのAI関連スレッドが正常取得できることを確認

### 完了条件
- 403エラーが解消されること
- 最低1つのスレッドが正常に取得できること
- ビルドエラーが発生しないこと

### 重要な注意事項
- 過度な変更は避け、最小限の修正で動作確認を優先
- 既存の高度機能は削除せず、一時的にコメントアウト
- 後続タスクで段階的に機能復元予定