# TASK-007: ArXivとHacker Newsのパース関数修正

## タスク概要
ArXiv（Academic Papers）とHacker Newsの記事が表示されない問題を修正する。Markdownファイルでは`##`（H2）で記事タイトルを記載しているが、パース関数は`###`（H3）を探しているため、記事が検出されない。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
なし

## worktree名
worktrees/TASK-007-fix-arxiv-hackernews-parsing

## 作業内容

### 1. parseAcademicPapersMarkdown関数の修正（App.tsx 691-692行目）
- 正規表現を`/^###\s*\[([^\]]+)\]\(([^)]+)\)$/`から`/^##\s*\[([^\]]+)\]\(([^)]+)\)$/`に変更
- 3つのハッシュマーク（###）を2つ（##）に修正

### 2. parseHackerNewsMarkdown関数の修正（App.tsx 754-755行目）
- 正規表現を`/^###\s*\[([^\]]+)\]\(([^)]+)\)$/`から`/^##\s*\[([^\]]+)\]\(([^)]+)\)$/`に変更
- 3つのハッシュマーク（###）を2つ（##）に修正

### 実際のMarkdownファイル形式
```markdown
## [記事タイトル](URL)

内容...
```

### テスト確認事項
- ArXivの論文一覧が正しく表示されること
- Hacker Newsの記事一覧が正しく表示されること
- 記事タイトル、URL、内容が正しく抽出されること
- カテゴリヘッダー（ArXiv、Hacker News）が正しく表示されること