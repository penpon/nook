# TASK-050: ArXivレイアウト退行問題の緊急修正

## タスク概要
paper → arxivへの名前変更時に漏れた条件分岐を修正し、ArXivのレイアウトを正しい状態に戻す。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/api/routers/content.py`

## 前提タスク
なし（緊急修正）

## worktree名
`worktrees/TASK-050-arxiv-layout-regression-fix`

## 作業内容

### 1. App.tsx条件分岐修正（2箇所）

#### 1.1 parseAcademicPapersMarkdown呼び出し部分（L1292）
**問題**: ArXivの特別なパース処理が動作しない
```typescript
// 修正前
if (selectedSource === 'paper' && data.items[0]?.content) {

// 修正後
if (selectedSource === 'arxiv' && data.items[0]?.content) {
```

#### 1.2 番号付けロジック部分（L1659）
**問題**: ArXivの番号付け処理が動作しない
```typescript
// 修正前
else if (selectedSource === 'paper') {

// 修正後
else if (selectedSource === 'arxiv') {
```

### 2. content.py条件分岐修正（L197）

**問題**: 全ソース取得時にArXivのタイトル変換が動作しない
```python
# 修正前
if src == "paper":

# 修正後
if src == "arxiv":
```

### 3. 修正による動作変更

修正前（現在の問題）:
- ArXivページに論文が表示されない
- 古いレイアウト（単一のMarkdownブロック）で表示される
- タイトル変換（質問文→読みやすいタイトル）が適用されない

修正後（期待される動作）:
- 各論文が個別のカードとして表示される
- 「ArXiv」カテゴリヘッダーが表示される
- タイトルが読みやすい形式に変換される（例：「🔍 研究背景と課題」）
- 番号付きで論文が表示される

### 4. 動作確認手順

1. フロントエンド確認:
   - http://localhost:5173/?source=arxivにアクセス
   - ArXivカテゴリヘッダーが表示されることを確認
   - 各論文が個別のカードで表示されることを確認
   - タイトルが変換されていることを確認

2. バックエンド確認（全ソース取得時）:
   ```bash
   curl http://localhost:8080/api/content/all
   ```
   - ArXivセクションのタイトルが変換されていることを確認

3. Playwrightでの自動確認:
   - スナップショットを撮影
   - 論文カードが表示されていることを確認

## 期待される効果
- ArXivページが正しいレイアウトで表示される
- 論文が個別のカードとして見やすく表示される
- タイトル変換により読みやすくなる
- 番号付けが正しく動作する

## 注意事項
- 他のソースに影響がないことを確認
- paper → arxivの変更漏れがないか最終確認
- キャッシュをクリアして動作確認

## 根本原因
TASK-045でpaper_summarizer → arxiv_summarizerへの変更を行った際、フロントエンドとバックエンドの一部の条件分岐が更新されず、'paper'のまま残っていたことが原因。