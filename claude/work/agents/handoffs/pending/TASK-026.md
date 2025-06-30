# TASK-026: Qiita Articles形式統一実装

## タスク概要
Qiita ArticlesをGitHub Trendingと同じ形式に変更する。Tech News（TASK-022）と同様の実装を行い、日付付きタイトルの削除、連番付与、カテゴリタグ化を実装する。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
TASK-025（Zenn Articles形式統一）

## worktree名
worktrees/TASK-026-qiita-articles-format-unification

## 作業内容

### 1. App.tsxの変更
- `parseQiitaArticlesMarkdown`関数を新規作成
  - Tech Newsの`parseTechNewsMarkdown`関数をベースに実装
  - 日付付きタイトル（# Qiita記事 (2025-06-24)）を無視
  - カテゴリセクション（## Qiita）を検出してisCategoryHeader: trueで追加
  - 記事（### [タイトル](URL)）を検出してisArticle: trueで追加
  - フィード情報と要約を抽出

- Qiita Articles処理ロジックを追加
  - `selectedSource === 'qiita'`の条件分岐を追加
  - `parseQiitaArticlesMarkdown`関数を呼び出し
  - 連番付与ロジックを実装（記事のみに連番、カテゴリヘッダーは除外）

### 2. 実装要件

**parseQiitaArticlesMarkdown関数の仕様:**
```typescript
function parseQiitaArticlesMarkdown(markdown: string): ContentItem[] {
  // 1. 日付付きタイトル（# Qiita記事 (2025-06-24)）を無視
  // 2. カテゴリセクション（## Qiita）を検出してisCategoryHeader: trueで追加  
  // 3. 記事（### [タイトル](URL)）を検出してisArticle: trueで追加
  // 4. フィード情報（**フィード**: 名前）を抽出
  // 5. 要約情報（**要約**: 内容）を抽出
  // 6. 各記事にcategoryプロパティを追加
}
```

**期待される動作:**
- Qiita ArticlesページでQiita記事が個別カード表示される
- 各記事に連番（1, 2, 3...）が付与される
- Qiitaカテゴリヘッダーがセクション見出しとして表示される
- GitHub Trendingと同じ見た目に統一される

### 3. データ形式
```markdown
# Qiita記事 (2025-06-24)

## Qiita

### [記事タイトル](URL)

**フィード**: フィード名

**要約**:
1. 記事の主な内容（1-2文）
2. 重要なポイント（箇条書き3-5点）
3. 技術的な洞察

---
```

### 4. 品質チェック
- ビルドが成功する
- 既存のテストが全て成功する  
- TypeScriptの型エラーがない
- リントエラーがない
- Tech Newsと同様の表示形式になる