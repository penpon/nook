"""Hacker Newsの記事を収集するサービス。"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import asyncio

from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.http_client import AsyncHTTPClient
from nook.common.decorators import handle_errors
from nook.common.exceptions import APIException


@dataclass
class Story:
    """
    Hacker News記事情報。
    
    Parameters
    ----------
    title : str
        タイトル。
    score : int
        スコア。
    url : str | None
        URL。
    text : str | None
        本文。
    """
    title: str
    score: int
    url: Optional[str] = None
    text: Optional[str] = None
    summary: str = ""



class HackerNewsRetriever(BaseService):
    """
    Hacker Newsの記事を収集するクラス。
    
    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """
    
    def __init__(self, storage_dir: str = "data"):
        """
        HackerNewsRetrieverを初期化します。
        
        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("hacker_news")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.http_client = AsyncHTTPClient()
    
    async def collect(self, limit: int = 30) -> None:
        """
        Hacker Newsの記事を収集して保存します。
        
        Parameters
        ----------
        limit : int, default=30
            取得する記事数。
        """
        stories = await self._get_top_stories(limit)
        await self._store_summaries(stories)
    
    # 同期版の互換性のためのラッパー
    def run(self, limit: int = 30) -> None:
        """同期的に実行するためのラッパー"""
        asyncio.run(self.collect(limit))
    
    @handle_errors(retries=3)
    async def _get_top_stories(self, limit: int) -> List[Story]:
        """
        トップ記事を取得します。
        
        Parameters
        ----------
        limit : int
            取得する記事数。
            
        Returns
        -------
        List[Story]
            取得した記事のリスト。
        """
        # トップストーリーのIDを取得
        response = await self.http_client.get(f"{self.base_url}/topstories.json")
        story_ids = response.json()[:limit]
        
        stories = []
        
        # 並行してストーリーを取得
        tasks = []
        for story_id in story_ids:
            tasks.append(self._fetch_story(story_id))
        
        story_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in story_results:
            if isinstance(result, Story):
                stories.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching story: {result}")
        
        # 要約を並行して生成
        await self._summarize_stories(stories)
        
        return stories
    
    async def _fetch_story(self, story_id: int) -> Optional[Story]:
        """個別のストーリーを取得"""
        try:
            response = await self.http_client.get(f"{self.base_url}/item/{story_id}.json")
            item = response.json()
            
            if "title" not in item:
                return None
            
            story = Story(
                title=item.get("title", ""),
                score=item.get("score", 0),
                url=item.get("url"),
                text=item.get("text")
            )
            
            # URLがある場合は記事の内容を取得
            if story.url and not story.text:
                await self._fetch_story_content(story)
            
            return story
        except Exception as e:
            self.logger.error(f"Error fetching story {story_id}: {e}")
            return None
    
    async def _fetch_story_content(self, story: Story) -> None:
        """記事の内容を取得"""
        try:
            # ユーザーエージェントを設定してアクセス制限を回避
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await self.http_client.get(story.url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # メタディスクリプションを取得
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if not meta_desc:
                    # Open Graphのdescriptionも試す
                    meta_desc = soup.find("meta", attrs={"property": "og:description"})
                
                if meta_desc and meta_desc.get("content"):
                    story.text = meta_desc.get("content")
                else:
                    # 本文の最初の段落を取得（より多くの段落を試す）
                    paragraphs = soup.find_all("p")
                    if paragraphs:
                        # 最初の3つの段落を結合（短すぎる段落は除外）
                        meaningful_paragraphs = [p.get_text().strip() for p in paragraphs[:5] 
                                                if len(p.get_text().strip()) > 50]
                        if meaningful_paragraphs:
                            story.text = " ".join(meaningful_paragraphs[:3])
                        else:
                            # 意味のある段落がない場合は最初の段落を使用
                            story.text = paragraphs[0].get_text().strip()
                    
                    # 本文が取得できない場合は、article要素を探す
                    if not story.text:
                        article = soup.find("article")
                        if article:
                            story.text = article.get_text()[:500]
        except Exception as e:
            # 403エラーなどのアクセス拒否エラーは頻繁に発生するため、ログレベルを下げる
            if "403" in str(e) or "Forbidden" in str(e):
                self.logger.warning(f"Access denied for {story.url}: {str(e)}")
                story.text = "アクセス制限により記事の内容を取得できませんでした。"
            else:
                self.logger.error(f"Error fetching content for {story.url}: {str(e)}")
    
    async def _summarize_stories(self, stories: List[Story]) -> None:
        """複数のストーリーを並行して要約"""
        tasks = []
        for story in stories:
            tasks.append(self._summarize_story(story))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _summarize_story(self, story: Story) -> None:
        """
        Hacker News記事を要約します。

        Parameters
        ----------
        story : Story
            要約する記事。
        """
        if not story.text:
            story.summary = "本文情報がないため要約できません。"
            return

        prompt = f"""
        以下のHacker News記事を要約してください。

        タイトル: {story.title}
        本文: {story.text}
        スコア: {story.score}

        要約は以下の形式で行い、日本語で回答してください:
        1. 記事の主な内容（1-2文）
        2. 重要なポイント（箇条書き3-5点）
        3. この記事が注目を集めた理由
        """

        system_instruction = """
        あなたはHacker News記事の要約を行うアシスタントです。
        与えられた記事を分析し、簡潔で情報量の多い要約を作成してください。
        技術的な内容は正確に、一般的な内容は分かりやすく要約してください。
        回答は必ず日本語で行ってください。専門用語は適切に翻訳し、必要に応じて英語の専門用語を括弧内に残してください。
        """

        try:
            summary = await self.gpt_client.generate_async(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=1000
            )
            story.summary = summary
            await self.rate_limit()  # API呼び出し後のレート制限
        except Exception as e:
            story.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(self, stories: List[Story]) -> None:
        """
        記事情報を保存します。
        
        Parameters
        ----------
        stories : List[Story]
            保存する記事のリスト。
        """
        today = datetime.now()
        
        # JSONでも保存（APIでの個別記事取得用）
        stories_data = []
        for story in stories:
            story_data = {
                "title": story.title,
                "score": story.score,
                "url": story.url,
                "text": story.text,
                "summary": story.summary
            }
            stories_data.append(story_data)
        
        # JSON形式で保存
        filename_json = f"{today.strftime('%Y-%m-%d')}.json"
        await self.save_json(stories_data, filename_json)
        
        # 従来のMarkdown形式も保存（互換性のため）
        content = f"# Hacker News トップ記事 ({today.strftime('%Y-%m-%d')})\n\n"
        
        for story in stories:
            title_link = f"[{story.title}]({story.url})" if story.url else story.title
            content += f"## {title_link}\n\n"
            content += f"スコア: {story.score}\n\n"
            
            # 要約があれば表示、なければ本文を表示
            if story.summary:
                content += f"**要約**:\n{story.summary}\n\n"
            elif story.text:
                content += f"{story.text[:500]}{'...' if len(story.text) > 500 else ''}\n\n"
            
            content += "---\n\n"
        
        # 保存
        filename = f"{today.strftime('%Y-%m-%d')}.md"
        await self.save_markdown(content, filename)