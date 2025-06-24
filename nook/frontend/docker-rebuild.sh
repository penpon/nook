#\!/bin/bash
# Dockerイメージとボリュームを完全に再構築

echo "1. 既存のコンテナを停止..."
docker-compose down -v

echo "2. ビルドキャッシュをクリア..."
docker builder prune -f

echo "3. フロントエンドイメージを削除..."
docker images | grep nook | awk '{print $3}' | xargs -r docker rmi -f

echo "4. 新しいイメージをビルド（キャッシュなし）..."
docker-compose build --no-cache frontend

echo "5. コンテナを起動..."
docker-compose up -d

echo "完了！"
