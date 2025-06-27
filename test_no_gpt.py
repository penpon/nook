#!/usr/bin/env python3
"""GPTクライアントなしでHacker Newsサービスをテスト"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# PYTHONPATHを設定
sys.path.insert(0, str(Path(__file__).parent))

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 環境変数設定（テスト用）
os.environ['OPENAI_API_KEY'] = 'test_key'

from nook.services.hacker_news.hacker_news import HackerNewsRetriever, Story
from nook.common.http_client import AsyncHTTPClient

class TestHackerNewsRetriever(HackerNewsRetriever):
    """テスト用のHacker Newsレトリーバー（GPT依存を除去）"""
    
    def __init__(self, storage_dir: str = "data"):
        # BaseServiceの初期化をスキップして直接初期化
        self.service_name = "hacker_news"
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.http_client = AsyncHTTPClient()
        self.logger = logging.getLogger("hacker_news")
        
        # ストレージディレクトリの作成
        self.storage_dir = Path(storage_dir) / "hacker_news"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def _summarize_story(self, story: Story) -> None:
        """要約をスキップ（テスト用）"""
        story.summary = f"[テスト] {story.title}の要約（GPTクライアント未使用）"
    
    async def save_json(self, data, filename):
        """JSONファイルを保存"""
        import json
        file_path = self.storage_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"Saved JSON: {file_path}")
    
    async def save_markdown(self, content, filename):
        """Markdownファイルを保存"""
        file_path = self.storage_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Saved Markdown: {file_path}")

async def test_hacker_news():
    """Hacker Newsサービスをテスト"""
    print(f"=== Hacker News Test Started at {datetime.now()} ===")
    
    try:
        retriever = TestHackerNewsRetriever()
        print("Test retriever initialized successfully")
        
        # 30記事を取得
        print("Collecting 30 stories...")
        await retriever.collect(limit=30)
        print("Collection completed successfully")
        
        # データファイルの確認
        data_dir = Path("data/hacker_news")
        today = datetime.now().strftime('%Y-%m-%d')
        
        json_file = data_dir / f"{today}.json"
        md_file = data_dir / f"{today}.md"
        
        if json_file.exists():
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"JSON file created with {len(data)} stories")
        else:
            print("JSON file not found")
            
        if md_file.exists():
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Markdown file created with {len(content)} characters")
        else:
            print("Markdown file not found")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hacker_news())