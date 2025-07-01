# TASK-020: アクセス制限サイトのブロックリスト機能実装

## タスク概要: Hacker Newsサービスで、アクセス制限のあるサイトを事前に除外するブロックリスト機能を実装する

## 変更予定ファイル:
- nook/services/hacker_news/hacker_news.py
- nook/services/hacker_news/blocked_domains.json (新規作成)

## 前提タスク: なし

## worktree名: worktrees/TASK-020-blocklist

## 作業内容:

### 1. ブロックドメインリストの作成
`nook/services/hacker_news/blocked_domains.json`を新規作成：
```json
{
  "blocked_domains": [
    "reuters.com",
    "wsj.com",
    "bloomberg.com",
    "ft.com",
    "economist.com",
    "science.org",
    "smithsonianmag.com",
    "blogs.bl.uk"
  ],
  "reasons": {
    "reuters.com": "401 - Authentication required",
    "wsj.com": "401 - Subscription required",
    "bloomberg.com": "403 - Bot protection",
    "ft.com": "403 - Paywall",
    "economist.com": "403 - Paywall",
    "science.org": "403 - Access restricted",
    "smithsonianmag.com": "403 - Bot detection",
    "blogs.bl.uk": "403 - Geographic restriction"
  }
}
```

### 2. HackerNewsRetrieverクラスの修正
以下の機能を追加：
- `__init__`でブロックリストを読み込み
- `_is_blocked_domain()`メソッドを追加してURLチェック
- `_fetch_story_content()`でブロックされたドメインをスキップ
- ブロックされた場合は専用のメッセージを設定

### 3. テストの作成
- ブロックリストの読み込みテスト
- ドメインチェック機能のテスト
- ブロックされたURLのスキップ動作テスト

## 期待される効果:
- 無駄なHTTPリクエストの削減
- エラーログの大幅な削減
- 処理時間の短縮
- より明確なエラーメッセージ