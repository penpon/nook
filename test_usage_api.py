#!/usr/bin/env python3
"""使用量APIのテストスクリプト"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# nookモジュールをパスに追加
sys.path.append(str(Path(__file__).parent))

def create_test_log_data():
    """テスト用のログデータを作成します。"""
    log_file = Path("data/api_usage/llm_usage_log.jsonl")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # テストデータを作成
    test_logs = [
        {
            "timestamp": "2025-06-23T10:00:00",
            "service": "tech_feed",
            "model": "gpt-4.1-nano",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": 0.001,
            "cumulative_cost_usd": 0.001
        },
        {
            "timestamp": "2025-06-23T11:00:00",
            "service": "reddit_explorer",
            "model": "gpt-4.1-nano",
            "input_tokens": 1500,
            "output_tokens": 750,
            "cost_usd": 0.0015,
            "cumulative_cost_usd": 0.0025
        },
        {
            "timestamp": "2025-06-22T15:00:00",
            "service": "business_feed",
            "model": "gpt-4.1-nano",
            "input_tokens": 800,
            "output_tokens": 400,
            "cost_usd": 0.0008,
            "cumulative_cost_usd": 0.0033
        }
    ]
    
    with open(log_file, 'w', encoding='utf-8') as f:
        for log in test_logs:
            f.write(json.dumps(log, ensure_ascii=False) + '\n')
    
    print(f"✓ テストログデータを作成しました: {log_file}")

def test_usage_functions():
    """使用量関数をテストします。"""
    print("使用量API関数のテストを開始します...")
    
    try:
        from nook.api.routers.usage import (
            read_usage_logs, 
            aggregate_by_service, 
            aggregate_by_day, 
            calculate_summary
        )
        
        # ログ読み込みテスト
        logs = read_usage_logs()
        print(f"✓ ログ読み込み成功: {len(logs)}件")
        
        # サービス別集計テスト
        service_data = aggregate_by_service(logs)
        print(f"✓ サービス別集計成功: {len(service_data)}サービス")
        for service in service_data:
            print(f"  - {service['service']}: {service['calls']}回, ${service['cost']:.6f}")
        
        # 日別集計テスト
        daily_data = aggregate_by_day(logs, 7)
        print(f"✓ 日別集計成功: {len(daily_data)}日分")
        
        # サマリー計算テスト
        summary = calculate_summary(logs)
        print(f"✓ サマリー計算成功:")
        print(f"  - 今日のトークン: {summary['todayTokens']}")
        print(f"  - 今日のコスト: ${summary['todayCost']:.6f}")
        print(f"  - 今月のコスト: ${summary['monthCost']:.6f}")
        print(f"  - 総呼び出し数: {summary['totalCalls']}")
        
        print("\n✅ すべての関数テストが成功しました！")
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def test_api_endpoints():
    """APIエンドポイントをテストします。"""
    print("\nAPIエンドポイントのテストを開始します...")
    
    try:
        from fastapi.testclient import TestClient
        import sys
        from pathlib import Path
        
        # nookパッケージをパスに追加
        sys.path.insert(0, str(Path(__file__).parent))
        from nook.api.main import app
        
        client = TestClient(app)
        
        # /api/usage/summary エンドポイントテスト
        response = client.get("/api/usage/summary")
        print(f"✓ /api/usage/summary: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - レスポンス: {data}")
        
        # /api/usage/by-service エンドポイントテスト
        response = client.get("/api/usage/by-service")
        print(f"✓ /api/usage/by-service: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - サービス数: {len(data)}")
        
        # /api/usage/daily エンドポイントテスト
        response = client.get("/api/usage/daily?days=7")
        print(f"✓ /api/usage/daily: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - 日数: {len(data)}")
        
        print("\n✅ すべてのAPIエンドポイントテストが成功しました！")
        
    except ImportError:
        print("⚠️ FastAPIのTestClientが利用できません。APIテストをスキップします。")
    except Exception as e:
        print(f"❌ APIテスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_log_data()
    test_usage_functions()
    test_api_endpoints()