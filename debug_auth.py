#!/usr/bin/env python3
import os
import sys

import openai
from dotenv import load_dotenv
from tenacity import RetryError

# .envを読み込む
load_dotenv()

print("=== 環境変数チェック ===")
api_key = os.environ.get("OPENAI_API_KEY")
print(f"OPENAI_API_KEY exists: {bool(api_key)}")
if api_key:
    print(f"Key starts with: {api_key[:7]}...")
    print(f"Key length: {len(api_key)}")

print("\n=== OpenAI クライアント初期化 ===")
try:
    client = openai.OpenAI(api_key=api_key)
    print("Client created successfully")
except Exception as e:
    print(f"Error creating client: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n=== gpt-4.1-nano テスト ===")
try:
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10,
    )
    print("gpt-4.1-nano works!")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    if hasattr(e, "response"):
        print(f"Response status: {e.response.status_code}")
        print(f"Response body: {e.response.text}")

print("\n=== GPTClient からのテスト ===")
try:
    from nook.common.gpt_client import GPTClient

    gpt = GPTClient()
    print("GPTClient created successfully")

    # generate_content メソッドのテスト
    result = gpt.generate_content("Hello", max_tokens=10)
    print(f"generate_content works! Response: {result[:50]}...")
except RetryError as e:
    print(f"RetryError occurred: {e}")
    # 内部のエラーを取得
    if e.last_attempt.failed:
        inner_error = e.last_attempt.exception()
        if inner_error:
            print(f"Inner error: {type(inner_error).__name__}: {inner_error}")
            if hasattr(inner_error, "response"):
                print(f"Response status: {inner_error.response.status_code}")
                print(f"Response body: {inner_error.response.text}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
