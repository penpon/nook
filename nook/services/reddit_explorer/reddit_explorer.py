"""Redditの人気投稿を収集・要約するサービス。"""

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import asyncpraw
import tomli

from nook.common.base_service import BaseService
from nook.common.dedup import DedupTracker
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots


@dataclass
class RedditPost:
    """
    Reddit投稿情報。

    Parameters
    ----------
    type : Literal["image", "gallery", "video", "poll", "crosspost", "text", "link"]
        投稿タイプ。
    id : str
        投稿ID。
    title : str
        タイトル。
    url : str | None
        URL。
    upvotes : int
        アップボート数。
    text : str
        本文。
    permalink : str
        投稿へのパーマリンク。
    thumbnail : str
        サムネイルURL。
    """

    type: Literal["image", "gallery", "video", "poll", "crosspost", "text", "link"]
    id: str
    title: str
    url: str | None
    upvotes: int
    text: str
    permalink: str = ""
    comments: list[dict[str, str | int]] = field(default_factory=list)
    summary: str = field(init=False)
    thumbnail: str = "self"
    popularity_score: float = field(default=0.0)
    created_at: datetime | None = None


class RedditExplorer(BaseService):
    """
    Redditの人気投稿を収集・要約するクラス。

    Parameters
    ----------
    client_id : str, optional
        Reddit APIのクライアントID。指定しない場合は環境変数から取得。
    client_secret : str, optional
        Reddit APIのクライアントシークレット。指定しない場合は環境変数から取得。
    user_agent : str, optional
        Reddit APIのユーザーエージェント。指定しない場合は環境変数から取得。
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        storage_dir: str = "data",
    ):
        """
        RedditExplorerを初期化します。

        Parameters
        ----------
        client_id : str, optional
            Reddit APIのクライアントID。指定しない場合は環境変数から取得。
        client_secret : str, optional
            Reddit APIのクライアントシークレット。指定しない場合は環境変数から取得。
        user_agent : str, optional
            Reddit APIのユーザーエージェント。指定しない場合は環境変数から取得。
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("reddit_explorer")

        self.client_id = client_id or os.environ.get("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.environ.get("REDDIT_USER_AGENT")

        if not all([self.client_id, self.client_secret, self.user_agent]):
            raise ValueError(
                "Reddit API credentials must be provided or set as environment variables"
            )

        # asyncprawインスタンスは使用時に作成
        self.reddit = None

        self.SUMMARY_LIMIT = 15

        self.http_client = None  # setup_http_clientで初期化

        # サブレディットの設定を読み込む
        script_dir = Path(__file__).parent
        with open(script_dir / "subreddits.toml", "rb") as f:
            self.subreddits_config = tomli.load(f)

    def run(self, limit: int | None = None) -> None:
        """
        Redditの人気投稿を収集・要約して保存します。

        Parameters
        ----------
        limit : Optional[int], default=None
            各サブレディットから取得する投稿数。Noneの場合は制限なし。
        """
        asyncio.run(self.collect(limit))

    async def collect(self, limit: int | None = None) -> None:
        """
        Redditの人気投稿を収集・要約して保存します（非同期版）。

        Parameters
        ----------
        limit : Optional[int], default=None
            各サブレディットから取得する投稿数。Noneの場合は制限なし。
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_posts: list[tuple[str, str, RedditPost]] = []
        dedup_tracker = await self._load_existing_titles()

        # Redditクライアントをコンテキストマネージャーで使用
        async with asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        ) as reddit:
            self.reddit = reddit

            try:
                # 各カテゴリのサブレディットから投稿を取得
                for category, subreddits in self.subreddits_config.items():
                    self.logger.info(f"カテゴリ {category} の処理を開始します...")
                    for subreddit_name in subreddits:
                        try:
                            self.logger.info(
                                f"サブレディット r/{subreddit_name} から投稿を取得しています..."
                            )
                            posts = await self._retrieve_hot_posts(
                                subreddit_name, limit, dedup_tracker
                            )

                            for post in posts:
                                candidate_posts.append((category, subreddit_name, post))

                        except Exception as e:
                            self.logger.error(
                                f"サブレディット r/{subreddit_name} の処理中にエラーが発生しました: {str(e)}"
                            )

                self.logger.info(
                    f"合計 {len(candidate_posts)} 件の投稿候補を取得しました"
                )

                selected_posts = self._select_top_posts(candidate_posts)
                self.logger.info(
                    f"人気スコア上位 {len(selected_posts)} 件の投稿を要約します"
                )

                for category, subreddit_name, post in selected_posts:
                    post.comments = await self._retrieve_top_comments_of_post(
                        post, limit=5
                    )
                    await self._summarize_reddit_post(post)

                if selected_posts:
                    await self._store_summaries(selected_posts)
                    self.logger.info("投稿の要約を保存しました")
                else:
                    self.logger.info("保存する投稿がありません")

            finally:
                # グローバルHTTPクライアントなのでクローズ不要
                pass
                # asyncprawのコンテキストマネージャーが自動的にクローズする

    async def _retrieve_hot_posts(
        self, subreddit_name: str, limit: int | None, dedup_tracker: DedupTracker
    ) -> list[RedditPost]:
        """
        サブレディットの人気投稿を取得します。

        Parameters
        ----------
        subreddit_name : str
            サブレディット名。
        limit : Optional[int]
            取得する投稿数。Noneの場合は制限なし。
        dedup_tracker : DedupTracker
            タイトル重複を追跡するトラッカー。

        Returns
        -------
        List[RedditPost]
            取得した投稿のリスト。
        """
        subreddit = await self.reddit.subreddit(subreddit_name)
        posts = []

        async for submission in subreddit.hot(limit=limit):
            if submission.stickied:
                continue

            # 投稿タイプを判定
            post_type = "text"
            if hasattr(submission, "is_video") and submission.is_video:
                post_type = "video"
            elif hasattr(submission, "is_gallery") and submission.is_gallery:
                post_type = "gallery"
            elif hasattr(submission, "poll_data") and submission.poll_data:
                post_type = "poll"
            elif (
                hasattr(submission, "crosspost_parent") and submission.crosspost_parent
            ):
                post_type = "crosspost"
            elif submission.is_self:
                post_type = "text"
            elif any(
                submission.url.endswith(ext)
                for ext in [".jpg", ".jpeg", ".png", ".gif"]
            ):
                post_type = "image"
            else:
                post_type = "link"

            # タイトルと本文を日本語に翻訳
            title = submission.title

            is_dup, normalized = dedup_tracker.is_duplicate(title)
            if is_dup:
                original = dedup_tracker.get_original_title(normalized) or title
                self.logger.info(
                    "重複Reddit投稿をスキップ: '%s' (初出: '%s')",
                    title,
                    original,
                )
                continue
            text_ja = (
                await self._translate_to_japanese(submission.selftext)
                if submission.selftext
                else ""
            )

            created_at = (
                datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if hasattr(submission, "created_utc")
                else None
            )

            post = RedditPost(
                type=post_type,
                id=submission.id,
                title=title,
                url=submission.url if not submission.is_self else None,
                upvotes=submission.score,
                text=text_ja,
                permalink=f"https://www.reddit.com{submission.permalink}",
                thumbnail=(
                    submission.thumbnail if hasattr(submission, "thumbnail") else "self"
                ),
                popularity_score=float(submission.score),
                created_at=created_at,
            )

            posts.append(post)
            dedup_tracker.add(post.title)

        return posts

    async def _translate_to_japanese(self, text: str) -> str:
        """
        テキストを日本語に翻訳します。

        Parameters
        ----------
        text : str
            翻訳するテキスト。

        Returns
        -------
        str
            翻訳されたテキスト。
        """
        if not text:
            return ""

        try:
            prompt = f"以下の英語のテキストを自然な日本語に翻訳してください。専門用語や固有名詞は適切に翻訳し、必要に応じて英語の原語を括弧内に残してください。\n\n{text}"

            translated_text = self.gpt_client.generate_content(
                prompt=prompt, temperature=0.3, max_tokens=1000
            )

            return translated_text
        except Exception as e:
            self.logger.error(f"Error translating text: {str(e)}")
            return text  # 翻訳に失敗した場合は原文を返す

    async def _retrieve_top_comments_of_post(
        self, post: RedditPost, limit: int = 5
    ) -> list[dict[str, str | int]]:
        """
        投稿のトップコメントを取得します。

        Parameters
        ----------
        post : RedditPost
            投稿情報。
        limit : int, default=5
            取得するコメント数。

        Returns
        -------
        List[Dict[str, str | int]]
            取得したコメントのリスト。
        """
        submission = await self.reddit.submission(id=post.id)
        submission.comment_sort = "top"
        submission.comment_limit = limit

        comments = []
        for comment in submission.comments[:limit]:
            if hasattr(comment, "body"):
                # コメントを日本語に翻訳
                comment_text_ja = await self._translate_to_japanese(comment.body)

                comments.append(
                    {
                        "text": comment_text_ja,
                        "score": comment.score if hasattr(comment, "score") else 0,
                    }
                )

        return comments

    async def _summarize_reddit_post(self, post: RedditPost) -> None:
        """
        Reddit投稿を要約します。

        Parameters
        ----------
        post : RedditPost
            要約する投稿。
        """
        prompt = f"""
        以下のReddit投稿を要約してください。

        タイトル: {post.title}
        本文: {post.text if post.text else '(本文なし)'}
        URL: {post.url if post.url else '(URLなし)'}
        
        トップコメント:
        {chr(10).join([f"- {comment['text']}" for comment in post.comments])}
        
        要約は以下の形式で行い、日本語で回答してください:
        1. 投稿の主な内容（1-2文）
        2. 重要なポイント（箇条書き3-5点）
        3. 議論の傾向（コメントから）
        """

        system_instruction = """
        あなたはReddit投稿の要約を行うアシスタントです。
        与えられた投稿とコメントを分析し、簡潔で情報量の多い要約を作成してください。
        技術的な内容は正確に、一般的な内容は分かりやすく要約してください。
        回答は必ず日本語で行ってください。専門用語は適切に翻訳し、必要に応じて英語の専門用語を括弧内に残してください。
        """

        try:
            summary = self.gpt_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=1000,
            )
            post.summary = summary
        except Exception as e:
            self.logger.error(f"要約の生成中にエラーが発生しました: {str(e)}")
            post.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(self, posts: list[tuple[str, str, RedditPost]]) -> None:
        if not posts:
            self.logger.info("保存する投稿がありません")
            return

        default_date = datetime.now().date()
        records = self._serialize_posts(posts)
        records_by_date = group_records_by_date(records, default_date=default_date)

        await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_posts,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("id", ""),
            sort_key=self._post_sort_key,
            limit=self.SUMMARY_LIMIT,
        )

    def _serialize_posts(self, posts: list[tuple[str, str, RedditPost]]) -> list[dict]:
        records: list[dict] = []
        for category, subreddit, post in posts:
            created_at = post.created_at or datetime.now(timezone.utc)
            records.append(
                {
                    "id": post.id,
                    "category": category,
                    "subreddit": subreddit,
                    "title": post.title,
                    "url": post.url,
                    "permalink": post.permalink,
                    "text": post.text,
                    "upvotes": post.upvotes,
                    "summary": getattr(post, "summary", ""),
                    "type": post.type,
                    "thumbnail": post.thumbnail,
                    "comments": post.comments,
                    "popularity_score": post.popularity_score,
                    "created_at": created_at.isoformat(),
                    "published_at": created_at.isoformat(),
                }
            )
        return records

    async def _load_existing_posts(self, target_date: datetime) -> list[dict]:
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        existing_json = await self.load_json(filename_json)
        if existing_json:
            if isinstance(existing_json, dict):
                flattened: list[dict] = []
                for subreddit, items in existing_json.items():
                    for item in items:
                        flattened.append({"subreddit": subreddit, **item})
                return flattened
            return existing_json

        markdown = await self.storage.load(f"{date_str}.md")
        if not markdown:
            return []

        return self._parse_markdown(markdown)

    def _post_sort_key(self, item: dict) -> tuple[float, datetime]:
        popularity = float(item.get("popularity_score", 0.0) or 0.0)
        created_raw = item.get("created_at") or item.get("published_at")
        if created_raw:
            try:
                created = datetime.fromisoformat(created_raw)
            except ValueError:
                created = datetime.min.replace(tzinfo=timezone.utc)
        else:
            created = datetime.min.replace(tzinfo=timezone.utc)
        return (popularity, created)

    def _extract_post_id_from_permalink(self, permalink: str) -> str:
        if not permalink:
            return ""

        trimmed = permalink.strip()
        trimmed = trimmed.split("?", 1)[0]
        trimmed = trimmed.rstrip("/")

        parts = trimmed.split("/")
        try:
            comments_index = parts.index("comments")
        except ValueError:
            comments_index = -1

        if comments_index != -1 and comments_index + 1 < len(parts):
            post_id = parts[comments_index + 1]
            return post_id.strip()

        for part in reversed(parts):
            if part:
                return part.strip()

        return ""

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        content = f"# Reddit 人気投稿 ({today.strftime('%Y-%m-%d')})\n\n"
        grouped: dict[str, list[dict]] = {}
        for record in records:
            subreddit = record.get("subreddit", "unknown")
            grouped.setdefault(subreddit, []).append(record)

        for subreddit, posts in grouped.items():
            content += f"## r/{subreddit}\n\n"
            for post in posts:
                content += f"### [{post['title']}]({post.get('permalink')})\n\n"
                url = post.get("url")
                if url and url != post.get("permalink"):
                    content += f"リンク: {url}\n\n"
                text = post.get("text")
                if text:
                    trimmed = text[:200]
                    ellipsis = "..." if len(text) > 200 else ""
                    content += f"本文: {trimmed}{ellipsis}\n\n"
                content += f"アップボート数: {post.get('upvotes', 0)}\n\n"
                content += f"**要約**:\n{post.get('summary', '')}\n\n"
                content += "---\n\n"
        return content

    def _parse_markdown(self, markdown: str) -> list[dict]:
        records: list[dict] = []
        subreddit_pattern = re.compile(r"^##\s+r/(?P<subreddit>.+)$", re.MULTILINE)
        post_pattern = re.compile(
            r"### \[(?P<title>.+?)\]\((?P<permalink>[^\)]+)\)\n\n"
            r"(?:リンク: (?P<link>.+?)\n\n)?"
            r"(?:本文: (?P<text>.+?)\n\n)?"
            r"アップボート数: (?P<upvotes>\d+)\n\n"
            r"\*\*要約\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        sections = list(subreddit_pattern.finditer(markdown))
        for idx, match in enumerate(sections):
            start = match.end()
            end = (
                sections[idx + 1].start() if idx + 1 < len(sections) else len(markdown)
            )
            block = markdown[start:end]
            subreddit = match.group("subreddit").strip()

            for post_match in post_pattern.finditer(block + "---"):
                permalink = post_match.group("permalink")
                record = {
                    "id": self._extract_post_id_from_permalink(permalink),
                    "category": "unknown",
                    "title": post_match.group("title").strip(),
                    "url": (post_match.group("link") or "").strip() or None,
                    "permalink": permalink.strip() if permalink else "",
                    "text": (post_match.group("text") or "").strip(),
                    "upvotes": int(post_match.group("upvotes") or 0),
                    "summary": post_match.group("summary").strip(),
                    "type": "text",
                    "thumbnail": "self",
                    "comments": [],
                    "popularity_score": 0.0,
                    "subreddit": subreddit,
                }
                records.append(record)

        return records

    def _select_top_posts(
        self, posts: list[tuple[str, str, RedditPost]]
    ) -> list[tuple[str, str, RedditPost]]:
        """人気順に投稿を並べ替え、上位のみ返します。"""
        if not posts:
            return []

        if len(posts) <= self.SUMMARY_LIMIT:
            return posts

        def sort_key(item: tuple[str, str, RedditPost]):
            _, _, post = item
            created = post.created_at or datetime.min
            return (post.popularity_score, created)

        sorted_posts = sorted(posts, key=sort_key, reverse=True)
        return sorted_posts[: self.SUMMARY_LIMIT]

    async def _load_existing_titles(self) -> DedupTracker:
        tracker = DedupTracker()
        try:
            content = self.storage.load_markdown("", datetime.now())
            if content:
                for match in re.finditer(r"^### \[(.+?)\]", content, re.MULTILINE):
                    tracker.add(match.group(1))
        except Exception as exc:
            self.logger.debug(f"既存Reddit投稿タイトルの読み込みに失敗しました: {exc}")
        return tracker
