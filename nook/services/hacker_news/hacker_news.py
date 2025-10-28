"""Hacker Newsの記事を収集するサービス。"""

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.decorators import handle_errors
from nook.common.dedup import DedupTracker
from nook.common.daily_merge import merge_records


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
    url: str | None = None
    text: str | None = None
    summary: str = ""


# フィルタリング条件の定数
SCORE_THRESHOLD = 20  # 最小スコア
MIN_TEXT_LENGTH = 100  # 最小テキスト長
MAX_TEXT_LENGTH = 10000  # 最大テキスト長
FETCH_LIMIT: int | None = None  # フィルタリング前に取得する記事数（Noneの場合は制限なし）
MAX_STORY_LIMIT = 15  # 保存する記事数の上限


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
        self.http_client = None  # setup_http_clientで初期化
        self.blocked_domains = self._load_blocked_domains()

    async def collect(self, limit: int = MAX_STORY_LIMIT) -> None:
        """
        Hacker Newsの記事を収集して保存します。
        
        Parameters
        ----------
        limit : int, default=15
            取得する記事数。
        """
        limit = min(limit, MAX_STORY_LIMIT)

        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        dedup_tracker = await self._load_existing_titles()

        stories = await self._get_top_stories(limit, dedup_tracker)
        await self._store_summaries(stories)

    # 同期版の互換性のためのラッパー
    def run(self, limit: int = MAX_STORY_LIMIT) -> None:
        """同期的に実行するためのラッパー"""
        asyncio.run(self.collect(limit))

    async def _load_existing_titles(self) -> DedupTracker:
        tracker = DedupTracker()
        today = datetime.now().strftime("%Y-%m-%d")
        filename_json = f"{today}.json"
        try:
            if await self.storage.exists(filename_json):
                data = await self.load_json(filename_json)
                if data:
                    for item in data:
                        title = item.get("title")
                        if title:
                            tracker.add(title)
            else:
                content = self.storage.load_markdown("hacker_news", datetime.now())
                if content:
                    for match in re.finditer(r"^## \[(.+?)\]", content, re.MULTILINE):
                        tracker.add(match.group(1))
                    for match in re.finditer(
                        r"^## (?!\[)(.+)$", content, re.MULTILINE
                    ):
                        tracker.add(match.group(1).strip())
        except Exception as exc:
            self.logger.debug(f"既存Hacker Newsタイトルの読み込みに失敗しました: {exc}")
        return tracker

    @handle_errors(retries=3)
    async def _get_top_stories(
        self, limit: int, dedup_tracker: DedupTracker
    ) -> list[Story]:
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
        # 1. topstoriesから多めに記事IDを取得（100件）
        response = await self.http_client.get(f"{self.base_url}/topstories.json")
        story_ids = response.json()
        if FETCH_LIMIT is not None:
            story_ids = story_ids[:FETCH_LIMIT]

        # 2. 並行してストーリーを取得（既存の処理）
        tasks = []
        for story_id in story_ids:
            tasks.append(self._fetch_story(story_id))

        story_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 有効なストーリーを収集
        all_stories = []
        for result in story_results:
            if isinstance(result, Story):
                all_stories.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching story: {result}")

        # 4. フィルタリング処理を追加
        filtered_stories = []
        for story in all_stories:
            # スコアフィルタリング
            if story.score < SCORE_THRESHOLD:
                continue

            # テキスト長フィルタリング
            text_content = story.text or ""
            text_length = len(text_content)

            if text_length < MIN_TEXT_LENGTH or text_length > MAX_TEXT_LENGTH:
                continue

            filtered_stories.append(story)

        # 5. スコアで降順ソート
        filtered_stories.sort(key=lambda story: story.score, reverse=True)

        unique_stories: list[Story] = []
        for story in filtered_stories:
            is_dup, normalized = dedup_tracker.is_duplicate(story.title)
            if is_dup:
                original = (
                    dedup_tracker.get_original_title(normalized) or story.title
                )
                self.logger.info(
                    "重複記事をスキップ: '%s' (初出: '%s')",
                    story.title,
                    original,
                )
                continue

            dedup_tracker.add(story.title)
            unique_stories.append(story)

        # 6. フィルタリング後の上位記事を選択（limitで指定された数）
        selected_stories = unique_stories[:limit]

        # 7. ログに統計情報を出力
        self.logger.info(
            f"Hacker News記事フィルタリング結果: "
            f"取得: {len(all_stories)}件, "
            f"フィルタリング後: {len(filtered_stories)}件, "
            f"選択: {len(selected_stories)}件"
        )

        # 8. 要約を並行して生成
        await self._summarize_stories(selected_stories)

        # 9. コンテンツフェッチの要約を出力
        await self._log_fetch_summary(selected_stories)

        return selected_stories

    def _load_blocked_domains(self) -> dict[str, Any]:
        """ブロックドメインリストを読み込みます。"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            blocked_domains_path = os.path.join(current_dir, "blocked_domains.json")

            with open(blocked_domains_path, encoding="utf-8") as f:
                blocked_data = json.load(f)

            self.logger.info(
                f"ブロックドメインリストを読み込みました: {len(blocked_data.get('blocked_domains', []))}件"
            )
            return blocked_data
        except Exception as e:
            self.logger.warning(f"ブロックドメインリストの読み込みに失敗しました: {e}")
            return {"blocked_domains": [], "reasons": {}}

    def _is_blocked_domain(self, url: str) -> bool:
        """指定されたURLがブロックされたドメインかどうかをチェックします。"""
        if not url:
            return False

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # www.を除去して比較
            if domain.startswith("www."):
                domain = domain[4:]

            blocked_domains = self.blocked_domains.get("blocked_domains", [])
            return domain in [d.lower() for d in blocked_domains]
        except Exception:
            return False

    async def _log_fetch_summary(self, stories: list[Story]) -> None:
        """コンテンツフェッチの要約ログを出力します。"""
        success_count = 0
        blocked_count = 0
        error_count = 0

        for story in stories:
            if not story.text:
                error_count += 1
            elif "ブロックされています" in story.text:
                blocked_count += 1
            elif (
                "アクセス制限により" in story.text
                or "記事が見つかりませんでした" in story.text
                or "記事の内容を取得できませんでした" in story.text
            ):
                error_count += 1
            else:
                success_count += 1

        self.logger.info(
            f"Content fetch summary: {success_count} succeeded, {blocked_count} blocked, {error_count} failed"
        )

    def _is_http1_required_domain(self, url: str) -> bool:
        """指定されたURLがHTTP/1.1を必要とするドメインかどうかをチェックします。"""
        if not url:
            return False

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # www.を除去して比較
            if domain.startswith("www."):
                domain = domain[4:]

            http1_required_domains = self.blocked_domains.get(
                "http1_required_domains", []
            )
            return domain in [d.lower() for d in http1_required_domains]
        except Exception:
            return False

    async def _fetch_story(self, story_id: int) -> Story | None:
        """個別のストーリーを取得"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/item/{story_id}.json"
            )
            item = response.json()

            if "title" not in item:
                return None

            story = Story(
                title=item.get("title", ""),
                score=item.get("score", 0),
                url=item.get("url"),
                text=item.get("text"),
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
        # ブロックされたドメインをチェック
        if self._is_blocked_domain(story.url):
            domain = urlparse(story.url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            reason = self.blocked_domains.get("reasons", {}).get(domain, "アクセス制限")
            story.text = f"このサイト（{domain}）は{reason}のためブロックされています。"
            self.logger.debug(f"ブロックされたドメインをスキップ: {story.url} - {reason}")
            return

        # HTTP/1.1が必要なドメインをチェック
        force_http1 = self._is_http1_required_domain(story.url)
        if force_http1:
            self.logger.info(f"Using HTTP/1.1 for {story.url} (required domain)")

        try:
            # ユーザーエージェントを設定してアクセス制限を回避
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await self.http_client.get(
                story.url, headers=headers, force_http1=force_http1
            )

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
                        meaningful_paragraphs = [
                            p.get_text().strip()
                            for p in paragraphs[:5]
                            if len(p.get_text().strip()) > 50
                        ]
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
            # HTTPエラーに応じてログレベルを調整
            error_str = str(e)

            if "401" in error_str or "403" in error_str or "Forbidden" in error_str:
                # 401/403エラーは想定内のため、debugレベル
                status_code = (
                    "401/403"
                    if ("401" in error_str or "403" in error_str)
                    else "Forbidden"
                )
                self.logger.debug(
                    f"Expected access restriction for {story.url}: {status_code}"
                )
                story.text = "アクセス制限により記事の内容を取得できませんでした。"
            elif "404" in error_str or "Not Found" in error_str:
                # 404エラーはinfoレベル
                self.logger.info(f"Content not found for {story.url}: 404")
                story.text = "記事が見つかりませんでした。"
            else:
                # その他の予期しないエラーはerrorレベル
                self.logger.error(f"Unexpected error fetching {story.url}: {str(e)}")
                story.text = "記事の内容を取得できませんでした。"

    async def _summarize_stories(self, stories: list[Story]) -> None:
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
                max_tokens=1000,
            )
            story.summary = summary
            await self.rate_limit()  # API呼び出し後のレート制限
        except Exception as e:
            story.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(self, stories: list[Story]) -> None:
        """
        記事情報を保存します。
        
        Parameters
        ----------
        stories : List[Story]
            保存する記事のリスト。
        """
        today = datetime.now()

        filename_json = f"{today.strftime('%Y-%m-%d')}.json"
        filename_md = f"{today.strftime('%Y-%m-%d')}.md"

        new_records = [
            {
                "title": story.title,
                "score": story.score,
                "url": story.url,
                "text": story.text,
                "summary": story.summary,
            }
            for story in stories
        ]

        existing_records = await self._load_existing_story_data(
            filename_json, filename_md
        )

        merged_records = merge_records(
            existing_records,
            new_records,
            key=lambda item: item.get("title", ""),
            sort_key=lambda item: (
                item.get("score", 0),
                item.get("summary") or "",
            ),
            limit=MAX_STORY_LIMIT,
        )

        await self.save_json(merged_records, filename_json)

        merged_stories = [
            Story(
                title=record.get("title", ""),
                score=record.get("score", 0),
                url=record.get("url"),
                text=record.get("text"),
                summary=record.get("summary", ""),
            )
            for record in merged_records
        ]

        content = self._render_markdown(merged_stories, today)
        await self.save_markdown(content, filename_md)

    def _render_markdown(self, stories: list[Story], today: datetime) -> str:
        content = f"# Hacker News トップ記事 ({today.strftime('%Y-%m-%d')})\n\n"

        for story in stories:
            title_link = (
                f"[{story.title}]({story.url})" if story.url else story.title
            )
            content += f"## {title_link}\n\n"
            content += f"スコア: {story.score}\n\n"

            if story.summary:
                content += f"**要約**:\n{story.summary}\n\n"
            elif story.text:
                trimmed = story.text[:500]
                ellipsis = "..." if len(story.text) > 500 else ""
                content += f"{trimmed}{ellipsis}\n\n"

            content += "---\n\n"

        return content

    async def _load_existing_story_data(
        self, filename_json: str, filename_md: str
    ) -> list[dict[str, Any]]:
        existing_json = await self.load_json(filename_json)
        if existing_json:
            return existing_json

        markdown_content = await self.storage.load(filename_md)
        if not markdown_content:
            return []

        return self._parse_markdown(markdown_content)

    def _parse_markdown(self, content: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        pattern = re.compile(
            r"##\s+(?:\[(?P<title>.+?)\]\((?P<url>[^\)]+)\)|(?P<title_only>.+?))\n\n"
            r"スコア:\s*(?P<score>\d+)\n\n"
            r"(?:(\*\*要約\*\*:\n(?P<summary>.*?))|(?P<text>.+?))?---",
            re.DOTALL,
        )

        for match in pattern.finditer(content + "---"):
            title = match.group("title") or match.group("title_only") or ""
            url = match.group("url")
            score = int(match.group("score") or 0)
            summary = (match.group("summary") or "").strip()
            text = (match.group("text") or "").strip()

            records.append(
                {
                    "title": title.strip(),
                    "url": url.strip() if url else None,
                    "score": score,
                    "summary": summary,
                    "text": text,
                }
            )

        return records
