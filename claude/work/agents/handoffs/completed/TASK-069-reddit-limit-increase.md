# TASK-069: Reddit投稿取得数を10件に増量

## タスク概要
現在のRedditサービスは各サブレディットから3件（デフォルト）の投稿しか取得していないため、ユーザーの要望に応じて10件に増量する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/run_services.py`

## 前提タスク
なし

## worktree名
worktrees/TASK-069-reddit-limit-increase

## 作業内容

### 1. 現在の問題状況
- r/MachineLearningから1件しか取得されていない
- 他のサブレディットも最大3件までしか取得されていない
- ユーザーは各サブレディットから10件程度を希望

### 2. 解決方法
`run_services.py`の`_run_sync_service`メソッドで、Redditサービスに`limit=10`を設定する。

### 3. 具体的な変更内容
```python
# 現在（line 66-77）
if service_name == "hacker_news":
    # Hacker Newsは15記事に制限
    await service.collect(limit=15)
    logger.info(f"Service {service_name} completed with limit=15")
elif service_name in ["tech_news", "business_news"]:
    # Tech News/Business Newsは各5記事に制限
    await service.collect(limit=5)
    logger.info(f"Service {service_name} completed with limit=5")
else:
    # その他のサービスはデフォルト値を使用
    await service.collect()
    logger.info(f"Service {service_name} completed successfully")
```

↓

```python
# 変更後
if service_name == "hacker_news":
    # Hacker Newsは15記事に制限
    await service.collect(limit=15)
    logger.info(f"Service {service_name} completed with limit=15")
elif service_name in ["tech_news", "business_news"]:
    # Tech News/Business Newsは各5記事に制限
    await service.collect(limit=5)
    logger.info(f"Service {service_name} completed with limit=5")
elif service_name == "reddit":
    # Redditは10記事に制限
    await service.collect(limit=10)
    logger.info(f"Service {service_name} completed with limit=10")
else:
    # その他のサービスはデフォルト値を使用
    await service.collect()
    logger.info(f"Service {service_name} completed successfully")
```

### 4. 完了前必須チェック
- [ ] コードの構文エラーがないことを確認
- [ ] 変更内容が正しく適用されていることを確認
- [ ] 他のサービスの処理に影響がないことを確認

### 5. 動作確認
テスト実行は不要。設定変更のみで、次回のRedditサービス実行時に自動的に10件取得されることを確認。

## 期待される結果
- 各サブレディットから最大10件の投稿が取得される
- r/MachineLearningからより多くの投稿が取得される
- 合計投稿数が28件→130件（13サブレディット×10件）程度に増加

## 注意事項
- Reddit APIのレート制限に注意
- 実際の投稿数がサブレディットによって異なる可能性がある
- 次回実行時に効果を確認