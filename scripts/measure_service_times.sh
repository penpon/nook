#!/bin/bash
set -euo pipefail

# スクリプトのディレクトリを基準にプロジェクトルートに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# カラー出力
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ログ関数
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }

# 結果ファイル
RESULT_FILE="${PROJECT_ROOT}/var/service_times_$(date +%Y%m%d_%H%M%S).csv"

# 環境変数を読み込む
load_env() {
    if [ -f ".env.production" ]; then
        set -a
        source .env.production
        set +a
        log_info "環境変数を .env.production から読み込みました"
    elif [ -f ".env" ]; then
        set -a
        source .env
        set +a
        log_info "環境変数を .env から読み込みました"
    fi
}

# サービス一覧
SERVICES=(
    "hacker_news"
    "github_trending"
    "zenn"
    "qiita"
    "tech_news"
    "business_news"
    "note"
    "reddit"
    "4chan"
    "5chan"
    "arxiv"
    "trendradar-zhihu"
    "trendradar-weibo"
    "trendradar-toutiao"
    "trendradar-36kr"
    "trendradar-juejin"
    "trendradar-ithome"
    "trendradar-sspai"
    "trendradar-producthunt"
)

# 計測結果を保存
echo "service,duration_seconds,status" > "$RESULT_FILE"

# 各サービスの実行時間を計測
measure_service() {
    local service_name=$1
    local start_time=$(date +%s.%N)
    local status="success"
    
    log_info "計測開始: ${service_name}"
    
    if ! uv run python -m nook.services.runner.run_services --service "$service_name" > /dev/null 2>&1; then
        status="failed"
    fi
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    echo "${service_name},${duration},${status}" >> "$RESULT_FILE"
    
    if [ "$status" = "success" ]; then
        log_success "完了: ${service_name} (${duration}秒)"
    else
        log_error "失敗: ${service_name} (${duration}秒)"
    fi
}

# メイン処理
main() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          サービス実行時間計測                                 ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    load_env
    mkdir -p "$(dirname "$RESULT_FILE")"
    
    local total_start=$(date +%s)
    
    for service in "${SERVICES[@]}"; do
        measure_service "$service"
    done
    
    local total_end=$(date +%s)
    local total_duration=$((total_end - total_start))
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          計測完了                                             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "合計時間: $((total_duration / 60))分 $((total_duration % 60))秒"
    log_info "結果ファイル: ${RESULT_FILE}"
    
    # 結果を表示
    echo ""
    echo "=== 計測結果 (秒数順) ==="
    sort -t',' -k2 -n -r "$RESULT_FILE" | tail -n +2 | while IFS=',' read -r name duration status; do
        printf "%-25s %10.2f秒  %s\n" "$name" "$duration" "$status"
    done
}

main "$@"
