# TASK-042: バックエンド緊急修正（Hacker News表示バグ・ArXivパラメータ統一）

## タスク概要
Hacker News表示の重大なバグ修正とArXivパラメータの統一を実施。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/api/routers/content.py`

## 前提タスク
なし（緊急修正）

## worktree名
`worktrees/TASK-042-backend-critical-fixes`

## 作業内容

### 1. Hacker News表示バグ修正（最優先）
**問題**: L113, L163で`source == "hacker news"`（スペース）と条件判定しているが、実際は`"hacker-news"`（ハイフン）
**影響**: JSON処理がスキップされ、Markdown処理にフォールバック → 表示が昔の形式に戻る

**修正箇所**:
- L113: `source == "hacker news"` → `source == "hacker-news"`
- L163: `source == "hacker news"` → `source == "hacker-news"`

### 2. ArXivパラメータ統一（第1段階）
**問題**: SOURCE_MAPPINGで`"paper": "paper_summarizer"`だが、フロントエンドで`arxiv`に統一したい
**修正箇所**:
- L42: `"paper": "paper_summarizer"` → `"arxiv": "paper_summarizer"`

**注意**: この段階ではサービス名は`paper_summarizer`のまま維持（後続タスクで変更）

### 3. 修正後の動作確認
- Hacker News表示がJSON形式で正常に処理されることを確認
- ArXivパラメータが新しいキーで動作することを確認

## 期待される効果
- Hacker Newsの表示が最新の構造化された形式に復元
- フロントエンドとバックエンドでのArXivパラメータ統一
- 表示の整合性確保

## 注意事項
- 緊急性が高い修正のため、最優先で実行
- 修正後は必ず動作確認を実施
- paper → arxiv変更により、フロントエンド側も連動修正が必要