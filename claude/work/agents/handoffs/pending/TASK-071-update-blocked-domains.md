# TASK-071: ブロックドメインリストの更新
## タスク概要: 現在403エラーを返している新たなドメインをblocked_domains.jsonに追加
## 変更予定ファイル: nook/services/hacker_news/blocked_domains.json
## 前提タスク: なし
## worktree名: worktrees/TASK-071-update-blocked-domains
## 作業内容:

### 1. 背景
- 複数のサイトが新たに403エラーを返すようになった
- これらのサイトは一時的にブロックリストに追加し、TASK-069/070の実装後に再評価する

### 2. 追加するドメイン

以下のドメインをblocked_domains.jsonに追加：

```json
[
  "nytimes.com",
  "cell.com",
  "journals.aps.org",
  "decodingml.substack.com",
  "commonwealmagazine.org",
  "jidonline.org",
  "backblaze.com",
  "blog.arduino.cc",
  "frest.substack.com",
  "parallelprogrammer.substack.com",
  "thestreet.com"
]
```

### 3. 実装手順

1. blocked_domains.jsonを開く
2. 上記のドメインを既存のリストに追加
3. 重複がないか確認
4. JSONの形式が正しいことを確認

### 4. 注意事項
- これは一時的な対策
- TASK-069/070実装後、これらのドメインを再テストし、アクセス可能になったものは削除する
- ドメイン名は正確に記載（wwwの有無に注意）

### 5. テスト
- サービスを実行し、403エラーが減少することを確認
- blocked_domains.jsonの構文エラーがないことを確認