# TASK-029: 4chan Threads形式統一実装

## タスク概要
4chan ThreadsをGitHub Trendingと同じ形式に変更する。Tech News（TASK-022）と同様の実装を行い、日付付きタイトルの削除、連番付与、カテゴリタグ化を実装する。4chan特有のタイムスタンプ情報にも対応する。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
TASK-028（Reddit Posts形式統一）

## worktree名
worktrees/TASK-029-4chan-threads-format-unification

## 作業内容

### 1. App.tsxの変更
- `parseFourchanThreadsMarkdown`関数を新規作成
  - Tech Newsの`parseTechNewsMarkdown`関数をベースに実装
  - 日付付きタイトル（# 4chan AI関連スレッド (2025-06-24)）を無視
  - カテゴリセクション（## /g/）を検出してisCategoryHeader: trueで追加
  - スレッド（### [スレッドタイトル](URL)）を検出してisArticle: trueで追加
  - タイムスタンプ情報（作成日時: <t:timestamp:F>）を抽出

- 4chan Threads処理ロジックを追加
  - `selectedSource === '4chan'`の条件分岐を追加
  - `parseFourchanThreadsMarkdown`関数を呼び出し
  - 連番付与ロジックを実装（スレッドのみに連番、カテゴリヘッダーは除外）

### 2. 実装要件

**parseFourchanThreadsMarkdown関数の仕様:**
```typescript
function parseFourchanThreadsMarkdown(markdown: string): ContentItem[] {
  // 1. 日付付きタイトル（# 4chan AI関連スレッド (2025-06-24)）を無視
  // 2. カテゴリセクション（## /板名/）を検出してisCategoryHeader: trueで追加
  // 3. スレッド（### [スレッドタイトル](URL)）を検出してisArticle: trueで追加
  // 4. 作成日時タイムスタンプを抽出してcontentに追加
  // 5. 要約情報（**要約**: 内容）を抽出
  // 6. 各スレッドにcategoryとboardプロパティを追加
}
```

**期待される動作:**
- 4chanページで4chanスレッドが個別カード表示される
- 各スレッドに連番（1, 2, 3...）が付与される
- 板名（/g/等）がカテゴリヘッダーとして表示される
- 作成日時が適切にフォーマットされて表示される
- GitHub Trendingと同じ見た目に統一される

### 3. データ形式
```markdown
# 4chan AI関連スレッド (2025-06-24)

## /g/

### [スレッドタイトル](URL)

作成日時: <t:1719235200:F>

**要約**:
1. スレッドの主な内容
2. 議論の主要ポイント（箇条書き）
3. 全体的な論調

---
```

### 4. 特殊処理要件
- Discordタイムスタンプ（<t:timestamp:F>）の適切な変換
- 板名の表示フォーマット
- 匿名掲示板特有の情報の適切な表示

### 5. 品質チェック
- ビルドが成功する
- 既存のテストが全て成功する  
- TypeScriptの型エラーがない
- リントエラーがない
- 4chan特有の情報が適切に表示される