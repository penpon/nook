# TASK-008: Hacker News記事をスコア順でソート

## タスク概要: フィルタリング後のHacker News記事をスコアが高い順にソートして表示する

## 変更予定ファイル:
- /Users/nana/workspace/nook/nook/services/hacker_news/hacker_news.py

## 前提タスク: TASK-006（フィルタリング条件の実装）

## worktree名: worktrees/TASK-008-hacker-news-score-sort

## 作業内容:

### 1. _get_top_storiesメソッドの修正

フィルタリング処理後、選択前にスコア順でソートする処理を追加：

```python
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

# 4.5. スコアで降順ソート（新規追加）
filtered_stories.sort(key=lambda story: story.score, reverse=True)

# 5. フィルタリング後の上位記事を選択（limitで指定された数）
selected_stories = filtered_stories[:limit]
```

### 2. 主な変更点

1. **ソート処理の追加**
   - フィルタリング後、記事選択前にソートを実行
   - `key=lambda story: story.score`でスコアを基準に指定
   - `reverse=True`で降順（高い順）にソート

2. **処理順序**
   - フィルタリング → **ソート（新規）** → 上位N件選択
   - これにより、スコアが高い記事から順に表示される

### 3. テスト確認項目

1. **スコア順の確認**
   - 生成されたJSONファイルで記事がスコア降順になっていること
   - 最初の記事が最もスコアが高いこと

2. **フィルタリング機能の維持**
   - score >= 20の条件が維持されていること
   - テキスト長フィルタリングが機能していること

3. **記事数の確認**
   - 30件（またはlimitで指定した数）が取得されていること

### 4. 実装後の確認

1. サービスを実行：`python -m nook.services.run_services --service hacker_news`
2. 生成されたJSONファイルを確認：
   ```bash
   python -c "import json; data = json.load(open('data/hacker_news/$(date +%Y-%m-%d).json')); print('スコア順:', [d['score'] for d in data[:10]])"
   ```
3. スコアが降順になっていることを確認

### 5. 期待される結果

変更前：
```
スコア順（現在）: [73, 32, 193, 24, 175, ...]  # topstoriesの順序
```

変更後：
```
スコア順（変更後）: [379, 329, 236, 193, 177, ...]  # スコア降順
```

これにより、ユーザーは最も人気のある（スコアが高い）記事から順に閲覧できるようになります。