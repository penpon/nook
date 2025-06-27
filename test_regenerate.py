#!/usr/bin/env python3
"""24日の記事を再生成するテスト"""

from nook.services.tech_feed.tech_feed import TechFeed
from datetime import datetime

def test_regenerate():
    """TechFeedで記事を再生成"""
    print("=== Tech Feed 再生成テスト ===")
    
    tech_feed = TechFeed()
    
    try:
        # 今日の記事を生成（1日分、最大5記事でテスト）
        print("記事を収集・要約中...")
        tech_feed.run(days=1, limit=5)
        print("✅ 正常に完了しました！")
        
        # 生成されたファイルを確認
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"data/tech_feed/{today}.md"
        print(f"ファイル: {file_path}")
        
    except Exception as e:
        print(f"❌ エラー発生: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_regenerate()