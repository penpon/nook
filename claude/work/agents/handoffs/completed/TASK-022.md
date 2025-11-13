# TASK-022: Tech News形式統一実装

## タスク概要
Tech NewsをGitHub Trendingと同じ形式に変更する。具体的には、単一Markdownコンテンツから個別カード表示に変更し、連番付与とカテゴリタグ化を実装する。

## 変更予定ファイル
- nook/frontend/src/App.tsx
- nook/frontend/src/components/ContentCard.tsx

## 前提タスク
なし

## worktree名
worktrees/TASK-022-tech-news-format-unification

## 作業内容

### 1. App.tsxの変更
- `parseTechNewsMarkdown`関数を新規作成
  - GitHub Trendingの`parseGitHubTrendingMarkdown`関数をベースに実装
  - カテゴリセクション（## Tech blogs, ## Hatena等）を検出
  - 記事（### [タイトル](URL)）を検出
  - フィード情報と要約を抽出
  - `isCategoryHeader`, `isArticle`フラグを設定

- Tech News処理ロジックを追加
  - `selectedSource === 'tech news'`の条件分岐を追加
  - `parseTechNewsMarkdown`関数を呼び出し
  - 連番付与ロジックを実装（記事のみに連番、カテゴリヘッダーは除外）

### 2. ContentCard.tsxの変更
- `isCategoryHeader`プロパティ対応を追加
- 既存の`isLanguageHeader`と同様の表示処理を実装
- カテゴリヘッダーのスタイル統一

### 3. 実装要件

**parseTechNewsMarkdown関数の仕様:**
```typescript
function parseTechNewsMarkdown(markdown: string): any[] {
  // 1. 日付付きタイトル（# 技術ニュース記事 (2025-06-24)）を無視
  // 2. カテゴリセクション（## カテゴリ名）を検出してisCategoryHeader: trueで追加  
  // 3. 記事（### [タイトル](URL)）を検出してisArticle: trueで追加
  // 4. フィード情報（**フィード**: 名前）を抽出
  // 5. 要約情報（**要約**: 内容）を抽出
  // 6. 各記事にcategoryプロパティを追加
}
```

**期待される動作:**
- Tech Newsページでカテゴリごとに記事が分類表示される
- 各記事に連番（1, 2, 3...）が付与される
- カテゴリヘッダー（Tech blogs, Hatena等）がセクション見出しとして表示される
- GitHub Trendingと同じ見た目に統一される

### 4. テスト要件
- 既存のTech Newsデータで正常にパースされることを確認
- カテゴリヘッダーと記事が正しく分離されることを確認
- 連番が正しく付与されることを確認
- 他のソース（GitHub Trending等）に影響しないことを確認

### 5. 品質チェック
- ビルドが成功する
- 既存のテストが全て成功する  
- TypeScriptの型エラーがない
- リントエラーがない