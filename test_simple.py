#!/usr/bin/env python3
"""シンプルなGPTテスト"""

from nook.common.gpt_client import GPTClient
import os

print("=== シンプルGPTテスト ===")

# 環境変数確認
api_key = os.environ.get("OPENAI_API_KEY")
print(f"API Key exists: {bool(api_key)}")
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"API Key preview: {api_key[:20]}..." if api_key else "No key")

try:
    # GPTClientで短いメッセージを生成
    gpt = GPTClient()
    response = gpt.generate_content("Say hello in Japanese", max_tokens=20)
    print(f"\n✅ Success! Response: {response}")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    
# 使用量ログも確認
import json
log_file = "data/api_usage/llm_usage_log.jsonl"
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        if lines:
            last_log = json.loads(lines[-1])
            print(f"\n最後のログ: {last_log['timestamp']} - Service: {last_log['service']}")