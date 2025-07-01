#!/bin/bash

# スクリプトのディレクトリを基準にプロジェクトルートに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 環境変数を読み込む
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Python仮想環境をアクティベート
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Please create a virtual environment first."
    echo "Run: uv venv"
    exit 1
fi

echo "Starting data collection services..."
echo "Date: $(date)"

# デバッグ: 環境変数の確認
echo "DEBUG: Checking OPENAI_API_KEY..."
if [ -n "$OPENAI_API_KEY" ]; then
    echo "DEBUG: OPENAI_API_KEY is set (length: ${#OPENAI_API_KEY})"
else
    echo "DEBUG: OPENAI_API_KEY is NOT set"
fi

# 各サービスを実行（エラーが発生しても続行）
echo "Launching all services in parallel..."

# 全サービスをバックグラウンドで実行
python -m nook.services.run_services --service hacker_news &
python -m nook.services.run_services --service github_trending &
python -m nook.services.run_services --service arxiv &
python -m nook.services.run_services --service tech_news &
python -m nook.services.run_services --service business_news &
python -m nook.services.run_services --service reddit &
python -m nook.services.run_services --service zenn &
python -m nook.services.run_services --service qiita &
python -m nook.services.run_services --service note &
python -m nook.services.run_services --service 4chan &
python -m nook.services.run_services --service 5chan &

# 全プロセスの完了を待つ
wait

echo "All services completed"

echo "Data collection completed at $(date)"

# 仮想環境を非アクティブ化
deactivate
