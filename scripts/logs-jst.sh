#!/bin/bash
# Docker logsをJST時刻で表示するスクリプト

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 使い方を表示
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "Usage: $0 [docker-compose logs options]"
    echo "Example: $0 -f -t"
    echo "         $0 --follow --timestamps backend"
    echo ""
    echo "This script converts UTC timestamps in docker-compose logs to JST"
    exit 0
fi

# docker-compose logsを実行し、Pythonスクリプトでタイムスタンプを変換
sudo docker-compose logs "$@" | python3 "$SCRIPT_DIR/convert_logs_to_jst.py"