# TASK-018: scripts/crawl_all.shのサービス名修正

## タスク概要
scripts/crawl_all.shでGitHub Trendingサービスを実行する際、誤ったサービス名を使用しているため、エラーが発生しています。

## 問題の詳細
- エラーメッセージ: `invalid choice: 'github' (choose from 'all', 'github_trending', ...)`
- 問題の行: `python -m nook.services.run_services --service github`
- 原因: サービス名が`github`ではなく`github_trending`である

## 変更予定ファイル
- scripts/crawl_all.sh

## 前提タスク
- なし（独立したタスク）

## 実装内容

1. scripts/crawl_all.shの30行目を修正
2. サービス名を`github`から`github_trending`に変更

## 修正例

修正前（30行目）:
```bash
python -m nook.services.run_services --service github || echo "Failed to collect GitHub Trending"
```

修正後:
```bash
python -m nook.services.run_services --service github_trending || echo "Failed to collect GitHub Trending"
```

## テスト方法
1. 修正後、scripts/crawl_all.shを実行
2. GitHub Trendingサービスが正常に実行されることを確認
3. `Failed to collect GitHub Trending`のエラーメッセージが表示されないことを確認

## 注意事項
- 他のサービス名も正しいか確認する
- run_services.pyの--helpで利用可能なサービス名を確認できる