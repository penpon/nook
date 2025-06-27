#!/usr/bin/env python3
"""GPT-4.1-nanoの修正テスト"""

import asyncio
from nook.services.tech_feed.tech_feed import TechFeed

async def test_tech_feed():
    """TechFeedで1記事だけテスト"""
    tech_feed = TechFeed()
    
    # フィードデータを少しだけ取得
    print("フィードを取得中...")
    feed_items = await tech_feed._get_feed_content(limit=1)
    
    if feed_items:
        print(f"1件の記事を取得しました: {feed_items[0]['title'][:50]}...")
        
        # 要約を生成
        print("要約を生成中...")
        try:
            summary = await tech_feed._summarize_text(feed_items[0]['content'][:500])
            print(f"要約成功: {summary[:100]}...")
        except Exception as e:
            print(f"要約エラー: {type(e).__name__}: {e}")
    else:
        print("記事が取得できませんでした")

if __name__ == "__main__":
    asyncio.run(test_tech_feed())