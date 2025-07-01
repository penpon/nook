# Nook - パーソナル情報ハブ

Nookは、さまざまな情報ソース（Reddit、Hacker News、GitHub Trending、技術ブログ、arXiv論文、ニュースサイト、掲示板）からコンテンツを収集し、一元的に表示するパーソナル情報ハブです。

Discus0434氏の[Nook](https://github.com/discus0434/nook)をベースに、大幅な機能拡張と改良を行っています。

## 主な特徴

- **11種類の情報ソース**から最新情報を自動収集
- すべてのコンテンツを**日本語に自動翻訳・要約**
- **LLM API使用量追跡**機能とダッシュボード
- **ダークモード対応**（システム設定連動）
- **Docker本番環境構成**（BASIC認証、nginx対応）
- 完全に**ローカルで動作**（AWS/S3不要）

## クイックスタート（3ステップで開始）

```bash
# 1. リポジトリをクローンしてセットアップ
git clone https://github.com/Tomatio13/nook.git && cd nook
./setup.sh

# 2. 最小限のAPIキー設定（OpenAI APIキーのみ必須）
echo "OPENAI_API_KEY=your-api-key-here" >> .env.production

# 3. Docker Composeで起動
docker-compose up -d
```

ブラウザで http://localhost にアクセスして利用開始！

## こんな方におすすめ

### 🎯 ユースケース
- **技術トレンドの追跡**: GitHub Trending、Hacker News、Reddit等から最新技術動向を一括収集
- **研究論文のサーベイ**: arXiv論文を自動要約して効率的に最新研究をキャッチアップ
- **情報の一元管理**: 複数のニュースソースを1つの画面で確認、日本語で読める
- **定期的な情報収集**: cronでスケジュール実行して毎朝最新情報をチェック

### 📊 活用例
- エンジニアの朝の情報収集ルーティン
- 研究者の論文調査効率化
- プロダクトマネージャーの技術トレンド把握
- 個人の技術ブログネタ探し

## 画面イメージ
### ダークモード
![画面イメージ](assets/screenshots/dark-screenshot.png)
### ライトモード
![画面イメージ](assets/screenshots/white-screenshot.png)

## 対応サービス（11種類）

1. **Reddit Explorer** - 人気subredditの投稿を収集・要約
2. **Hacker News Retriever** - 技術ニュースとディスカッション
3. **ArXiv Summarizer** - arXiv論文の要約
4. **GitHub Trending** - 人気急上昇リポジトリ
5. **Tech Feed** - 技術ブログのRSSフィード
6. **Business Feed** 📍 - ビジネスニュースRSSフィード
7. **Zenn Explorer** 📍 - Zennの技術記事
8. **Qiita Explorer** 📍 - Qiitaの技術記事
9. **Note Explorer** 📍 - noteの技術記事
10. **4chan Explorer** 📍 - 4chanの技術系スレッド
11. **5chan Explorer** 📍 - 5chの技術系スレッド

📍 = 新規追加サービス

## 技術スタック

### バックエンド
- **Python 3.12** + **FastAPI**
- **OpenAI API** (GPT-4互換) - テキスト生成・要約
- **uv** - 高速パッケージマネージャー
- **非同期処理** - httpx, asyncio
- **エラーハンドリング** - 統一的な例外処理システム

### フロントエンド
- **React 18** + **TypeScript** + **Vite**
- **Material-UI** (@mui/material) - UIコンポーネント
- **Tailwind CSS** - スタイリング（ダークモード対応）
- **Recharts** - 使用量グラフ表示

### インフラ
- **Docker** + **Docker Compose**
- **nginx** - リバースプロキシ、BASIC認証
- **GitHub Actions** - CI/CD（予定）

## セットアップ

### 前提条件

- Docker & Docker Compose
- Python 3.12以上（ローカル開発時）
- Node.js 18以上（ローカル開発時）

### 必要なAPIキー

- **OPENAI_API_KEY** - OpenAI API (旧: GROK_API_KEY)
- **REDDIT_CLIENT_ID** / **REDDIT_CLIENT_SECRET**
- **OPENWEATHERMAP_API_KEY**

### Docker本番環境セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/Tomatio13/nook.git
cd nook

# 初期設定スクリプトの実行
chmod +x setup.sh
./setup.sh

# .env.productionの編集
# APIキーを設定してください
vim .env.production

# Docker Composeで起動
docker-compose up -d

# アクセス
# http://localhost (ポート80)
# BASIC認証のユーザー名・パスワードはsetup.sh実行時に設定
```

### ローカル開発環境セットアップ

```bash
# Python環境（uvを使用）
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# フロントエンド
cd nook/frontend
npm install

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定

# バックエンド起動
python -m nook.api.run

# フロントエンド起動（別ターミナル）
cd nook/frontend
npm run dev
```

## 使用方法

### データ収集の実行

```bash
# すべてのサービスを実行
./scripts/crawl_all.sh

# または個別に実行
python -m nook.services.run_services --service all
python -m nook.services.run_services --service reddit
python -m nook.services.run_services --service hacker_news
python -m nook.services.run_services --service github_trending
python -m nook.services.run_services --service arxiv
python -m nook.services.run_services --service tech_news
python -m nook.services.run_services --service business_news
python -m nook.services.run_services --service zenn
python -m nook.services.run_services --service qiita
python -m nook.services.run_services --service note
python -m nook.services.run_services --service 4chan
python -m nook.services.run_services --service 5chan
```

### データの保存場所

```
data/
├── reddit_explorer/      # Reddit投稿
├── hacker_news/         # Hacker Newsデータ
├── arxiv_summarizer/    # arXiv論文
├── github_trending/     # GitHubトレンド
├── tech_feed/          # 技術ブログ
├── business_feed/      # ビジネスニュース
├── zenn_explorer/      # Zenn記事
├── qiita_explorer/     # Qiita記事
├── note_explorer/      # note記事
├── fourchan_explorer/  # 4chanスレッド
├── fivechan_explorer/  # 5chスレッド
└── api_usage/          # LLM使用量ログ
```

## APIエンドポイント

### コンテンツ取得
- `GET /api/content/{source}?date={YYYY-MM-DD}`
  - source: 上記サービス名のいずれか
  - date: 取得したい日付（省略時は最新）

### LLM使用量
- `GET /api/usage` - 全体の使用量統計
- `GET /api/usage/by-service` - サービス別統計
- `GET /api/usage/daily` - 日別統計
- `GET /api/usage/history` - 使用履歴（過去30日）

### その他
- `GET /health` - ヘルスチェック
- `GET /api/weather` - 天気情報取得（神奈川県）

## 新機能

### LLM API使用量追跡
- リアルタイムでAPI使用量とコストを記録
- サービス別・日別の詳細統計
- 使用量ダッシュボード（グラフ表示）

### エラーハンドリングシステム
- 統一的なエラー処理
- 構造化エラーレスポンス
- エラーメトリクスの収集

### ダークモード対応
- システム設定に連動
- Tailwind CSSベースの実装
- すべてのコンポーネントで対応

## 設定ファイル

### RSSフィード設定
- `nook/services/tech_feed/feed.toml` - 技術ブログのRSSフィード設定
- `nook/services/business_feed/feed.toml` - ビジネスニュースのRSSフィード設定
- `nook/services/note_explorer/feed.toml` - noteのRSSフィード設定
- `nook/services/qiita_explorer/feed.toml` - QiitaのRSSフィード設定
- `nook/services/zenn_explorer/feed.toml` - ZennのRSSフィード設定

### 掲示板設定
- `nook/services/fourchan_explorer/boards.toml` - 4chanの監視対象スレッド設定
- `nook/services/fivechan_explorer/boards.toml` - 5chの監視対象スレッド設定

### その他の設定
- `nook/services/reddit_explorer/subreddits.toml` - 監視対象subreddit設定
- `nook/services/github_trending/languages.toml` - 監視対象プログラミング言語設定

## ディレクトリ構造

```
nook/
├── nook/
│   ├── api/             # FastAPI バックエンド
│   ├── common/          # 共通モジュール
│   ├── services/        # 各種サービス実装
│   └── frontend/        # React フロントエンド
├── data/                # 収集データ保存
├── logs/                # アプリケーションログ
├── nginx/               # nginx設定
├── claude/work/         # タスク管理
├── worktrees/          # Git worktree
├── scripts/            # ユーティリティスクリプト
├── docker-compose.yaml # 本番環境構成
├── Dockerfile.backend  # バックエンド用
├── Dockerfile.frontend # フロントエンド用
├── setup.sh           # セットアップスクリプト
├── CLAUDE.md          # 開発ガイドライン
└── DEVELOPMENT_LOG.md # 開発履歴
```

## 開発ガイドライン

詳細な開発ガイドラインは[CLAUDE.md](./CLAUDE.md)を参照してください。

- ロールシステム（Boss/Worker/Researcher）
- タスク管理フロー
- Git worktreeを使った並行開発
- コミット規約

開発履歴は[DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md)に記録されています。

## トラブルシューティング

### よくある問題

1. **APIキーエラー**
   - `.env`または`.env.production`にAPIキーが正しく設定されているか確認

2. **Docker起動エラー**
   - ポート80が使用中でないか確認
   - `docker-compose logs`でエラーログを確認

3. **データ取得エラー**
   - APIレート制限に達していないか確認
   - ネットワーク接続を確認

## よくある質問（FAQ）

### Q: 最小限必要なAPIキーは？
A: `OPENAI_API_KEY`のみ必須です。他のAPIキーは対応するサービスを使用する場合のみ必要です。

### Q: データはどのくらいの頻度で更新される？
A: 手動実行またはcronで設定した頻度で更新されます。推奨は1日1〜2回です。

### Q: 日本語以外の言語に対応していますか？
A: 現在は日本語のみ対応しています。元の言語での表示オプションは今後の開発予定です。

### Q: クラウドサービスは必要ですか？
A: いいえ、完全にローカルで動作します。AWS S3等は不要です。

### Q: どのくらいのストレージが必要ですか？
A: 通常の使用では1GB程度で十分です。長期間のデータを保持する場合は適宜削除してください。

### Q: 複数人で使用できますか？
A: BASIC認証で保護されているため、認証情報を共有すれば複数人で使用可能です。

### Q: モバイル対応していますか？
A: レスポンシブデザインのため、スマートフォンやタブレットでも閲覧可能です。

## ライセンス

GNU AFFERO GENERAL PUBLIC LICENSE

## 謝辞

- [Nook (Original)](https://github.com/discus0434/nook)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [Vite](https://vitejs.dev/)
- [Material-UI](https://mui.com/)
- [OpenAI](https://openai.com/)
- その他すべてのオープンソースプロジェクト
