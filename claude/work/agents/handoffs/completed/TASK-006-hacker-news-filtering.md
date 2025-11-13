# TASK-006: Hacker Newsフィルタリング条件の実装

## タスク概要: Hacker Newsの記事収集にフィルタリング条件を追加し、質の高い記事のみを選別する

## 変更予定ファイル: 
- /Users/nana/workspace/nook/nook/services/hacker_news/hacker_news.py

## 前提タスク: なし

## worktree名: worktrees/TASK-006-hacker-news-filtering

## 作業内容:

### 1. 定数の追加
HackerNewsRetrieverクラスの上部に以下の定数を追加：
```python
# フィルタリング条件の定数
SCORE_THRESHOLD = 20  # 最小スコア
MIN_TEXT_LENGTH = 100  # 最小テキスト長
MAX_TEXT_LENGTH = 10000  # 最大テキスト長
FETCH_LIMIT = 100  # フィルタリング前に取得する記事数
```

### 2. _get_top_storiesメソッドの改修
以下の変更を実装：

```python
async def _get_top_stories(self, limit: int) -> List[Story]:
    # 1. topstoriesから多めに記事IDを取得（100件）
    response = await self.http_client.get(f"{self.base_url}/topstories.json")
    story_ids = response.json()[:FETCH_LIMIT]  # 100件取得
    
    # 2. 並行してストーリーを取得（既存の処理）
    tasks = []
    for story_id in story_ids:
        tasks.append(self._fetch_story(story_id))
    
    story_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 3. 有効なストーリーを収集
    all_stories = []
    for result in story_results:
        if isinstance(result, Story):
            all_stories.append(result)
        elif isinstance(result, Exception):
            self.logger.error(f"Error fetching story: {result}")
    
    # 4. フィルタリング処理を追加
    filtered_stories = []
    for story in all_stories:
        # スコアフィルタリング
        if story.score < SCORE_THRESHOLD:
            continue
        
        # テキスト長フィルタリング
        text_content = story.text or ""
        text_length = len(text_content)
        
        if text_length < MIN_TEXT_LENGTH or text_length > MAX_TEXT_LENGTH:
            continue
        
        filtered_stories.append(story)
    
    # 5. フィルタリング後の上位記事を選択（limitで指定された数）
    selected_stories = filtered_stories[:limit]
    
    # 6. ログに統計情報を出力
    self.logger.info(
        f"Hacker News記事フィルタリング結果: "
        f"取得: {len(all_stories)}件, "
        f"フィルタリング後: {len(filtered_stories)}件, "
        f"選択: {len(selected_stories)}件"
    )
    
    # 7. 要約を並行して生成
    await self._summarize_stories(selected_stories)
    
    return selected_stories
```

### 3. 実装上の注意点
- 外部コンテンツ取得後のテキストも考慮する
- テキストがnullの場合は空文字列として扱う
- フィルタリング後に指定数（30件）に満たない場合でも処理を継続
- ログで統計情報を出力し、フィルタリングの効果を可視化

### 4. テスト確認項目
- スコアが20未満の記事が除外されること
- テキスト長が100文字未満または10,000文字超の記事が除外されること
- フィルタリング後も最大30件の記事が取得されること
- エラーハンドリングが正しく機能すること

### 5. 実装後の確認
- `python -m nook.services.run_services --service hacker_news`で動作確認
- ログでフィルタリング統計を確認
- 生成されるJSONとMarkdownファイルの内容を確認