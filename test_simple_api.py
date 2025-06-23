#!/usr/bin/env python3
"""シンプルなAPIテスト"""

import json
from datetime import datetime
from pathlib import Path

def create_test_log():
    """テスト用ログを作成"""
    log_file = Path("data/api_usage/llm_usage_log.jsonl")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    test_logs = [
        {
            "timestamp": "2025-06-23T10:00:00",
            "service": "tech_feed",
            "model": "gpt-4.1-nano",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": 0.001,
            "cumulative_cost_usd": 0.001
        }
    ]
    
    with open(log_file, 'w', encoding='utf-8') as f:
        for log in test_logs:
            f.write(json.dumps(log, ensure_ascii=False) + '\n')
    
    print("✓ テストログ作成完了")

def test_direct_import():
    """直接インポートテスト"""
    try:
        import sys
        sys.path.insert(0, '.')
        
        from nook.api.routers.usage import read_usage_logs, calculate_summary
        
        logs = read_usage_logs()
        summary = calculate_summary(logs)
        
        print(f"✓ ログ読み込み成功: {len(logs)}件")
        print(f"✓ サマリー: 今日のコスト ${summary['todayCost']:.6f}")
        print("✅ 直接テスト成功")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_log()
    test_direct_import()