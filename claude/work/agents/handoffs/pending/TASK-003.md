# TASK-003: run_services.pyの並列度制限実装

## タスク概要
run_services.py内で無制限に並列実行されている問題を根本的に解決。セマフォを使用して同時実行サービス数を制限する。

## 変更予定ファイル
- nook/services/run_services.py
- .env.example（新しい環境変数の追加）

## 前提タスク
- TASK-002（crawl_all.shの緊急修正）

## worktree名
worktrees/TASK-003-limit-service-concurrency

## 作業内容

### 1. run_services.pyの修正

**ServiceRunnerクラスのrun_all()メソッドを修正:**

```python
async def run_all(self) -> None:
    """すべてのサービスを並行実行"""
    self.running = True
    start_time = datetime.now()
    
    # 環境変数から並列度を取得（デフォルト: 3）
    max_concurrent = int(os.getenv("NOOK_SERVICE_CONCURRENCY", "3"))
    logger.info(f"Starting {len(self.sync_services)} services with max concurrency: {max_concurrent}")
    
    # セマフォで並列度を制限
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_limit(name, service):
        async with semaphore:
            logger.info(f"Acquired semaphore for {name}")
            try:
                return await self._run_sync_service(name, service)
            finally:
                logger.info(f"Released semaphore for {name}")
    
    try:
        # 各サービスを制限付きで並行実行
        service_tasks = [
            run_with_limit(name, service) 
            for name, service in self.sync_services.items()
        ]
        
        results = await gather_with_errors(
            *service_tasks,
            task_names=list(self.sync_services.keys())
        )
        
        # 以下既存のコード...
```

### 2. run_service()メソッドも念のため確認
単一サービス実行時は並列度制限不要だが、ログを追加して動作を明確化。

### 3. .env.exampleへの追加
```bash
# Service execution settings
NOOK_SERVICE_CONCURRENCY=3  # Maximum number of services to run in parallel
```

### 4. 各サービス内の並列度制限（オプション）
時間があれば、主要なサービス（hacker_news.pyなど）内のHTTPリクエスト並列度も制限：

```python
# 環境変数で制御可能に
http_concurrency = int(os.getenv("NOOK_HTTP_CONCURRENCY", "10"))
semaphore = asyncio.Semaphore(http_concurrency)
```

### 5. テスト計画
1. 環境変数を設定してテスト
   ```bash
   export NOOK_SERVICE_CONCURRENCY=2
   python -m nook.services.run_services --service all
   ```

2. ログで並列実行数を確認
3. システムリソースの使用状況を確認
4. 異なる並列度での実行時間を比較

### 6. 推奨される環境変数設定
```bash
# 控えめな設定（安定性重視）
NOOK_SERVICE_CONCURRENCY=3
NOOK_HTTP_CONCURRENCY=10

# 通常の設定
NOOK_SERVICE_CONCURRENCY=5
NOOK_HTTP_CONCURRENCY=20

# 高速設定（リソースに余裕がある場合）
NOOK_SERVICE_CONCURRENCY=8
NOOK_HTTP_CONCURRENCY=30
```

## 期待される効果
- システムリソースの使用量が予測可能になる
- APIレート制限エラーの削減
- 環境に応じた柔軟な調整が可能
- デバッグが容易になる（ログで並列実行を追跡）

## 完了条件
- [ ] run_services.pyにセマフォベースの並列度制限を実装
- [ ] 環境変数で並列度を調整可能
- [ ] ログで並列実行の状況を確認可能
- [ ] .env.exampleに新しい環境変数を記載
- [ ] 異なる並列度でテストを実施