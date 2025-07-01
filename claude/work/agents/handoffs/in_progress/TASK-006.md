# TASK-006: README.md実装済み機能の同期とAPI一覧の完全化

## タスク概要: README.mdを最新のコードベースと同期させ、実装済み機能を正確に反映する

## 変更予定ファイル:
- README.md
- nook/services/paper_summarizer/ (削除)

## 前提タスク: なし

## worktree名: worktrees/TASK-006-readme-sync-features

## 作業内容:

### 1. paper_summarizerディレクトリの削除
- nook/services/paper_summarizer/ディレクトリを削除（空のディレクトリ、arxiv_summarizerが正しい実装）

### 2. APIエンドポイント一覧の完全化
README.mdのAPIエンドポイントセクションに以下を追加：
```markdown
### その他
- `GET /health` - ヘルスチェック
- `GET /api/weather` - 天気情報取得（神奈川県）
```

### 3. サービス実行コマンドの修正
run_servicesのサービス名リストを正確に反映：
- tech_feedではなくtech_newsが正しい（run_services.py:50行目参照）
- business_feedではなくbusiness_newsが正しい

### 4. データディレクトリ構造の確認と修正
実際のディレクトリ構造と一致するよう修正

### 5. 設定ファイルセクションの追加
新たに以下のセクションを追加：
```markdown
## 設定ファイル

### RSSフィード設定
- `nook/services/tech_feed/feed.toml` - 技術ブログのRSSフィード設定
- `nook/services/business_feed/feed.toml` - ビジネスニュースのRSSフィード設定

### 掲示板設定
- `nook/services/fourchan_explorer/boards.toml` - 4chanの監視対象スレッド設定
- `nook/services/fivechan_explorer/boards.toml` - 5chの監視対象スレッド設定
```

## 完了条件:
- paper_summarizerディレクトリが削除されている
- README.mdが最新のコードベースと完全に一致している
- 天気APIエンドポイントが記載されている
- 設定ファイルの説明が追加されている