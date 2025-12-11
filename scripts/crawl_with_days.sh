#!/bin/bash

# 任意の取得日数(--days)を指定してクローラーを実行する補助スクリプト

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

DAYS=1
SERVICES=""
DRY_RUN=false

show_help() {
    cat <<EOF
任意の--days値を指定してデータ収集サービスを実行します。

使用方法:
    $(basename "$0") [オプション]

オプション:
    --days N             取得対象日数を指定 (1以上の整数、省略時は1)
    --services svc1,...  実行するサービスをカンマ区切りで指定 (省略時は全サービス)
    --dry-run            実行するコマンドを表示するのみ
    --help               ヘルプを表示

例:
    ./scripts/crawl_with_days.sh --days 2
    ./scripts/crawl_with_days.sh --days 3 --services tech_news,business_news
    ./scripts/crawl_with_days.sh --dry-run --days 5
EOF
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

run_service() {
    local service="$1"
    local cmd=(python -m nook.services.runner.run_services --service "$service" --days "$DAYS")

    if [ "$DRY_RUN" = true ]; then
        echo "DRY-RUN: ${cmd[*]}"
    else
        "${cmd[@]}" &
    fi
}

run_batch() {
    local batch_label="$1"
    shift

    log "$batch_label"

    for service in "$@"; do
        run_service "$service"
    done

    if [ "$DRY_RUN" = false ]; then
        wait
    fi
}

activate_environment() {
    if [ -f ".env" ]; then
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    fi

    if [ -f ".venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source .venv/bin/activate
    else
        log "Error: .venv が見つかりません。先に仮想環境を作成してください。"
        log "ヒント: uv venv"
        exit 1
    fi
}

deactivate_environment() {
    if [ "$DRY_RUN" = false ]; then
        deactivate
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)
            if [[ -z "$2" ]]; then
                echo "Error: --days の値が指定されていません" >&2
                exit 1
            fi
            DAYS="$2"
            shift 2
            ;;
        --services)
            if [[ -z "$2" ]]; then
                echo "Error: --services の値が指定されていません" >&2
                exit 1
            fi
            SERVICES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Error: 未知のオプション $1" >&2
            show_help
            exit 1
            ;;
    esac
done

if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [ "$DAYS" -lt 1 ]; then
    echo "Error: --days には1以上の整数を指定してください (指定値: $DAYS)" >&2
    exit 1
fi

SERVICE_ARRAY=()
if [ -n "$SERVICES" ] && [ "$SERVICES" != "ALL" ]; then
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
fi

log "days=$DAYS, dry_run=$DRY_RUN"

if [ "$DRY_RUN" = false ]; then
    activate_environment
fi

if [ ${#SERVICE_ARRAY[@]} -gt 0 ]; then
    log "指定サービスを実行: ${SERVICE_ARRAY[*]}"
    for raw_service in "${SERVICE_ARRAY[@]}"; do
        service="${raw_service//[[:space:]]/}"
        if [ -z "$service" ]; then
            continue
        fi
        run_service "$service"
    done
    if [ "$DRY_RUN" = false ]; then
        wait
    fi
else
    run_batch "Starting batch 1/3..." \
        hacker_news \
        github_trending \
        reddit

    run_batch "Starting batch 2/3..." \
        tech_news \
        business_news \
        arxiv \
        zenn

    run_batch "Starting batch 3/3..." \
        qiita \
        note \
        4chan \
        5chan
fi

log "All services completed"

deactivate_environment
