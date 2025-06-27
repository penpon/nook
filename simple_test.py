#!/usr/bin/env python3
"""Hacker News APIの基本テスト"""

import asyncio
import httpx
import json

async def test_hacker_news_api():
    """Hacker News APIの基本動作をテスト"""
    print("=== Testing Hacker News API ===")
    
    base_url = "https://hacker-news.firebaseio.com/v0"
    
    async with httpx.AsyncClient() as client:
        # Top storiesを取得
        print("1. Fetching top stories...")
        response = await client.get(f"{base_url}/topstories.json")
        story_ids = response.json()
        print(f"Got {len(story_ids)} story IDs")
        print(f"First 10 IDs: {story_ids[:10]}")
        
        # 最初の5記事の詳細を取得
        print("\n2. Fetching story details...")
        for i, story_id in enumerate(story_ids[:5]):
            try:
                response = await client.get(f"{base_url}/item/{story_id}.json")
                item = response.json()
                
                print(f"\n--- Story {i+1} ---")
                print(f"ID: {story_id}")
                print(f"Title: {item.get('title', 'N/A')}")
                print(f"Score: {item.get('score', 0)}")
                print(f"URL: {item.get('url', 'N/A')}")
                print(f"Type: {item.get('type', 'N/A')}")
                
                # Launch HN系の記事かチェック
                if not item.get('url'):
                    print("-> This is a Launch HN/Ask HN style post (no URL)")
                
            except Exception as e:
                print(f"Error fetching story {story_id}: {e}")
                
        print("\n=== Test completed ===")

if __name__ == "__main__":
    asyncio.run(test_hacker_news_api())