# TASK-009: Hacker Newsのスコアソート実装

## タスク概要: 
Hacker Newsの記事をスコアの高い順（降順）にソートして表示する機能を実装する。現在、記事は保存された順番で表示されているため、スコアが高い記事が必ずしも上位に表示されていない。

## 変更予定ファイル: 
- `/Users/nana/workspace/nook/nook/api/routers/content.py`

## 前提タスク: 
なし

## worktree名: 
worktrees/TASK-009-hacker-news-score-sort

## 作業内容:

### 1. 問題の詳細
現在、Hacker Newsの記事は以下のような順番で表示されている：
- 1位: スコア73
- 2位: スコア32
- 3位: スコア193（最高スコアなのに3位）
- 4位: スコア24
- 5位: スコア175

正しくは、スコアの高い順（193, 175, 167, 133...）で表示されるべき。

### 2. 修正内容
`/Users/nana/workspace/nook/nook/api/routers/content.py`で以下の修正を行う：

#### Hacker News単独表示の修正（78-95行目付近）
```python
# 現在のコード
for i, story in enumerate(stories_data):
    # ...処理...

# 修正後のコード
# スコアで降順ソート
sorted_stories = sorted(stories_data, key=lambda x: x.get('score', 0), reverse=True)
for i, story in enumerate(sorted_stories):
    # ...処理...
```

#### 全ソース表示の修正（112-129行目付近）
同様に、allソースの場合もHacker Newsの記事をスコア順でソートする：
```python
# 現在のコード
for i, story in enumerate(stories_data):
    # ...処理...

# 修正後のコード
# スコアで降順ソート
sorted_stories = sorted(stories_data, key=lambda x: x.get('score', 0), reverse=True)
for i, story in enumerate(sorted_stories):
    # ...処理...
```

### 3. テスト方法
1. 開発サーバーを起動
2. Playwrightまたはブラウザで`http://localhost:5173`にアクセス
3. Hacker Newsソースを選択
4. 記事がスコアの高い順に表示されることを確認
   - 最高スコアの記事が1番目に表示される
   - 2番目以降もスコアの降順で表示される

### 4. 注意事項
- `story.get('score', 0)`を使用して、scoreフィールドが存在しない場合のエラーを防ぐ
- ソートは降順（reverse=True）で行う
- 既存のテストがある場合は、テストも実行して互換性を確認する