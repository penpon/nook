# TASK-071: ブロックドメインリストの更新
## タスク概要: TASK-069実装後もアクセスできないサイトをblocked_domains.jsonに追加
## 変更予定ファイル: nook/services/hacker_news/blocked_domains.json
## 前提タスク: TASK-069
## worktree名: worktrees/TASK-071-update-blocked-domains
## 作業内容:

### 1. 背景
- TASK-069の403エラー対策（ブラウザヘッダー + cloudscraper）実装後も、一部のサイトは403エラーを返す
- これらのサイトは最新のCloudflare保護や高度なBot検出を使用しており、通常の回避策では対応不可
- 実際のテストで、TASK-069実装により約50%のサイトはアクセス可能になることを確認済み

### 2. 追加するドメイン

TASK-069実装後もアクセスできない以下のドメインをblocked_domains.jsonに追加：

```json
[
  "nytimes.com",
  "cell.com", 
  "journals.aps.org",
  "decodingml.substack.com"
]
```

### 3. アクセス可能になるドメイン（追加不要）

TASK-069実装により以下のサイトはアクセス可能になるため、ブロックリストには追加しない：
- ethanzuckerman.com
- friendsjournal.org
- overclock3d.net
- commonwealmagazine.org
- jidonline.org

### 4. 実装手順

1. blocked_domains.jsonを開く
2. 上記の4つのドメインを既存のリストに追加
3. 重複がないか確認
4. JSONの形式が正しいことを確認
5. その他の403エラーサイト（backblaze.com等）も必要に応じて追加

### 5. 注意事項
- TASK-069実装前にこのタスクを実行しない（前提タスクの完了を確認）
- ドメイン名は正確に記載（wwwの有無に注意）
- 将来的により高度な回避策が実装された場合は、これらのドメインを再評価

### 6. テスト
- TASK-069実装後にサービスを実行
- 403エラーが大幅に減少することを確認
- blocked_domains.jsonの構文エラーがないことを確認