# TASK-017: README.md全面更新

## タスク概要
プロジェクトの現在の状態を正確に反映するようREADME.mdを全面的に更新する。

## 変更予定ファイル
- README.md

## 前提タスク
- なし（単独で実行可能）

## 作業内容

### 1. プロジェクト概要セクションの更新
- サービス数を5個から11個に更新
- 各サービスの説明を追加:
  - Reddit Explorer
  - Hacker News Retriever
  - Paper Summarizer
  - Tech Feed
  - Business Feed（新規）
  - Zenn Explorer（新規）
  - Qiita Explorer（新規）
  - Note Explorer（新規）
  - 4chan Explorer（新規）
  - 5chan Explorer（新規）
  - OpenWeatherMap Weather（既存だが未記載）

### 2. 技術スタックの更新
- バックエンド:
  - Grok API → OpenAI API（GPT-4互換）に変更
  - uvによるパッケージ管理を明記
- フロントエンド:
  - Material-UI（@mui/material）を追加
  - Recharts（グラフライブラリ）を追加
  - Tailwind CSS（ダークモード対応）を追加

### 3. セットアップ手順の更新
- Python環境:
  ```bash
  # uvを使った環境構築
  uv venv
  source .venv/bin/activate
  uv pip install -r requirements.txt
  ```
- 環境変数:
  - GROK_API_KEY → OPENAI_API_KEY に変更
  - 新規APIキーの説明を追加
- setup.shスクリプトの説明を追加（BASIC認証設定）

### 4. Docker構成の更新
- docker-compose.dev.yamlの記述を削除
- docker-compose.yamlの3コンテナ構成を説明:
  - nginx: リバースプロキシ、BASIC認証
  - backend: FastAPIアプリケーション
  - frontend: ビルド専用コンテナ
- デプロイ手順を詳細化

### 5. ディレクトリ構造の更新
- data/配下に新サービス用ディレクトリを追加
- api_usage/（LLM使用量ログ）を追加
- claude/work/（タスク管理）を追加
- worktrees/（Git worktree）を追加

### 6. 実行方法の更新
- scripts/crawl_all.shの説明を追加
- 個別実行時のサービス名を修正:
  - paper → paper_summarizer
  - tech_news → tech_feed

### 7. 新機能セクションの追加
- LLM API使用量追跡機能（/api/usage）
- 使用量ダッシュボード
- ダークモード対応
- エラーハンドリングシステム

### 8. 開発ガイドラインセクションの追加
- CLAUDE.mdへの参照
- DEVELOPMENT_LOG.mdの説明
- ロールシステムとタスク管理の概要

### 9. APIエンドポイント一覧の追加
- 各サービスのエンドポイント
- 使用量取得エンドポイント（/api/usage）

## 注意事項
- 既存の有用な情報は保持する
- 新機能や変更点を明確に記載する
- セットアップ手順は実際に動作するものにする
- 日本語での説明を維持する