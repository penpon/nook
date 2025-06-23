#!/usr/bin/env python3
"""GPTClientのテストスクリプト"""

import os
import sys
import json
from pathlib import Path

# nookモジュールをパスに追加
sys.path.append(str(Path(__file__).parent))

from nook.common.gpt_client import GPTClient

def test_gpt_client():
    """GPTClientの基本動作をテストします。"""
    print("GPTClientのテストを開始します...")
    
    try:
        # GPTClientの初期化
        client = GPTClient()
        print("✓ GPTClientの初期化成功")
        
        # 簡単なテキスト生成
        prompt = "Hello, world!"
        response = client.generate_content(prompt, max_tokens=50)
        print(f"✓ テキスト生成成功: {response[:50]}...")
        
        # ログファイルが作成されているか確認
        log_file = Path("data/api_usage/llm_usage_log.jsonl")
        if log_file.exists():
            print("✓ ログファイルが作成されました")
            
            # 最新のログエントリを表示
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_log = json.loads(lines[-1])
                    print(f"✓ 最新ログエントリ:")
                    print(f"  - サービス: {last_log['service']}")
                    print(f"  - 入力トークン: {last_log['input_tokens']}")
                    print(f"  - 出力トークン: {last_log['output_tokens']}")
                    print(f"  - コスト: ${last_log['cost_usd']:.6f}")
                    print(f"  - 累計コスト: ${last_log['cumulative_cost_usd']:.6f}")
        else:
            print("❌ ログファイルが作成されていません")
            
        print("\n✅ すべてのテストが成功しました！")
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gpt_client()