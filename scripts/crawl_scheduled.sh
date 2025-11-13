#!/bin/bash

# 拡張版クローラー：日付・時刻制御機能付き
# 使用例:
#   ./crawl_scheduled.sh --date 2025-07-01
#   ./crawl_scheduled.sh --from 2025-07-01 --to 2025-07-05
#   ./crawl_scheduled.sh --weekday monday,friday --time 09:00,18:00
#   ./crawl_scheduled.sh --business-days-only --skip-holidays
#   ./crawl_scheduled.sh --dry-run --from 2025-07-01 --to 2025-07-31

# スクリプトのディレクトリを基準にプロジェクトルートに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# デフォルト値
EXECUTE_NOW=false
DRY_RUN=false
SKIP_HOLIDAYS=false
BUSINESS_DAYS_ONLY=false
VERBOSE=false
SELECTED_SERVICES=""
TARGET_DATE=""
DATE_FROM=""
DATE_TO=""
WEEKDAYS=""
TIMES=""
SCHEDULE_FILE=""

# 日本の祝日リスト（2025年版 - 拡張可能）
declare -A JAPANESE_HOLIDAYS=(
    ["2025-01-01"]="元日"
    ["2025-01-13"]="成人の日"
    ["2025-02-11"]="建国記念の日"
    ["2025-02-23"]="天皇誕生日"
    ["2025-03-20"]="春分の日"
    ["2025-04-29"]="昭和の日"
    ["2025-05-03"]="憲法記念日"
    ["2025-05-04"]="みどりの日"
    ["2025-05-05"]="こどもの日"
    ["2025-07-21"]="海の日"
    ["2025-08-11"]="山の日"
    ["2025-09-15"]="敬老の日"
    ["2025-09-23"]="秋分の日"
    ["2025-10-13"]="スポーツの日"
    ["2025-11-03"]="文化の日"
    ["2025-11-23"]="勤労感謝の日"
)

# ヘルプ表示
show_help() {
    cat << EOF
拡張版クローラー：日付・時刻制御機能付き

使用方法:
    $(basename "$0") [オプション]

基本オプション:
    --date YYYY-MM-DD       特定の日付で実行（現在時刻との比較）
    --from YYYY-MM-DD       開始日付（--toと組み合わせて使用）
    --to YYYY-MM-DD         終了日付（--fromと組み合わせて使用）
    --weekday DAY1,DAY2     曜日指定（monday,tuesday,wednesday,thursday,friday,saturday,sunday）
    --time HH:MM,HH:MM      実行時刻指定（カンマ区切りで複数指定可能）
    
高度なオプション:
    --skip-holidays         日本の祝日をスキップ
    --business-days-only    営業日（平日かつ非祝日）のみ実行
    --schedule-file FILE    カスタムスケジュールファイルを使用
    --dry-run              実際には実行せず、実行予定を表示
    
その他のオプション:
    --services SERVICE1,SERVICE2    実行するサービスを指定（デフォルト：全サービス）
    --verbose                      詳細ログを表示
    --help                         このヘルプを表示

使用例:
    # 特定の日付で実行
    $(basename "$0") --date 2025-07-01
    
    # 日付範囲で毎日実行
    $(basename "$0") --from 2025-07-01 --to 2025-07-05
    
    # 月曜と金曜の9時と18時に実行
    $(basename "$0") --weekday monday,friday --time 09:00,18:00
    
    # 営業日のみ、祝日はスキップ
    $(basename "$0") --business-days-only --skip-holidays
    
    # dry-runで7月の実行予定を確認
    $(basename "$0") --dry-run --from 2025-07-01 --to 2025-07-31 --time 09:00,17:00

スケジュールファイル形式:
    # schedule.txt
    2025-07-01 09:00 hacker_news,github_trending
    2025-07-02 18:00 ALL
    monday,wednesday,friday 12:00 reddit,tech_news
    business_days 09:00,17:00 ALL

EOF
}

# ログ出力
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

verbose_log() {
    if [ "$VERBOSE" = true ]; then
        log "[VERBOSE] $1"
    fi
}

# 日付が祝日かチェック
is_holiday() {
    local date=$1
    [[ -n "${JAPANESE_HOLIDAYS[$date]}" ]]
}

# 営業日かチェック
is_business_day() {
    local date=$1
    local day_of_week=$(date -d "$date" +%u 2>/dev/null || date -j -f "%Y-%m-%d" "$date" +%u 2>/dev/null)
    
    # 週末チェック（土曜=6、日曜=7）
    if [ "$day_of_week" -eq 6 ] || [ "$day_of_week" -eq 7 ]; then
        return 1
    fi
    
    # 祝日チェック
    if [ "$SKIP_HOLIDAYS" = true ] && is_holiday "$date"; then
        return 1
    fi
    
    return 0
}

# 曜日が指定された曜日リストに含まれるかチェック
matches_weekday() {
    local date=$1
    local target_weekdays=$2
    
    if [ -z "$target_weekdays" ]; then
        return 0
    fi
    
    local day_name=$(date -d "$date" +%A 2>/dev/null || date -j -f "%Y-%m-%d" "$date" +%A 2>/dev/null | tr '[:upper:]' '[:lower:]')
    
    IFS=',' read -ra WEEKDAY_ARRAY <<< "$target_weekdays"
    for weekday in "${WEEKDAY_ARRAY[@]}"; do
        if [ "$day_name" = "$weekday" ]; then
            return 0
        fi
    done
    
    return 1
}

# 時刻が指定された時刻リストに含まれるかチェック
matches_time() {
    local current_time=$1
    local target_times=$2
    
    if [ -z "$target_times" ]; then
        return 0
    fi
    
    IFS=',' read -ra TIME_ARRAY <<< "$target_times"
    for time in "${TIME_ARRAY[@]}"; do
        if [ "$current_time" = "$time" ]; then
            return 0
        fi
    done
    
    return 1
}

# 実行条件をチェック
should_execute() {
    local check_date=$1
    local check_time=$2
    
    # 営業日のみモード
    if [ "$BUSINESS_DAYS_ONLY" = true ]; then
        if ! is_business_day "$check_date"; then
            verbose_log "スキップ: $check_date は営業日ではありません"
            return 1
        fi
    fi
    
    # 祝日スキップ
    if [ "$SKIP_HOLIDAYS" = true ] && is_holiday "$check_date"; then
        verbose_log "スキップ: $check_date は祝日（${JAPANESE_HOLIDAYS[$check_date]}）です"
        return 1
    fi
    
    # 曜日チェック
    if [ -n "$WEEKDAYS" ]; then
        if ! matches_weekday "$check_date" "$WEEKDAYS"; then
            verbose_log "スキップ: $check_date は指定曜日ではありません"
            return 1
        fi
    fi
    
    # 時刻チェック
    if [ -n "$TIMES" ]; then
        if ! matches_time "$check_time" "$TIMES"; then
            verbose_log "スキップ: $check_time は指定時刻ではありません"
            return 1
        fi
    fi
    
    return 0
}

# サービスを実行
execute_services() {
    local services=$1
    
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
        log "Error: .venv not found. Please create a virtual environment first."
        log "Run: uv venv"
        return 1
    fi
    
    if [ -z "$services" ] || [ "$services" = "ALL" ]; then
        # 既存のcrawl_all.shの実装を使用
        log "全サービスを実行します"
        
        # グループ1: 軽量なサービス
        log "Starting batch 1/3..."
        python -m nook.services.run_services --service hacker_news &
        python -m nook.services.run_services --service github_trending &
        python -m nook.services.run_services --service reddit &
        wait
        
        # グループ2: 中程度のサービス
        log "Starting batch 2/3..."
        python -m nook.services.run_services --service tech_news &
        python -m nook.services.run_services --service business_news &
        python -m nook.services.run_services --service arxiv &
        python -m nook.services.run_services --service zenn &
        wait
        
        # グループ3: 残りのサービス
        log "Starting batch 3/3..."
        python -m nook.services.run_services --service qiita &
        python -m nook.services.run_services --service note &
        python -m nook.services.run_services --service 4chan &
        python -m nook.services.run_services --service 5chan &
        wait
    else
        # 指定されたサービスのみ実行
        IFS=',' read -ra SERVICE_ARRAY <<< "$services"
        log "指定されたサービスを実行: ${SERVICE_ARRAY[*]}"
        
        for service in "${SERVICE_ARRAY[@]}"; do
            python -m nook.services.run_services --service "$service" &
        done
        wait
    fi
    
    # 仮想環境を非アクティブ化
    deactivate
}

# スケジュールファイルを解析
parse_schedule_file() {
    local file=$1
    
    if [ ! -f "$file" ]; then
        log "Error: スケジュールファイルが見つかりません: $file"
        return 1
    fi
    
    while IFS= read -r line; do
        # コメントと空行をスキップ
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # スケジュール行を解析
        # フォーマット: DATE TIME SERVICES
        # または: WEEKDAY TIME SERVICES
        # または: business_days TIME SERVICES
        
        echo "$line" | while read -r date_spec time_spec services_spec; do
            if [ "$date_spec" = "business_days" ]; then
                BUSINESS_DAYS_ONLY=true
                TIMES="$time_spec"
                SELECTED_SERVICES="$services_spec"
            elif [[ "$date_spec" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                TARGET_DATE="$date_spec"
                TIMES="$time_spec"
                SELECTED_SERVICES="$services_spec"
            else
                WEEKDAYS="$date_spec"
                TIMES="$time_spec"
                SELECTED_SERVICES="$services_spec"
            fi
        done
    done < "$file"
}

# メイン処理のためのスケジュール実行
run_scheduled_execution() {
    local current_date=$(date +%Y-%m-%d)
    local current_time=$(date +%H:%M)
    
    # 単一日付モード
    if [ -n "$TARGET_DATE" ]; then
        # 指定された日付で実行（現在日付との比較は行わない）
        local execution_time="${current_time}"
        
        # 時刻が指定されている場合は最初の時刻を使用
        if [ -n "$TIMES" ]; then
            execution_time=$(echo "$TIMES" | cut -d',' -f1)
        fi
        
        if should_execute "$TARGET_DATE" "$execution_time"; then
            if [ "$DRY_RUN" = true ]; then
                log "[DRY-RUN] 実行予定: $TARGET_DATE $execution_time - サービス: ${SELECTED_SERVICES:-ALL}"
            else
                log "実行: $TARGET_DATE（指定日付） - 現在時刻: $current_date $current_time"
                execute_services "$SELECTED_SERVICES"
            fi
        fi
        return
    fi
    
    # 日付範囲モード
    if [ -n "$DATE_FROM" ] && [ -n "$DATE_TO" ]; then
        # dry-runの場合は範囲内のすべての日付をチェック
        if [ "$DRY_RUN" = true ]; then
            local check_date="$DATE_FROM"
            while [ "$check_date" \< "$DATE_TO" ] || [ "$check_date" = "$DATE_TO" ]; do
                if [ -n "$TIMES" ]; then
                    IFS=',' read -ra TIME_ARRAY <<< "$TIMES"
                    for time in "${TIME_ARRAY[@]}"; do
                        if should_execute "$check_date" "$time"; then
                            log "[DRY-RUN] 実行予定: $check_date $time - サービス: ${SELECTED_SERVICES:-ALL}"
                        fi
                    done
                else
                    if should_execute "$check_date" "00:00"; then
                        log "[DRY-RUN] 実行予定: $check_date - サービス: ${SELECTED_SERVICES:-ALL}"
                    fi
                fi
                check_date=$(date -d "$check_date + 1 day" +%Y-%m-%d 2>/dev/null || date -j -v+1d -f "%Y-%m-%d" "$check_date" +%Y-%m-%d 2>/dev/null)
            done
        else
            # 実際の実行は現在日時が範囲内の場合のみ
            if [ "$current_date" \> "$DATE_FROM" ] || [ "$current_date" = "$DATE_FROM" ]; then
                if [ "$current_date" \< "$DATE_TO" ] || [ "$current_date" = "$DATE_TO" ]; then
                    if should_execute "$current_date" "$current_time"; then
                        log "実行: $current_date $current_time"
                        execute_services "$SELECTED_SERVICES"
                    fi
                fi
            fi
        fi
        return
    fi
    
    # 継続的実行モード（曜日/時刻指定のみ）
    if should_execute "$current_date" "$current_time"; then
        if [ "$DRY_RUN" = true ]; then
            log "[DRY-RUN] 実行予定: $current_date $current_time - サービス: ${SELECTED_SERVICES:-ALL}"
        else
            log "実行: $current_date $current_time"
            execute_services "$SELECTED_SERVICES"
        fi
    fi
}

# コマンドライン引数の解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            TARGET_DATE="$2"
            shift 2
            ;;
        --from)
            DATE_FROM="$2"
            shift 2
            ;;
        --to)
            DATE_TO="$2"
            shift 2
            ;;
        --weekday)
            WEEKDAYS="$2"
            shift 2
            ;;
        --time)
            TIMES="$2"
            shift 2
            ;;
        --skip-holidays)
            SKIP_HOLIDAYS=true
            shift
            ;;
        --business-days-only)
            BUSINESS_DAYS_ONLY=true
            SKIP_HOLIDAYS=true
            shift
            ;;
        --schedule-file)
            SCHEDULE_FILE="$2"
            shift 2
            ;;
        --services)
            SELECTED_SERVICES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# バリデーション
if [ -n "$DATE_FROM" ] && [ -z "$DATE_TO" ]; then
    log "Error: --from を指定する場合は --to も必要です"
    exit 1
fi

if [ -n "$DATE_TO" ] && [ -z "$DATE_FROM" ]; then
    log "Error: --to を指定する場合は --from も必要です"
    exit 1
fi

# メイン実行
log "拡張版クローラー開始"
verbose_log "設定: TARGET_DATE=$TARGET_DATE, DATE_FROM=$DATE_FROM, DATE_TO=$DATE_TO"
verbose_log "設定: WEEKDAYS=$WEEKDAYS, TIMES=$TIMES"
verbose_log "設定: SKIP_HOLIDAYS=$SKIP_HOLIDAYS, BUSINESS_DAYS_ONLY=$BUSINESS_DAYS_ONLY"
verbose_log "設定: DRY_RUN=$DRY_RUN, SERVICES=$SELECTED_SERVICES"

if [ -n "$SCHEDULE_FILE" ]; then
    parse_schedule_file "$SCHEDULE_FILE"
fi

run_scheduled_execution

log "拡張版クローラー終了"