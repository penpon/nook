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
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# 設定
readonly MAX_PARALLEL=4
readonly LOG_DIR="${PROJECT_ROOT}/var/logs"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ログ関数
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }

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
    else
        log_warn ".env ファイルが見つかりません"
    fi
}

# サービス実行関数
run_service() {
    local service_name=$1
    local log_file="${LOG_DIR}/${service_name}_${TIMESTAMP}.log"
    
    log_info "開始: ${service_name}"
    
    if uv run python -m nook.services.runner.run_services --service "$service_name" > "$log_file" 2>&1; then
        log_success "完了: ${service_name}"
        return 0
    else
        log_error "失敗: ${service_name} (ログ: ${log_file})"
        return 1
    fi
}

# バッチ実行関数（並列実行を制御）
run_batch() {
    local batch_name=$1
    shift
    local services=("$@")
    local pids=()
    local failed=0
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log_info "バッチ開始: ${batch_name} (${#services[@]} サービス)"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    for service in "${services[@]}"; do
        run_service "$service" &
        pids+=($!)
        
        # 並列実行数の制限
        while [ ${#pids[@]} -ge $MAX_PARALLEL ]; do
            local new_pids=()
            for pid in "${pids[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    new_pids+=("$pid")
                else
                    wait "$pid" || ((failed++))
                fi
            done
            pids=("${new_pids[@]}")
            [ ${#pids[@]} -ge $MAX_PARALLEL ] && sleep 1
        done
    done
    
    # 残りのプロセスを待機
    for pid in "${pids[@]}"; do
        wait "$pid" || ((failed++))
    done
    
    if [ $failed -eq 0 ]; then
        log_success "バッチ完了: ${batch_name}"
    else
        log_warn "バッチ完了: ${batch_name} (${failed} 件の失敗)"
    fi
    
    return $failed
}

# メイン処理
main() {
    local start_time=$(date +%s)
    local total_failed=0
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Nook Data Collection - 全サービス実行               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "開始時刻: $(date)"
    log_info "プロジェクトルート: ${PROJECT_ROOT}"
    
    # 環境変数の読み込み
    load_env
    
    # ログディレクトリの作成
    mkdir -p "$LOG_DIR"
    
    # APIキーの確認
    if [ -n "${OPENAI_API_KEY:-}" ]; then
        log_info "OPENAI_API_KEY: 設定済み (${#OPENAI_API_KEY} 文字)"
    else
        log_warn "OPENAI_API_KEY: 未設定"
    fi
    
    # ==========================================================================
    # バッチ1: 軽量・高速サービス（外部API依存なし）
    # ==========================================================================
    run_batch "軽量サービス" \
        "hacker_news" \
        "github_trending" \
        "zenn" \
        "qiita" \
    || ((total_failed+=$?))
    
    # ==========================================================================
    # バッチ2: 中程度のサービス（RSS/スクレイピング）
    # ==========================================================================
    run_batch "RSSフィード・探索サービス" \
        "tech_news" \
        "business_news" \
        "note" \
        "reddit" \
    || ((total_failed+=$?))
    
    # ==========================================================================
    # バッチ3: 掲示板サービス（レート制限考慮）
    # ==========================================================================
    run_batch "掲示板サービス" \
        "4chan" \
        "5chan" \
        "arxiv" \
    || ((total_failed+=$?))
    
    # ==========================================================================
    # バッチ4: TrendRadar中国系サービス（外部MCP接続）
    # ==========================================================================
    run_batch "TrendRadar (中国系)" \
        "trendradar-zhihu" \
        "trendradar-weibo" \
        "trendradar-toutiao" \
        "trendradar-36kr" \
        "trendradar-wallstreetcn" \
        "trendradar-tencent" \
    || ((total_failed+=$?))
    
    # ==========================================================================
    # バッチ5: TrendRadar技術系サービス（外部MCP接続）
    # ==========================================================================
    run_batch "TrendRadar (技術系)" \
        "trendradar-juejin" \
        "trendradar-ithome" \
        "trendradar-sspai" \
        "trendradar-producthunt" \
        "trendradar-freebuf" \
        "trendradar-v2ex" \
    || ((total_failed+=$?))
    
    # 完了サマリー
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                       実行完了サマリー                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    log_info "終了時刻: $(date)"
    log_info "実行時間: ${minutes}分 ${seconds}秒"
    log_info "ログディレクトリ: ${LOG_DIR}"
    
    if [ $total_failed -eq 0 ]; then
        log_success "すべてのサービスが正常に完了しました"
    else
        log_warn "${total_failed} 件のエラーが発生しました"
    fi
    
    return $total_failed
}

# スクリプト実行
main "$@"
