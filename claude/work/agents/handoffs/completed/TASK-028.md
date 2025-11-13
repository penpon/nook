# TASK-028: Reddit Posts形式統一実装

## タスク概要
Reddit PostsをGitHub Trendingと同じ形式に変更する。Tech News（TASK-022）と同様の実装を行い、日付付きタイトルの削除、連番付与、カテゴリタグ化を実装する。Reddit特有の4階層構造（Tech → サブレディット → 投稿）とアップボート数にも対応する。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
TASK-027（note Articles形式統一）

## worktree名
worktrees/TASK-028-reddit-posts-format-unification

## 作業内容

### 1. App.tsxの変更
- `parseRedditPostsMarkdown`関数を新規作成
  - Tech Newsの`parseTechNewsMarkdown`関数をベースに実装
  - 日付付きタイトル（# Reddit 人気投稿 (2025-06-24)）を無視
  - カテゴリセクション（## Tech）を検出してisCategoryHeader: trueで追加
  - サブレディット（### r/subreddit名）をサブカテゴリとして処理
  - 投稿（#### [投稿タイトル](URL)）を検出してisArticle: trueで追加
  - アップボート数とリンク情報を抽出

- Reddit Posts処理ロジックを追加
  - `selectedSource === 'reddit'`の条件分岐を追加
  - `parseRedditPostsMarkdown`関数を呼び出し
  - 連番付与ロジックを実装（投稿のみに連番、カテゴリヘッダーは除外）

### 2. 実装要件

**parseRedditPostsMarkdown関数の仕様:**
```typescript
function parseRedditPostsMarkdown(markdown: string): ContentItem[] {
  // 1. 日付付きタイトル（# Reddit 人気投稿 (2025-06-24)）を無視
  // 2. カテゴリセクション（## Tech）を検出してisCategoryHeader: trueで追加
  // 3. サブレディット（### r/subreddit名）をサブカテゴリヘッダーとして追加
  // 4. 投稿（#### [投稿タイトル](URL)）を検出してisArticle: trueで追加
  // 5. アップボート数を抽出してcontentに追加
  // 6. 要約情報（**要約**: 内容）を抽出
  // 7. 各投稿にcategoryとsubredditプロパティを追加
}
```

**期待される動作:**
- Reddit PostsページでReddit投稿が個別カード表示される
- 各投稿に連番（1, 2, 3...）が付与される
- Techカテゴリヘッダーとサブレディットヘッダーが階層表示される
- アップボート数が投稿情報として表示される
- GitHub Trendingと同じ見た目に統一される

### 3. データ形式
```markdown
# Reddit 人気投稿 (2025-06-24)

## Tech

### r/programming

#### [投稿タイトル](URL)

リンク: URL

本文: 投稿本文

アップボート: 1234

**要約**:
1. 投稿の主な内容
2. 重要なポイント（箇条書き）
3. 議論の傾向

---
```

### 4. 特殊処理要件
- 4階層構造の適切な処理
- サブレディット名の表示
- アップボート数の表示
- 投稿本文の引用表示

### 5. 品質チェック
- ビルドが成功する
- 既存のテストが全て成功する  
- TypeScriptの型エラーがない
- リントエラーがない
- Reddit特有の情報が適切に表示される