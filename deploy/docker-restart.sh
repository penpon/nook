#!/bin/bash
# Dockerコンテナの再起動（ビルドなし）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRENDRADAR_DIR="$SCRIPT_DIR/../config/trendradar"

echo "0. ディレクトリ移動..."
cd "$SCRIPT_DIR"

echo "1. 既存のコンテナを停止..."
docker-compose down

# TrendRadarコンテナも停止
echo "   [DEBUG] TrendRadar docker-compose.yml: $TRENDRADAR_DIR/docker-compose.yml"
if [ -f "$TRENDRADAR_DIR/docker-compose.yml" ]; then
    echo "   TrendRadarコンテナを停止..."
    docker-compose -f "$TRENDRADAR_DIR/docker-compose.yml" down
else
    echo "   [WARNING] TrendRadar docker-compose.yml が見つかりません"
fi

echo "2. メインコンテナを起動..."
docker-compose up -d

# TrendRadarコンテナを起動
if [ -f "$TRENDRADAR_DIR/docker-compose.yml" ]; then
    echo "3. TrendRadarコンテナを起動..."
    docker-compose -f "$TRENDRADAR_DIR/docker-compose.yml" up -d
    echo "   - trend-radar (port 8080)"
    echo "   - trend-radar-mcp (port 3333)"
else
    echo "   [WARNING] TrendRadar docker-compose.yml が見つかりません"
fi

echo "完了！"
