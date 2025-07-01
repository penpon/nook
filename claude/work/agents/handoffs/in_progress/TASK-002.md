# TASK-002: 緊急: crawl_all.shの並列度制限を実装

## タスク概要
TASK-001で無制限の並列化を実装してしまったため、リソース枯渇を防ぐために並列度制限を緊急実装する。

## 変更予定ファイル
- scripts/crawl_all.sh

## 前提タスク
- TASK-001（完了済み - 問題のある実装）

## worktree名
worktrees/TASK-002-limit-crawl-parallelism

## 作業内容

### 1. 問題の認識
- 現在11個のサービスが同時に起動
- 各サービス内でも無制限にHTTPリクエストが並列実行
- 最悪の場合、1000以上の同時HTTPリクエストが発生する可能性

### 2. 緊急修正の実装

**修正案: 3-4個ずつのグループで実行**

```bash
echo "Launching services in controlled batches..."

# グループ1: 軽量なサービス
echo "Starting batch 1/3..."
python -m nook.services.run_services --service hacker_news &
python -m nook.services.run_services --service github_trending &
python -m nook.services.run_services --service reddit &
wait

# グループ2: 中程度のサービス
echo "Starting batch 2/3..."
python -m nook.services.run_services --service tech_news &
python -m nook.services.run_services --service business_news &
python -m nook.services.run_services --service arxiv &
python -m nook.services.run_services --service zenn &
wait

# グループ3: 残りのサービス
echo "Starting batch 3/3..."
python -m nook.services.run_services --service qiita &
python -m nook.services.run_services --service note &
python -m nook.services.run_services --service 4chan &
python -m nook.services.run_services --service 5chan &
wait

echo "All services completed"
```

### 3. グループ分けの根拠
- **グループ1**: APIが安定していて高速なサービス
- **グループ2**: データ量が多いまたは処理が重いサービス
- **グループ3**: 優先度が低いまたは不安定なサービス

### 4. テスト方法
1. 修正後のスクリプトを実行
2. システムリソース（CPU、メモリ、ネットワーク）をモニタリング
3. エラーログを確認
4. 全サービスが正常に完了することを確認

### 5. 期待される効果
- 同時実行数が最大4サービスに制限される
- システムリソースの枯渇を防ぐ
- APIレート制限エラーを回避
- より安定した実行

### 6. 今後の改善案への橋渡し
この緊急修正の後、TASK-003でrun_services.py側の根本的な並列度制限を実装する。

## 完了条件
- [ ] crawl_all.shが3グループに分けて実行されるよう修正
- [ ] 各グループが順次実行される（waitで待機）
- [ ] システムリソースの過剰使用が解消される
- [ ] 全サービスが正常に実行される