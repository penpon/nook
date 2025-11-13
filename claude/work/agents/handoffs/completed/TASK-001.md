# TASK-001: crawl_all.shの並列化実装

## タスク概要
scripts/crawl_all.sh を並列処理に変更し、データ収集の高速化を実現する。シンプルな & wait 方式を採用し、最小限の変更で最大の効果を得る。

## 変更予定ファイル
- scripts/crawl_all.sh

## 前提タスク
なし

## worktree名
worktrees/TASK-001-parallelize-crawl-all

## 作業内容

### 1. 実装前の確認
- 現在の実行時間を測定（scripts/measure_crawl_time.sh が利用可能）
- 既存のエラーハンドリングを確認

### 2. 並列化の実装
scripts/crawl_all.sh の36-67行目を以下のように変更：

**変更前（順次実行）:**
```bash
echo "Collecting Hacker News..."
python -m nook.services.run_services --service hacker_news || echo "Failed to collect Hacker News"

echo "Collecting GitHub Trending..."
python -m nook.services.run_services --service github_trending || echo "Failed to collect GitHub Trending"
# ... 以下同様
```

**変更後（並列実行）:**
```bash
echo "Launching all services in parallel..."

# 全サービスをバックグラウンドで実行
python -m nook.services.run_services --service hacker_news &
python -m nook.services.run_services --service github_trending &
python -m nook.services.run_services --service arxiv &
python -m nook.services.run_services --service tech_news &
python -m nook.services.run_services --service business_news &
python -m nook.services.run_services --service reddit &
python -m nook.services.run_services --service zenn &
python -m nook.services.run_services --service qiita &
python -m nook.services.run_services --service note &
python -m nook.services.run_services --service 4chan &
python -m nook.services.run_services --service 5chan &

# 全プロセスの完了を待つ
wait

echo "All services completed"
```

### 3. 実装の要点
- 各サービスの実行に `&` を追加してバックグラウンド実行
- 最後に `wait` コマンドで全プロセスの完了を待つ
- エラーメッセージ出力（`|| echo "Failed..."`）は削除
  - 理由：各サービス内部で適切にログ出力されるため不要
- 開始メッセージを統一（個別のメッセージは不要）

### 4. テスト
- 変更後のスクリプトを実行して正常動作を確認
- 可能であれば実行時間を測定して改善効果を確認
- 各サービスのログが正常に出力されることを確認

### 5. 期待される効果
- 実行時間が約1/2～1/3に短縮
- 各サービス内部のasyncio並列処理（並列度5）と組み合わせて効率的な処理

### 6. 注意事項
- シンプルさを維持する（複雑な並列制御は不要）
- 既存のエラーハンドリングの仕組みを壊さない
- ログ出力の競合は各サービス内部で適切に処理されているため考慮不要

## 完了条件
- [ ] scripts/crawl_all.sh が並列処理に変更されている
- [ ] 全サービスが正常に実行される
- [ ] エラーが発生してもスクリプトが正常終了する
- [ ] 実行時間が短縮されている（測定して確認）