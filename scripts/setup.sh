#!/bin/bash

# nginxディレクトリ作成（deploy配下に存在確認）
mkdir -p deploy/nginx

# BASIC認証ファイル作成
echo "BASIC認証のユーザー名を入力してください:"
read username
htpasswd -c deploy/nginx/.htpasswd $username

# 環境変数ファイル作成
if [ ! -f .env.production ]; then
    if [ -f .env ]; then
        cp .env .env.production
    else
        touch .env.production
    fi
    echo ".env.production を作成しました。APIキーを設定してください。"
fi

# データディレクトリの権限設定
mkdir -p data logs
chmod 755 data logs

echo "セットアップ完了！"
echo "cd deploy && docker-compose up -d でサービスを起動してください。"