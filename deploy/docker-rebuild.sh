#\!/bin/bash
# Dockerイメージとボリュームを完全に再構築

echo "0. ディレクトリ移動..."
cd "$(dirname "$0")"

echo "1. 既存のコンテナを停止..."
docker-compose down -v

echo "2. ビルドキャッシュをクリア..."
docker builder prune -f

echo "3. 不要なボリュームを削除..."
docker volume rm -f $(docker volume ls -q | grep frontend-dist) 2>/dev/null || true

echo "4. 既存のイメージを削除..."
docker images | grep nook | awk '{print $3}' | xargs -r docker rmi -f

echo "5. 新しいイメージをビルド（キャッシュなし）..."
docker-compose build --no-cache

echo "6. コンテナを起動..."
docker-compose up -d

echo "完了！"
