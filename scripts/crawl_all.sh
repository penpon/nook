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
echo "Collecting Hacker News..."
python -m nook.services.run_services --service hacker_news || echo "Failed to collect Hacker News"

echo "Collecting GitHub Trending..."
python -m nook.services.run_services --service github_trending || echo "Failed to collect GitHub Trending"

echo "Collecting Papers..."
python -m nook.services.run_services --service paper || echo "Failed to collect Papers"

echo "Collecting Tech Feed..."
python -m nook.services.run_services --service tech_news || echo "Failed to collect Tech Feed"

echo "Collecting Business Feed..."
python -m nook.services.run_services --service business_news || echo "Failed to collect Business Feed"

echo "Collecting Reddit..."
python -m nook.services.run_services --service reddit || echo "Failed to collect Reddit"

echo "Collecting Zenn..."
python -m nook.services.run_services --service zenn || echo "Failed to collect Zenn"

echo "Collecting Qiita..."
python -m nook.services.run_services --service qiita || echo "Failed to collect Qiita"

echo "Collecting Note..."
python -m nook.services.run_services --service note || echo "Failed to collect Note"

echo "Collecting 4chan..."
python -m nook.services.run_services --service 4chan || echo "Failed to collect 4chan"

echo "Collecting 5chan..."
python -m nook.services.run_services --service 5chan || echo "Failed to collect 5chan"

echo "Data collection completed at $(date)"

# 仮想環境を非アクティブ化
deactivate
