#!/usr/bin/env python3
"""Hacker Newsサービスのテスト用スクリプト"""

import asyncio
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)

from nook.services.hacker_news.hacker_news import HackerNewsRetriever

async def test_hacker_news():
    """Hacker Newsサービスをテスト"""
    print(f"=== Hacker News Test Started at {datetime.now()} ===")
    
    try:
        retriever = HackerNewsRetriever()
        print("Retriever initialized successfully")
        
        # 少数で試す
        print("Collecting 5 stories for testing...")
        await retriever.collect(limit=5)
        print("Collection completed successfully")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hacker_news())