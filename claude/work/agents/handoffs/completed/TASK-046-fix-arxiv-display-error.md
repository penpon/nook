# TASK-046: ArXiv表示エラー緊急修正

## タスク概要
http://localhost:5173/?source=arxivで発生している404エラーとApp.tsx内の条件分岐エラーを緊急修正。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし（緊急修正）

## worktree名
`worktrees/TASK-046-fix-arxiv-display-error`

## 作業内容

### 1. App.tsx内の条件分岐修正（最優先）
**問題**: L604, L971で`selectedSource === 'paper'`となっているが、実際は`'arxiv'`に変更済み
**影響**: ArXivの特別処理ロジックが動作せず、404エラーが発生

**修正箇所**:
- L604: `if (selectedSource === 'paper' && data.items[0]?.content) {` → `if (selectedSource === 'arxiv' && data.items[0]?.content) {`
- L971: `else if (selectedSource === 'paper') {` → `else if (selectedSource === 'arxiv') {`

### 2. データ取得確認
- ArXivデータが実際に生成されているかバックエンドを確認
- `data/arxiv_summarizer/2025-07-01.md`ファイルの存在確認

### 3. エラー原因の特定
- Playwrightを使用してブラウザの詳細エラーを確認
- ネットワークリクエストの確認
- API呼び出しの成功/失敗を検証

### 4. 動作確認
- 修正後にhttp://localhost:5173/?source=arxivが正常に表示されることを確認
- ArXivの論文一覧が適切に表示されることを確認
- 404エラーが解消されることを確認

## 期待される効果
- ArXivページの正常表示
- 404エラーの解消
- 特別処理ロジックの正常動作

## 注意事項
- 緊急性が高い修正のため、最優先で実行
- 修正後は必ずPlaywrightで動作確認を実施
- 他のソースに影響がないことを確認

## デバッグ手順
1. App.tsx条件分岐修正
2. ブラウザリロード
3. Playwrightでエラー確認
4. 必要に応じて追加修正実施