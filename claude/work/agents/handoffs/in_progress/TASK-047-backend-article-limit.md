# TASK-047: バックエンド記事取得数制限実装

## タスク概要
Hacker News、Tech News、Business Newsの記事取得数を制限する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/run_services.py`
- `/Users/nana/workspace/nook/nook/services/run_services_sync.py`

## 前提タスク
なし

## worktree名
`worktrees/TASK-047-backend-article-limit`

## 作業内容

### 1. run_services.pyの修正

#### _run_sync_serviceメソッドを修正
```python
async def _run_sync_service(self, service_name: str, service):
    """同期サービスを非同期で実行"""
    logger.info(f"Starting service: {service_name}")
    
    try:
        # サービスごとに異なるlimitパラメータを設定
        if service_name == "hacker_news":
            # Hacker Newsは15記事に制限
            result = await self.loop.run_in_executor(
                self.executor,
                lambda: service.collect(limit=15)
            )
        elif service_name in ["tech_news", "business_news"]:
            # Tech News/Business Newsは各5記事に制限
            result = await self.loop.run_in_executor(
                self.executor,
                lambda: service.collect(limit=5)
            )
        else:
            # その他のサービスはデフォルト値を使用
            result = await self.loop.run_in_executor(
                self.executor,
                service.run
            )
        
        if result:
            logger.info(f"Service {service_name} completed with data")
        else:
            logger.info(f"Service {service_name} completed without data")
    except Exception as e:
        logger.error(f"Service {service_name} failed: {e}")
        raise
```

### 2. run_services_sync.pyの修正

#### 各サービス実行関数を修正

```python
def run_hacker_news():
    """
    Hacker Newsからのトップ記事収集サービスを実行します。
    """
    print("Hacker Newsからトップ記事を収集しています...")
    try:
        hacker_news = HackerNewsRetriever()
        # 15記事に制限
        hacker_news.collect(limit=15)
        print("Hacker Newsの記事収集が完了しました。")
    except Exception as e:
        print(f"Hacker Newsの記事収集中にエラーが発生しました: {str(e)}")

def run_tech_feed():
    """
    技術記事のフィード収集サービスを実行します。
    """
    print("技術記事のフィードを収集しています...")
    try:
        tech_feed = TechFeed()
        # 5記事に制限
        tech_feed.collect(limit=5)
        print("技術記事のフィードの収集が完了しました。")
    except Exception as e:
        print(f"技術記事のフィード収集中にエラーが発生しました: {str(e)}")

def run_business_feed():
    """
    ビジネス記事のフィード収集サービスを実行します。
    """
    print("ビジネス記事のフィードを収集しています...")
    try:
        business_feed = BusinessFeed()
        # 5記事に制限
        business_feed.collect(limit=5)
        print("ビジネス記事のフィードの収集が完了しました。")
    except Exception as e:
        print(f"ビジネス記事のフィード収集中にエラーが発生しました: {str(e)}")
```

### 3. 動作確認手順

1. 修正後、各サービスを個別に実行して取得数を確認：
   ```bash
   python -m nook.services.run_services_sync --service hacker_news
   python -m nook.services.run_services_sync --service tech_news
   python -m nook.services.run_services_sync --service business_news
   ```

2. 生成されたファイルの記事数を確認：
   - `data/hacker_news/YYYY-MM-DD.json` → 15記事
   - `data/tech_feed/YYYY-MM-DD.md` → 5記事
   - `data/business_feed/YYYY-MM-DD.md` → 5記事

3. ログを確認して正しいlimitが適用されていることを確認

## 期待される効果
- Hacker Newsの記事数が15件に制限される
- Tech News/Business Newsの記事数が各5件に制限される
- API呼び出し数の削減とパフォーマンス向上

## 注意事項
- collectメソッドが存在しないサービスは従来通りrunメソッドを使用
- 制限値は固定値として実装（将来的に設定ファイル化も検討）
- ログで実際の取得数を記録し、動作確認を容易にする