# TASK-030: 5ch Threads形式統一実装

## タスク概要
5ch ThreadsをGitHub Trendingと同じ形式に変更する。Tech News（TASK-022）と同様の実装を行い、日付付きタイトルの削除、連番付与、カテゴリタグ化を実装する。5ch特有のスレッド番号、レス数、作成日時情報にも対応する。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
TASK-029（4chan Threads形式統一）

## worktree名
worktrees/TASK-030-5ch-threads-format-unification

## 作業内容

### 1. App.tsxの変更
- `parseFivechanThreadsMarkdown`関数を新規作成
  - Tech Newsの`parseTechNewsMarkdown`関数をベースに実装
  - 日付付きタイトル（# 5chan AI関連スレッド (2025-06-24)）を無視
  - カテゴリセクション（## 板名 (/板名/)）を検出してisCategoryHeader: trueで追加
  - スレッド（### [番号: スレッドタイトル (レス数)](URL)）を検出してisArticle: trueで追加
  - スレッド番号、レス数、作成日時を抽出

- 5ch Threads処理ロジックを追加
  - `selectedSource === '5chan'`の条件分岐を追加
  - `parseFivechanThreadsMarkdown`関数を呼び出し
  - 連番付与ロジックを実装（スレッドのみに連番、カテゴリヘッダーは除外）

### 2. 実装要件

**parseFivechanThreadsMarkdown関数の仕様:**
```typescript
function parseFivechanThreadsMarkdown(markdown: string): ContentItem[] {
  // 1. 日付付きタイトル（# 5chan AI関連スレッド (2025-06-24)）を無視
  // 2. カテゴリセクション（## 板名 (/板名/)）を検出してisCategoryHeader: trueで追加
  // 3. スレッド（### [番号: スレッドタイトル (レス数)](URL)）を検出してisArticle: trueで追加
  // 4. スレッド番号、レス数を抽出してcontentに追加
  // 5. 作成日時を抽出してcontentに追加
  // 6. 要約情報（**要約**: 内容）を抽出
  // 7. 各スレッドにcategory、board、threadNumber、replyCountプロパティを追加
}
```

**期待される動作:**
- 5chページで5chスレッドが個別カード表示される
- 各スレッドに連番（1, 2, 3...）が付与される
- 板名（CG (/cg/)等）がカテゴリヘッダーとして表示される
- スレッド番号、レス数、作成日時が適切に表示される
- GitHub Trendingと同じ見た目に統一される

### 3. データ形式
```markdown
# 5chan AI関連スレッド (2025-06-24)

## CG (/cg/)

### [123: スレッドタイトル (456)](URL)

作成日時: 2025-06-24 12:34:56

**要約**:
1. スレッドの主な内容
2. 議論の主要ポイント（箇条書き）
3. 全体的な論調

---
```

### 4. 特殊処理要件
- スレッド番号の抽出と表示
- レス数の抽出と表示
- 作成日時のフォーマット
- 板名の適切な表示（詳細名と短縮名の両方）
- タイトルからの情報分離

### 5. 品質チェック
- ビルドが成功する
- 既存のテストが全て成功する  
- TypeScriptの型エラーがない
- リントエラーがない
- 5ch特有の情報が適切に表示される