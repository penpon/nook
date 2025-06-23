# 開発ログ

## 2025年06月23日 - セッションID修正

### 作業概要
GitコミットメッセージのセッションID取得を修正

### 実装詳細
- Claude CodeのセッションIDは`~/.claude/statsig/statsig.session_id.*`ファイルに保存されている
- JSONファイルから`sessionID`フィールドを抽出して使用

## 2025年06月23日

### 作業概要
tech_feedサービスに画像生成AIとAI駆動開発関連の新しいRSSフィードを追加

### 背景と課題
- 本プロジェクトは画像生成AIとAI駆動開発の技術ブログ情報を収集するプロジェクト
- 既存のtech_feedに重要な技術ブログが不足していた
- 特に画像生成AI（Stable Diffusion、Midjourney、ComfyUI、FLUX.1）とAI駆動開発（Claude Code、Cursor、v0、Replit Agent）関連の情報源が欠けていた

### 設計判断
- 既存のtech_feed/feed.tomlに新カテゴリを追加する方法を選択
- 新しいサービスを作成するのではなく、既存サービスを拡張することで管理を簡素化
- RSS/Atomフィードが提供されている信頼性の高いソースを優先

### 実装詳細
1. **tech_blogsカテゴリへの追加**
   - ITmedia AI+
   - ASCII.jp（デジタルカテゴリ）
   - GIGAZINE
   - 窓の杜

2. **ai_mlカテゴリへの追加**
   - Stability AI Blog（画像生成AI）
   - Midjourney Blog（画像生成AI）
   - Anthropic Blog（AI駆動開発）
   - Microsoft Semantic Kernel Blog
   - GitHub AI/ML カテゴリ
   - Vercel Blog（v0開発元）

3. **新カテゴリ「ai_driven_dev」の追加**
   - Cursor Blog
   - dev.toのAI関連タグフィード
   - プロンプトエンジニアリングタグ

### 関連機能との連携
- tech_feed.pyのカテゴリ処理は自動的に新カテゴリを認識
- 既存の日本語フィルタリング機能が日本語技術メディアを適切に処理
- storage機能によりMarkdown形式で保存

### 今後の拡張時の注意点
- 一部のRSSフィードURLは変更される可能性があるため、定期的な確認が必要
- Replitブログなど一部のサービスはRSSフィードを提供していない可能性
- 日付フィルタリングのロジックに改善の余地あり（現在多くの記事が日付フィルタで除外）

### トラブルシューティング
- run_services.pyのサービス名不一致（techfeed → tech_news）を修正
- Python環境はCLAUDE.mdに記載の通り、必ず.venv/bin/activateしてから実行
- 必要なパッケージはuv pip install -r requirements.txtでインストール

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/tech_feed/feed.toml` - RSSフィード追加
- `/Users/nana/workspace/nook/nook/services/run_services.py` - サービス名の不一致修正
- `/Users/nana/workspace/nook/DEVELOPMENT_LOG.md` - 本ログファイル（新規作成）