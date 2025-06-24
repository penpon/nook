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