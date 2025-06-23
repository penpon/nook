"""LLM API使用量APIルーター。"""

import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict

from fastapi import APIRouter, HTTPException

router = APIRouter()

# キャッシュの設定（5分間有効）
CACHE_DURATION = 300  # 5分
_cache = {}
_cache_timestamps = {}

def _get_cache_key(func_name: str, **kwargs) -> str:
    """キャッシュキーを生成します。"""
    key_parts = [func_name]
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    return "_".join(key_parts)

def _is_cache_valid(cache_key: str) -> bool:
    """キャッシュが有効かチェックします。"""
    if cache_key not in _cache_timestamps:
        return False
    return time.time() - _cache_timestamps[cache_key] < CACHE_DURATION

def _get_from_cache(cache_key: str) -> Optional[Any]:
    """キャッシュからデータを取得します。"""
    if _is_cache_valid(cache_key):
        return _cache.get(cache_key)
    return None

def _set_cache(cache_key: str, data: Any) -> None:
    """キャッシュにデータを設定します。"""
    _cache[cache_key] = data
    _cache_timestamps[cache_key] = time.time()

def read_usage_logs() -> List[Dict]:
    """ログファイルからデータを読み込みます。"""
    log_file = Path("data/api_usage/llm_usage_log.jsonl")
    
    if not log_file.exists():
        return []
    
    logs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    log_entry = json.loads(line)
                    # timestampをdatetimeオブジェクトに変換
                    log_entry['timestamp_dt'] = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    logs.append(log_entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read usage logs: {e}")
    
    return logs

def aggregate_by_service(logs: List[Dict]) -> List[Dict]:
    """サービス別に集計します。"""
    service_stats = defaultdict(lambda: {
        "calls": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "cost": 0.0,
        "lastCalled": None
    })
    
    for log in logs:
        service = log.get('service', 'unknown')
        service_stats[service]["calls"] += 1
        service_stats[service]["inputTokens"] += log.get('input_tokens', 0)
        service_stats[service]["outputTokens"] += log.get('output_tokens', 0)
        service_stats[service]["cost"] += log.get('cost_usd', 0.0)
        
        # 最後の呼び出し時刻を更新
        if (service_stats[service]["lastCalled"] is None or 
            log['timestamp_dt'] > datetime.fromisoformat(service_stats[service]["lastCalled"].replace('Z', '+00:00'))):
            service_stats[service]["lastCalled"] = log['timestamp']
    
    # 結果を整形
    result = []
    for service, stats in service_stats.items():
        result.append({
            "service": service,
            "calls": stats["calls"],
            "inputTokens": stats["inputTokens"],
            "outputTokens": stats["outputTokens"],
            "cost": round(stats["cost"], 6),
            "lastCalled": stats["lastCalled"]
        })
    
    return sorted(result, key=lambda x: x["cost"], reverse=True)

def aggregate_by_day(logs: List[Dict], days: int) -> List[Dict]:
    """日別に集計します。"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    # 指定期間内のログをフィルタリング
    filtered_logs = []
    for log in logs:
        log_date = log['timestamp_dt'].date()
        if start_date <= log_date <= end_date:
            filtered_logs.append(log)
    
    # 日別・サービス別に集計
    daily_stats = defaultdict(lambda: defaultdict(float))
    daily_totals = defaultdict(float)
    
    for log in filtered_logs:
        date_str = log['timestamp_dt'].strftime('%Y-%m-%d')
        service = log.get('service', 'unknown')
        cost = log.get('cost_usd', 0.0)
        
        daily_stats[date_str][service] += cost
        daily_totals[date_str] += cost
    
    # 結果を整形
    result = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        result.append({
            "date": date_str,
            "services": dict(daily_stats[date_str]),
            "totalCost": round(daily_totals[date_str], 6)
        })
        current_date += timedelta(days=1)
    
    return result

def calculate_summary(logs: List[Dict]) -> Dict:
    """サマリー情報を計算します。"""
    if not logs:
        return {
            "todayTokens": 0,
            "todayCost": 0.0,
            "monthCost": 0.0,
            "totalCalls": 0
        }
    
    now = datetime.now()
    today = now.date()
    month_start = today.replace(day=1)
    
    today_tokens = 0
    today_cost = 0.0
    month_cost = 0.0
    total_calls = len(logs)
    
    for log in logs:
        log_date = log['timestamp_dt'].date()
        cost = log.get('cost_usd', 0.0)
        
        if log_date == today:
            today_tokens += log.get('input_tokens', 0) + log.get('output_tokens', 0)
            today_cost += cost
        
        if log_date >= month_start:
            month_cost += cost
    
    return {
        "todayTokens": today_tokens,
        "todayCost": round(today_cost, 6),
        "monthCost": round(month_cost, 6),
        "totalCalls": total_calls
    }

@router.get("/summary")
async def get_usage_summary():
    """
    使用量のサマリー情報を返します。
    
    Returns
    -------
    Dict
        サマリー情報
    """
    cache_key = _get_cache_key("summary")
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        logs = read_usage_logs()
        summary = calculate_summary(logs)
        _set_cache(cache_key, summary)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate summary: {e}")

@router.get("/by-service")
async def get_usage_by_service():
    """
    サービス別の使用量を返します。
    
    Returns
    -------
    List[Dict]
        サービス別使用量
    """
    cache_key = _get_cache_key("by_service")
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        logs = read_usage_logs()
        service_usage = aggregate_by_service(logs)
        _set_cache(cache_key, service_usage)
        return service_usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to aggregate by service: {e}")

@router.get("/daily")
async def get_daily_usage(days: int = 30):
    """
    日別の使用量を返します。
    
    Parameters
    ----------
    days : int, default=30
        取得する日数
        
    Returns
    -------
    List[Dict]
        日別使用量
    """
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    cache_key = _get_cache_key("daily", days=days)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        logs = read_usage_logs()
        daily_usage = aggregate_by_day(logs, days)
        _set_cache(cache_key, daily_usage)
        return daily_usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to aggregate daily usage: {e}")