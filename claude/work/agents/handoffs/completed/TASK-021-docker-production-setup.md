# TASK-021: Docker本番環境構成の実装

## タスク概要
サーバー移行のためのDocker構成ファイルを作成し、uv対応を含む本番環境向けの設定を実装する。

## 要件
- ポート80番のみ使用
- BASIC認証の実装
- uvパッケージマネージャーの採用
- 非rootユーザーでの実行
- シンプルで管理しやすい構成

## 実装内容

### 1. nginxディレクトリとnginx.confの作成
```nginx
server {
    listen 80;
    server_name _;
    
    # アクセスログとエラーログ
    access_log /var/log/nginx/nook-access.log;
    error_log /var/log/nginx/nook-error.log;

    # BASIC認証
    auth_basic "Nook Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # ルートパス
    root /usr/share/nginx/html;
    index index.html;

    # フロントエンド静的ファイル
    location / {
        try_files $uri $uri/ /index.html;
        
        # キャッシュ設定
        add_header Cache-Control "public, max-age=3600";
    }

    # 静的アセット（長期キャッシュ）
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API リバースプロキシ
    location /api {
        proxy_pass http://backend:8000/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # バッファ設定
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # ヘルスチェック（BASIC認証なし）
    location /health {
        auth_basic off;
        proxy_pass http://backend:8000/health;
        access_log off;
    }

    # gzip圧縮
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml application/atom+xml image/svg+xml;
}
```

### 2. Dockerfile.backendの更新（uv対応）
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# uvのインストール
RUN apt-get update && apt-get install -y \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# uvをPATHに追加
ENV PATH="/root/.cargo/bin:$PATH"

# 非rootユーザーの作成
RUN useradd -m -u 1000 appuser

# requirements.txtをコピー（キャッシュ効率化）
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# アプリケーションコードをコピー
COPY nook ./nook
COPY data ./data

# ディレクトリの所有権を変更
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# 環境変数の設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ポート公開
EXPOSE 8000

# デフォルトコマンド
CMD ["python", "-m", "nook.api.run", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Dockerfile.frontendの作成/更新
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# package.jsonをコピー（キャッシュ効率化）
COPY nook/frontend/package*.json ./

# 依存関係インストール
RUN npm ci

# ソースコードをコピー
COPY nook/frontend .

# 環境変数を設定
ENV VITE_API_URL=/api

# 本番ビルド
RUN npm run build

# ビルド結果を保存
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/dist ./dist
```

### 4. docker-compose.yamlの更新
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: nook-nginx
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/.htpasswd:/etc/nginx/.htpasswd:ro
      - frontend-dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - frontend
    networks:
      - nook-network

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: nook-backend
    restart: always
    expose:
      - "8000"
    volumes:
      - ./data:/app/data
      - ./nook:/app/nook:ro
      - ./logs:/app/logs
    env_file:
      - .env.production
    networks:
      - nook-network
    user: "1000:1000"
    command: python -m nook.api.run --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: nook-frontend-builder
    volumes:
      - frontend-dist:/app/dist
    networks:
      - nook-network

networks:
  nook-network:
    driver: bridge

volumes:
  frontend-dist:
```

### 5. .env.productionの作成
```env
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here

# OpenWeatherMap API設定
OPENWEATHERMAP_API_KEY=your_openweathermap_api_key_here

# Reddit API設定
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT="python:nook:v1.0 (by /u/your_username)"

# API設定
HOST=0.0.0.0
PORT=8000

# ログレベル
LOG_LEVEL=INFO
```

### 6. setup.shの作成
```bash
#!/bin/bash

# nginxディレクトリ作成
mkdir -p nginx

# BASIC認証ファイル作成
echo "BASIC認証のユーザー名を入力してください:"
read username
htpasswd -c nginx/.htpasswd $username

# 環境変数ファイル作成
if [ ! -f .env.production ]; then
    cp .env .env.production
    echo ".env.production を作成しました。APIキーを設定してください。"
fi

# データディレクトリの権限設定
mkdir -p data logs
chmod 755 data logs

echo "セットアップ完了！"
echo "docker-compose up -d でサービスを起動してください。"
```

## 実装手順
1. nginxディレクトリを作成
2. nginx.confファイルを作成
3. Dockerfile.backendを更新（uv対応）
4. Dockerfile.frontendを作成/更新
5. docker-compose.yamlを更新
6. .env.productionテンプレートを作成
7. setup.shスクリプトを作成
8. 必要に応じてREADMEに本番環境デプロイ手順を追記

## 成功基準
- すべてのDocker構成ファイルが正しく作成される
- uvを使用したビルドが成功する
- docker-compose up -dでサービスが起動する
- ポート80でアクセスでき、BASIC認証が機能する

## 注意事項
- .htpasswdファイルは手動で作成する必要がある（setup.sh使用）
- .env.productionは.envをベースに作成し、APIキーはプレースホルダーとする
- 既存の開発環境に影響を与えないよう注意する