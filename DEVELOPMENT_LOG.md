# 開発ログ

## 2025年06月23日 - business_feedへのRSSフィード追加

### 作業概要
business_feedサービスに主要ビジネスメディアのRSSフィードを追加

### 背景と課題
- 既存のbusiness_feedには一部のビジネスメディアしか含まれていなかった
- 東洋経済オンライン、現代ビジネス、JBpressなどの主要メディアが不足
- feed.tomlに「bussiness」というタイポがあった

### 実装詳細
1. **feed.tomlの修正**
   - 「bussiness」を「business」に修正（タイポ修正）
   - 以下のRSSフィードを追加：
     - 東洋経済オンライン: `http://toyokeizai.net/list/feed/rss`
     - 現代ビジネス（講談社）: `https://gendai.media/list/feed/rss`
     - JBpress（日本ビジネスプレス）: `https://jbpress.ismedia.jp/list/feed/rss`

### 関連機能との連携
- business_feed.pyはtomliライブラリを使用してfeed.tomlを読み込むため、変数名変更の影響なし
- 既存の処理フローで新しいフィードも自動的に処理される

### 今後の拡張時の注意点
- ダイヤモンド・オンライン、プレジデントオンラインは統合RSSフィードのURLが不明
- Forbes JAPANはRSS提供の有無が要確認
- NewsPicksは有料会員向けコンテンツが多いため要検討

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/business_feed/feed.toml` - タイポ修正とRSSフィード追加

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

## 2025年06月23日 - APIエンドポイント404エラーの調査

### 作業概要
APIエンドポイントの404エラー調査と原因特定

### 背景と課題
- フロントエンドから`/api/content/5chan`と`/api/content/business news`へのリクエストで404エラーが報告された
- uvicornのログに複数の404エラーが記録されていた

### 調査結果
1. **APIエンドポイントの確認**
   - `/api/content/{source}`のルーティングは正しく設定されている（nook/api/routers/content.py:29）
   - `SOURCE_MAPPING`に`5chan`と`business news`は適切に定義されている
   
2. **データディレクトリの状態**
   - `/data`ディレクトリには`github_trending`、`hacker_news`、`paper_summarizer`の3つのみ存在
   - `business_feed`、`fivechan_explorer`等のディレクトリが存在しない
   - 既存データは`2025-03-02`の古いデータのみ

3. **エラーの本質**
   - 実際は404エラーではなく、APIは「No content available. Please run the services first.」を返している
   - データが生成されていないことが根本原因

### 解決方法
1. 必要なサービスを実行してデータを生成する：
   ```bash
   python -m nook.services.run_services --service business_news
   python -m nook.services.run_services --service 5chan
   ```
   
2. または全サービスを実行：
   ```bash
   python -m nook.services.run_services --service all
   ```

### 関連機能との連携
- フロントエンドの`sources`配列（nook/frontend/src/App.tsx:9）に定義されているすべてのソースに対応するデータが必要
- サービス実行スクリプト（run_services.py）にはすべてのサービスが実装されている

### 今後の拡張時の注意点
- 新しいデータソースを追加する際は、以下を確認すること：
  1. `SOURCE_MAPPING`への追加
  2. サービス実装の作成
  3. `run_services.py`への統合
  4. フロントエンドの`sources`配列への追加
  5. 定期的なデータ生成の設定（cronジョブなど）

### トラブルシューティング
- APIエンドポイントが404を返す場合は、まずcurlで直接確認：
  ```bash
  curl -s "http://localhost:8000/api/content/source_name?date=YYYY-MM-DD"
  ```
- 「No content available」の場合は、該当サービスを実行してデータを生成する

### 変更ファイル一覧
- 調査のみで変更なし

## 2025年06月23日 - AI駆動開発と画像生成AIフィードの追加

### 作業概要
Zenn、Qiita、NoteのRSSフィードにAI駆動開発と画像生成AI関連のフィードを追加

### 背景と課題
- 本プロジェクトは画像生成AIとAI駆動開発の技術情報を収集することがメイン目的
- 既存のフィード設定では重要なツールやサービスのカバレッジが不足していた
- 特にGitHub Copilot、v0、Midjourney、ComfyUIなどの主要ツールが欠けていた

### 設計判断
- 既存のfeed.tomlファイルに新しいフィードを追加する方式を採用
- カテゴリごとにコメントを追加し、管理しやすい構造に整理
- 各サービスの命名規則に従ったURL形式を使用

### 実装詳細
1. **Zennに追加したフィード**
   - AI駆動開発: githubcopilot, v0, replit, windsurf, codeium
   - 画像生成AI: midjourney, comfyui, flux, dalle
   - 既存の構文エラー（カンマ不足）も修正

2. **Qiitaに追加したフィード**
   - AI駆動開発: githubcopilot, v0, replit, windsurf, codeium, codewhisperer
   - 画像生成AI: midjourney, comfyui, flux, dalle, firefly
   - タイポ修正: qitta → qiita

3. **Noteに追加したフィード**
   - AI駆動開発: GitHubCopilot, v0, Replit, Windsurf, Codeium
   - 画像生成AI: Midjourney, ComfyUI, FLUX, DALLE, Firefly, StableDiffusion
   - 大文字小文字の使い分けはNoteの慣例に従った

### 関連機能との連携
- 各サービスのexplorer.pyは自動的に新しいフィードを認識
- フィルタリング機能により関連性の高い記事のみが収集される
- storage機能により統一されたMarkdown形式で保存

### 今後の拡張時の注意点
- 新しいAIツールの登場に応じて定期的にフィードリストの更新が必要
- 一部のタグ/ハッシュタグは存在しない可能性があるため、実行時のエラーハンドリングが重要
- 各プラットフォームのRSSフィードURL形式の変更に注意

### トラブルシューティング
- フィード取得エラーが発生した場合は、URLの有効性を確認
- タグが存在しない場合は、代替タグまたは削除を検討
- レート制限に注意し、必要に応じて取得間隔を調整

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/zenn_explorer/feed.toml` - AI駆動開発と画像生成AIフィード追加
- `/Users/nana/workspace/nook/nook/services/qiita_explorer/feed.toml` - AI駆動開発と画像生成AIフィード追加、タイポ修正
- `/Users/nana/workspace/nook/nook/services/note_explorer/feed.toml` - AI駆動開発と画像生成AIフィード追加

## 2025年06月23日 - 重点キーワード対応のフィード追加

### 作業概要
Anthropic、Claude、OpenAI、Gemini、Cursor、MCP、A2A（Agent to Agent）関連のRSSフィード追加

### 背景と課題
- ユーザーが特に重視するキーワード（anthropic, claude, claudecode, openai, codex, gemini, cursor, mcp, a2a）の実装状況を調査
- Gemini、Codex、A2A関連のカバレッジが不足していることが判明
- A2Aは2025年4月にGoogleが発表した新しいエージェント間通信プロトコルで、まったくカバーされていなかった

### 調査結果
1. **良好にカバーされているもの**
   - Anthropic/Claude/ClaudeCode: 全サービスでカバー済み
   - OpenAI: 全サービスでカバー済み、公式ブログも含む
   - Cursor: 全サービスでカバー済み、公式ブログも含む
   - MCP: Zenn、Qiitaでカバー済み

2. **不足していたもの**
   - Codex: どのサービスにも存在しない
   - Gemini: Noteのみでカバー
   - A2A (Agent to Agent): まったくカバーされていない

### 実装詳細
1. **Zennに追加**
   - gemini, googleai, agent関連フィード

2. **Qiitaに追加**
   - gemini, googleai, codex, agent関連フィード

3. **Noteに追加**
   - MCP, ModelContextProtocol, GoogleAI, Agent関連フィード

4. **tech_feedに追加**
   - Google AI公式フィード（ai.google.dev、blog.google）
   - dev.toのMCP、agent、multiagent関連フィード

5. **reddit_explorerに追加**
   - ClaudeAI, OpenAI, GoogleGemini, cursor, MachineLearning
   - LocalLLaMA, singularity, AgentGPT, AutoGPT

### 重要な発見
- MCPは「AI用のRSS」として位置づけられている（The New Stack記事）
- A2AはGoogleがMCPに対抗して発表した新プロトコル
- CursorブログはRSSフィードを提供していない（ユーザー要望あり）

### 今後の拡張時の注意点
- A2Aプロトコルは新しいため、今後フィード数が増える可能性が高い
- Codexは現在OpenAI APIに統合されているため、個別のフィードは少ない
- エージェント関連の技術は急速に発展しているため、定期的な見直しが必要

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/zenn_explorer/feed.toml` - Gemini、A2A関連フィード追加
- `/Users/nana/workspace/nook/nook/services/qiita_explorer/feed.toml` - Gemini、Codex、A2A関連フィード追加
- `/Users/nana/workspace/nook/nook/services/note_explorer/feed.toml` - MCP、A2A関連フィード追加
- `/Users/nana/workspace/nook/nook/services/tech_feed/feed.toml` - Google AI、MCP、A2A関連フィード追加
- `/Users/nana/workspace/nook/nook/services/reddit_explorer/subreddits.toml` - AI関連サブレディット大幅追加

## 2025年06月23日 - 5ch/4chan設定ファイルの修正

### 作業概要
5ch explorerと4chan explorerの設定ファイルの問題を修正

### 背景と課題
- fivechan_explorerのboards.tomlにAI関連議論が最も活発な「ネットサービス板」が欠落
- fourchan_explorerに不適切な「subreddits.toml」が存在（4chanはsubredditsではなくboardsを使用）
- 5chの一部の板設定に誤りがあった

### 調査結果
1. **5chのAI関連スレッド調査**
   - 「ネットサービス板(esite)」に【ChatGPT】AIチャット総合【Gemini・Claude】のような活発なスレッドが存在
   - ニュース速報系の板でもAI関連の話題が頻繁に取り上げられている

2. **4chanの実装確認**
   - fourchan_explorer.pyではボードリストがハードコード（["g", "sci", "biz", "pol"]）
   - subreddits.tomlファイルは一切参照されていない

### 実装詳細
1. **fivechan_explorerのboards.toml修正**
   - 追加: "esite" = "ネットサービス" (最重要)
   - 追加: "newsplus" = "ニュース速報+"
   - 追加: "news" = "ニュース速報"
   - 追加: "poverty" = "ニュー速(嫌儲)"
   - 削除: "iga" = "アニメ" (板IDの誤り)
   - 削除: "mmo", "akiba", "gogame" (AI関連の議論が少ない)

2. **fourchan_explorerの修正**
   - 不適切なsubreddits.tomlを削除
   - 新規にboards.tomlを作成（将来的な外部化に備えて）

### 関連機能との連携
- fivechan_explorer.pyは修正されたboards.tomlから板情報を読み込む
- fourchan_explorer.pyは現時点ではハードコードのままだが、将来的にboards.tomlを参照するよう改修可能

### 今後の拡張時の注意点
- 5chの板構成は変更される可能性があるため、定期的な確認が必要
- 4chanのボード設定を外部化する際は、fourchan_explorer.pyの修正も必要
- AI関連の議論が新しい板で活発になった場合は追加を検討

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/fivechan_explorer/boards.toml` - AI関連板の追加と不要な板の削除
- `/Users/nana/workspace/nook/nook/services/fourchan_explorer/subreddits.toml` - 削除（不適切なファイル）
- `/Users/nana/workspace/nook/nook/services/fourchan_explorer/boards.toml` - 新規作成（将来の外部化に備えて）

## 2025年06月23日 - 4chanボードリストの外部化

### 作業概要
fourchan_explorer.pyでハードコードされていたボードリストをboards.tomlから読み込むように修正

### 背景と課題
- ボードリストがソースコード内にハードコードされており、変更が困難
- 他のサービス（5chan explorer）は既にtomlファイルから設定を読み込んでいる
- 統一性とメンテナンス性向上のため外部化が必要

### 実装詳細
1. **tomliインポートの追加**
   - 他のサービスと同様にtomlパーサーを使用

2. **_load_boards()メソッドの追加**
   - boards.tomlから設定を読み込む
   - ファイルが存在しない場合はデフォルト値を使用
   - エラーハンドリングを実装

3. **初期化処理の修正**
   - `self.target_boards`をハードコードから`_load_boards()`の結果に変更

### 動作確認
- 既存のボードリスト（g, sci, biz, pol）が正しく読み込まれることを確認
- boards.tomlが存在しない場合でもデフォルト値で動作することを確認

### 今後の拡張時の注意点
- 新しいボードを追加する場合は、boards.tomlに追記するだけで対応可能
- ボードの説明コメントを活用して、各ボードの特徴を記録
- 有害なコンテンツが多いボードについては注意書きを記載

### 変更ファイル一覧
- `/Users/nana/workspace/nook/nook/services/fourchan_explorer/fourchan_explorer.py` - ボードリスト外部化の実装
- `/Users/nana/workspace/nook/nook/services/fourchan_explorer/boards.toml` - コメント更新