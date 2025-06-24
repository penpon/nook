# TASK-018: CLAUDE.md改善

## タスク概要
worktreeでの作業が確実に行われるよう、CLAUDE.mdのWorkerワークフローと指示書フォーマットを改善する。

## 変更予定ファイル
- CLAUDE.md

## 前提タスク
- なし（単独で実行可能）

## 作業ディレクトリ
**必ず以下のディレクトリで作業すること：**
```bash
cd worktrees/TASK-018-backend
```

## 作業内容

### 1. Workerワークフローの改善（セクション3）

現在のWorkerワークフローに以下を追加：

```markdown
### Worker ワークフロー

1. **待機**: Bossがタスクを配布するまで待機
2. **タスク受領**: 配布されたタスクファイルを確認
3. **作業ディレクトリへ移動**: 【重要】必ず指定されたworktreeに移動
   ```bash
   # タスク指示書に記載されたディレクトリに移動
   cd worktrees/TASK-XXX-backend
   # 現在のブランチを確認
   pwd && git branch --show-current
   ```
4. **worktree内で実装**: 移動確認後、作業を開始
5. **git add & commit**: 完了時は必ずコミット
6. **タスクファイル移動**: タスクファイルをpending/ → in_progress/ → completed/へ段階的に移動
```

### 2. タスク指示書フォーマットの追加（新セクション）

セクション4の後に新しいセクションを追加：

```markdown
## 4.5. タスク指示書フォーマット（Boss必須）

### 必須記載項目
すべてのタスク指示書に以下を必ず含めること：

```markdown
# TASK-XXX: [タスク名]

## タスク概要
[タスクの説明]

## 変更予定ファイル
- [具体的なファイルパス]

## 前提タスク
- [依存するタスク番号]

## 作業ディレクトリ
**必ず以下のディレクトリで作業すること：**
```bash
cd worktrees/TASK-XXX-backend
```

## 作業前チェックリスト
- [ ] 正しいworktreeディレクトリに移動したか
- [ ] `git branch --show-current`で正しいブランチか確認したか
- [ ] 変更予定ファイルの現状を確認したか

## 作業内容
[具体的な作業内容]
```

### 3. 重要なルールの更新（セクション7）

Workerの責任に以下を追加：

```markdown
### Worker の責任
- **必ず指定されたworktree内で作業**（developブランチでの直接作業は厳禁）
- 作業開始前に`pwd && git branch --show-current`で確認
- タスクファイルをpending/ → in_progress/ → completed/へ段階的に移動
- 作業完了後、DEVELOPMENT_LOG.mdへの記録（worktree内で実施）
```

### 4. よくある間違いセクション追加（新セクション10）

```markdown
## 10. よくある間違いと対策

### 1. developブランチでの直接作業
**問題**: Workerがworktreeに移動せず、メインディレクトリで作業してしまう
**対策**: 
- 作業前に必ず`cd worktrees/TASK-XXX-backend`を実行
- `git branch --show-current`で確認

### 2. タスクファイルの移動忘れ
**問題**: 作業完了後もタスクファイルがpending/に残る
**対策**: 
- in_progress/への移動: 作業開始時
- completed/への移動: 作業完了・コミット後

### 3. DEVELOPMENT_LOG.mdの更新場所
**問題**: worktree内のDEVELOPMENT_LOG.mdを更新してしまう
**対策**: メインリポジトリのDEVELOPMENT_LOG.mdを更新する
```

## 実装時の注意点
- 既存の内容は保持し、追加・修正のみ行う
- 日本語での説明を維持
- 実際の運用で発生した問題（worktree未使用）を防ぐ内容にする