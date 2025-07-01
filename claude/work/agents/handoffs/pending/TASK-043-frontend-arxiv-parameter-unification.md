# TASK-043: フロントエンドArXivパラメータ統一

## タスク概要
フロントエンドのArXivパラメータをpaperからarxivに統一し、表示の整合性を確保。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/config/sourceDisplayInfo.ts`

## 前提タスク
TASK-042（バックエンド修正完了後）

## worktree名
`worktrees/TASK-043-frontend-arxiv-parameter-unification`

## 作業内容

### 1. App.tsx修正
**問題**: L13で`sources = ['paper', ...]`だが、L782のメタデータでは`source: 'arxiv'`と不整合
**修正箇所**:
- L13: `const sources = ['paper', 'github', ...]` → `const sources = ['arxiv', 'github', ...]`

### 2. sourceDisplayInfo.ts修正
**問題**: L35で`'paper'`キーを使用しているが、arxivに統一したい
**修正箇所**:
- L35: `'paper': {` → `'arxiv': {`

### 3. 整合性確認
- URLパラメータ`?source=arxiv`でArXivが正常に表示されることを確認
- ArXivのタグ表示が正常に動作することを確認
- 他のソースに影響がないことを確認

## 期待される効果
- URLパラメータとメタデータの整合性確保
- ArXivタグの正常表示
- 統一されたパラメータ名による保守性向上

## 注意事項
- TASK-042のバックエンド修正完了後に実行
- 修正後は各ソースの表示確認が必要
- React Queryのキャッシュキーが変更されるため、自動的にデータ再取得される