# Nook - パーソナル情報ハブ

Nookは、複数の情報ソース（Reddit、Hacker News、GitHub Trending、arXiv論文、Zenn、Qiita、知乎など）からコンテンツを収集し、日本語に翻訳・要約して一元表示するパーソナル情報ハブです。

## 技術スタック

- **バックエンド**: Python 3.12+ / FastAPI / OpenAI API
- **フロントエンド**: React 18 / TypeScript / Vite / Tailwind CSS
- **インフラ**: Docker / Docker Compose / nginx

## ディレクトリ構成

```
nook/
├── nook/                # バックエンドソースコード
│   ├── api/             # FastAPI エンドポイント
│   ├── core/            # 共通コンポーネント
│   └── services/        # 12種の情報収集サービス
├── frontend/            # フロントエンドソースコード (React/Vite)
├── tests/               # テストコード
├── deploy/              # Docker/nginx本番環境設定
├── data/                # 収集データ保存先
└── scripts/             # ユーティリティスクリプト
```

## セットアップ

### 前提条件

- Docker & Docker Compose（本番環境）
- Python 3.12+（ローカル開発）
- Node.js 18+（ローカル開発）

### Docker本番環境（推奨）

```bash
git clone https://github.com/Tomatio13/nook.git && cd nook
./scripts/setup.sh
echo "OPENAI_API_KEY=your-api-key" >> .env.production
cd deploy && docker-compose up -d
```

http://localhost でアクセス可能