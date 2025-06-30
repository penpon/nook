# TASK-011: フロントエンドでGitHub TrendingのMarkdownをパースして個別カード化

## タスク概要: GitHub TrendingのMarkdownコンテンツを解析し、リポジトリごとに個別カードとして表示

## 変更予定ファイル: 
- nook/frontend/src/App.tsx
- nook/frontend/src/components/RepositoryCard.tsx（新規作成、必要に応じて）

## 前提タスク: TASK-010（タイトルが空になっていること）

## worktree名: worktrees/TASK-011-parse-github-markdown

## 作業内容:

1. **Markdownパース関数の作成**
   - GitHub TrendingのMarkdownを解析する関数を実装
   - 言語セクション（## Python, ## Go, ## Rust）を識別
   - 各リポジトリ（### [owner/repo](url)）を抽出
   - 説明文とスター数を抽出

2. **データ構造の定義**
   ```typescript
   interface ParsedRepository {
     name: string;        // "owner/repo"
     url: string;         // GitHub URL
     description: string; // 日本語の説明
     stars: string;       // スター数
     language: string;    // 所属言語
   }
   ```

3. **App.tsxの修正**
   - GitHub Trendingの場合の特別な処理を追加
   - Markdownをパースして複数のContentItemに変換
   - 言語セクションヘッダーとリポジトリを別々のアイテムとして扱う

4. **表示ロジックの実装**
   - パースした各リポジトリを個別のContentCardとして表示
   - 番号付けは自動的に適用される
   - リンクはすでにContentCardで処理される

5. **エラーハンドリング**
   - Markdownの形式が想定と異なる場合の処理
   - フォールバック表示の実装

## 期待される成果:
- GitHub TrendingがHacker Newsと同じように個別カードで表示される
- 各リポジトリに番号が付く
- リポジトリ名がクリック可能なリンクになる
- 言語別セクションは維持される