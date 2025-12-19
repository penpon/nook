#!/bin/bash
# Dockerイメージとボリュームを完全に再構築

SCRIPT_DIR="$(dirname "$0")"
TRENDRADAR_DIR="$(dirname "$SCRIPT_DIR")/config/trendradar"

echo "0. ディレクトリ移動..."
cd "$SCRIPT_DIR"

echo "1. 既存のコンテナを停止..."
docker-compose down -v

# TrendRadarコンテナも停止
if [ -f "$TRENDRADAR_DIR/docker-compose.yml" ]; then
    echo "   TrendRadarコンテナを停止..."
    docker-compose -f "$TRENDRADAR_DIR/docker-compose.yml" down
fi

echo "2. ビルドキャッシュをクリア..."
docker builder prune -f

echo "3. 不要なボリュームを削除..."
docker volume rm -f $(docker volume ls -q | grep frontend-dist) 2>/dev/null || true

echo "4. 既存のイメージを削除..."
docker images | grep nook | awk '{print $3}' | xargs -r docker rmi -f

echo "5. 新しいイメージをビルド（キャッシュなし）..."
docker-compose build --no-cache

echo "6. メインコンテナを起動..."
docker-compose up -d

# TrendRadarコンテナを起動
if [ -f "$TRENDRADAR_DIR/docker-compose.yml" ]; then
    echo "7. TrendRadarコンテナを起動..."
    docker-compose -f "$TRENDRADAR_DIR/docker-compose.yml" up -d
    echo "   - trend-radar (port 8080)"
    echo "   - trend-radar-mcp (port 3333)"
fi

echo "完了！"
