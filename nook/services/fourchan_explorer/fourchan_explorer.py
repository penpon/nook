"""4chanからのAI関連スレッド収集サービス。"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomli

from nook.common.base_service import BaseService
from nook.common.dedup import DedupTracker
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.gpt_client import GPTClient
from nook.common.storage import LocalStorage


@dataclass
class Thread:
    """
    4chanスレッド情報。

    Parameters
    ----------
    thread_id : int
        スレッドID。
    title : str
        スレッドタイトル。
    url : str
        スレッドURL。
    board : str
        ボード名。
    posts : List[Dict[str, Any]]
        投稿リスト。
    timestamp : int
        作成タイムスタンプ。
    """

    thread_id: int
    title: str
    url: str
    board: str
    posts: list[dict[str, Any]]
    timestamp: int
    summary: str = field(default="")
    popularity_score: float = field(default=0.0)


class FourChanExplorer(BaseService):
    """
    4chanからAI関連スレッドを収集するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    TOTAL_LIMIT = 15

    def __init__(self, storage_dir: str = "data"):
        """
        FourChanExplorerを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("fourchan_explorer")
        self.http_client = None  # setup_http_clientで初期化
        self.gpt_client = GPTClient()

        storage_path = Path(storage_dir)
        if storage_path.name != self.service_name:
            storage_path = storage_path / self.service_name
        self.storage = LocalStorage(str(storage_path))

        # 対象となるボードを設定ファイルから読み込む
        self.target_boards = self._load_boards()

        # AIに関連するキーワード
        self.ai_keywords = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "ml",
            "deep learning",
            "neural network",
            "gpt",
            "llm",
            "chatgpt",
            "claude",
            "gemini",
            "grok",
            "anthropic",
            "openai",
            "stable diffusion",
            "dalle",
            "midjourney",
        ]

        # APIリクエスト間の遅延（4chanのAPI利用規約を遵守するため）
        self.request_delay = 1  # 秒

    def _load_boards(self) -> list[str]:
        """
        対象となるボードの設定を読み込みます。

        Returns
        -------
        List[str]
            ボードIDのリスト
        """
        script_dir = Path(__file__).parent
        boards_file = script_dir / "boards.toml"

        # boards.tomlが存在しない場合はデフォルト値を使用
        if not boards_file.exists():
            self.logger.warning(
                f"警告: {boards_file} が見つかりません。デフォルトのボードを使用します。"
            )
            return ["g", "sci", "biz", "pol"]

        try:
            with open(boards_file, "rb") as f:
                config = tomli.load(f)
                boards_dict = config.get("boards", {})
                # ボードIDのリストを返す
                return list(boards_dict.keys())
        except Exception as e:
            self.logger.error(f"エラー: boards.tomlの読み込みに失敗しました: {e}")
            self.logger.info("デフォルトのボードを使用します。")
            return ["g", "sci", "biz", "pol"]

    def run(self, thread_limit: int | None = None) -> None:
        """
        4chanからAI関連スレッドを収集して保存します。

        Parameters
        ----------
        thread_limit : Optional[int], default=None
            各ボードから取得するスレッド数。Noneの場合は制限なし。
        """
        asyncio.run(self.collect(thread_limit))

    async def collect(self, thread_limit: int | None = None) -> None:
        """
        4chanからAI関連スレッドを収集して保存します（非同期版）。

        Parameters
        ----------
        thread_limit : Optional[int], default=None
            各ボードから取得するスレッド数。Noneの場合は制限なし。
        """
        total_limit = self.TOTAL_LIMIT

        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        candidate_threads: list[Thread] = []
        selected_threads: list[Thread] = []
        dedup_tracker = self._load_existing_titles()

        try:
            # 各ボードからスレッドを取得
            for board in self.target_boards:
                try:
                    self.logger.info(
                        f"ボード /{board}/ からのスレッド取得を開始します..."
                    )
                    threads = await self._retrieve_ai_threads(
                        board, thread_limit, dedup_tracker
                    )
                    self.logger.info(
                        f"ボード /{board}/ から {len(threads)} 件のスレッドを取得しました"
                    )
                    candidate_threads.extend(threads)

                    # APIリクエスト間の遅延
                    await asyncio.sleep(self.request_delay)

                except Exception as e:
                    self.logger.error(f"Error processing board /{board}/: {str(e)}")

            self.logger.info(
                f"合計 {len(candidate_threads)} 件のスレッド候補を取得しました"
            )

            selected_threads = self._select_top_threads(candidate_threads, total_limit)
            self.logger.info(
                f"人気スコア上位 {len(selected_threads)} 件のスレッドを要約します"
            )

            for thread in selected_threads:
                await self._summarize_thread(thread)

            # 要約を保存
            if selected_threads:
                await self._store_summaries(selected_threads)
                self.logger.info("スレッドの要約を保存しました")
            else:
                self.logger.info("保存するスレッドがありません")

        finally:
            # グローバルクライアントなのでクローズ不要
            pass

    async def _retrieve_ai_threads(
        self, board: str, limit: int | None, dedup_tracker: DedupTracker
    ) -> list[Thread]:
        """
        特定のボードからAI関連スレッドを取得します。

        Parameters
        ----------
        board : str
            ボード名。
        limit : Optional[int]
            取得するスレッド数。Noneの場合は制限なし。

        Returns
        -------
        List[Thread]
            取得したスレッドのリスト。
        """
        # カタログの取得（すべてのスレッドのリスト）
        catalog_url = f"https://a.4cdn.org/{board}/catalog.json"
        response = await self.http_client.get(catalog_url)
        catalog_data = response.json()

        # AI関連のスレッドをフィルタリング
        ai_threads = []
        for page in catalog_data:
            for thread in page.get("threads", []):
                # スレッドのタイトル（subject）とコメント（com）を確認
                subject = thread.get("sub", "").lower()
                comment = thread.get("com", "").lower()

                # HTMLタグを除去
                if comment:
                    comment = re.sub(r"<[^>]*>", "", comment)

                # AIキーワードが含まれているかチェック
                is_ai_related = any(
                    keyword in subject or keyword in comment
                    for keyword in self.ai_keywords
                )

                if is_ai_related:
                    is_dup, normalized = dedup_tracker.is_duplicate(title)
                    if is_dup:
                        original = dedup_tracker.get_original_title(normalized) or title
                        self.logger.info(
                            "重複スレッドをスキップ: '%s' (初出: '%s')",
                            title,
                            original,
                        )
                        continue

                    thread_id = thread.get("no")
                    timestamp = thread.get("time", 0)
                    title = thread.get("sub", f"Untitled Thread {thread_id}")

                    # スレッドのURLを構築
                    thread_url = f"https://boards.4chan.org/{board}/thread/{thread_id}"

                    # スレッドの投稿を取得
                    thread_data = await self._retrieve_thread_posts(board, thread_id)

                    popularity_score = self._calculate_popularity(
                        thread_metadata=thread,
                        posts=thread_data,
                    )

                    dedup_tracker.add(title)

                    ai_threads.append(
                        Thread(
                            thread_id=thread_id,
                            title=title,
                            url=thread_url,
                            board=board,
                            posts=thread_data,
                            timestamp=timestamp,
                            popularity_score=popularity_score,
                        )
                    )

                    # 指定された数のスレッドを取得したら終了
                    if limit is not None and len(ai_threads) >= limit:
                        break

            if limit is not None and len(ai_threads) >= limit:
                break

        return ai_threads

    async def _retrieve_thread_posts(
        self, board: str, thread_id: int
    ) -> list[dict[str, Any]]:
        """
        スレッドの投稿を取得します。

        Parameters
        ----------
        board : str
            ボード名。
        thread_id : int
            スレッドID。

        Returns
        -------
        List[Dict[str, Any]]
            投稿のリスト。
        """
        thread_url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
        try:
            response = await self.http_client.get(thread_url)
            thread_data = response.json()
            posts = thread_data.get("posts", [])

            # APIリクエスト間の遅延
            await asyncio.sleep(self.request_delay)

            return posts
        except Exception as e:
            self.logger.error(f"スレッドの取得に失敗しました: {str(e)}")
            return []

    def _load_existing_titles(self) -> DedupTracker:
        tracker = DedupTracker()
        try:
            content = self.storage.load_markdown("", datetime.now())
            if content:
                for match in re.finditer(r"^### \[(.+?)\]", content, re.MULTILINE):
                    tracker.add(match.group(1))
        except Exception as exc:
            self.logger.debug(f"既存スレッドタイトルの読み込みに失敗しました: {exc}")
        return tracker

    def _calculate_popularity(
        self, thread_metadata: dict[str, Any], posts: list[dict[str, Any]]
    ) -> float:
        replies = thread_metadata.get("replies", 0) or 0
        images = thread_metadata.get("images", 0) or 0
        bumps = thread_metadata.get("bumps", 0) or 0

        recency_bonus = 0.0
        try:
            last_modified = thread_metadata.get("last_modified") or thread_metadata.get(
                "time", 0
            )
            if last_modified:
                now = datetime.now()
                modified = datetime.fromtimestamp(last_modified)
                hours = (now - modified).total_seconds() / 3600
                recency_bonus = 24 / max(1.0, hours)
        except Exception:
            pass

        return float(replies + images * 2 + bumps + len(posts) + recency_bonus)

    def _select_top_threads(self, threads: list[Thread], limit: int) -> list[Thread]:
        if not threads:
            return []

        if len(threads) <= limit:
            return threads

        def sort_key(thread: Thread):
            created = datetime.fromtimestamp(thread.timestamp)
            return (thread.popularity_score, created)

        sorted_threads = sorted(threads, key=sort_key, reverse=True)
        return sorted_threads[:limit]

    async def _summarize_thread(self, thread: Thread) -> None:
        """
        スレッドを要約します。

        Parameters
        ----------
        thread : Thread
            要約するスレッド。
        """
        # スレッドのコンテンツを抽出（最初の投稿と、最も反応のある投稿を含む）
        thread_content = ""

        # スレッドのタイトルを追加
        thread_content += f"タイトル: {thread.title}\n\n"

        # オリジナルポスト（OP）を追加
        if thread.posts and len(thread.posts) > 0:
            op = thread.posts[0]
            op_text = op.get("com", "")
            if op_text:
                # HTMLタグを除去
                op_text = re.sub(r"<[^>]*>", " ", op_text)
                thread_content += f"OP: {op_text}\n\n"

        # 返信を追加（最大5件）
        replies = thread.posts[1:6] if len(thread.posts) > 1 else []
        for i, reply in enumerate(replies):
            reply_text = reply.get("com", "")
            if reply_text:
                # HTMLタグを除去
                reply_text = re.sub(r"<[^>]*>", " ", reply_text)
                thread_content += f"返信 {i+1}: {reply_text}\n\n"

        prompt = f"""
        以下の4chanスレッドを要約してください。

        ボード: /{thread.board}/
        {thread_content}
        
        要約は以下の形式で行い、日本語で回答してください:
        1. スレッドの主な内容（1-2文）
        2. 議論の主要ポイント（箇条書き3-5点）
        3. スレッドの全体的な論調
        
        注意：攻撃的な内容やヘイトスピーチは緩和し、主要な技術的議論に焦点を当ててください。
        """

        system_instruction = """
        あなたは4chanスレッドの要約を行うアシスタントです。
        投稿された内容を客観的に分析し、技術的議論や情報に焦点を当てた要約を提供してください。
        過度な攻撃性、ヘイトスピーチ、差別的内容は中和して表現し、有益な情報のみを抽出してください。
        回答は日本語で行い、AIやテクノロジーに関連する情報を優先的に含めてください。
        """

        try:
            summary = self.gpt_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=1000,
            )
            thread.summary = summary
        except Exception as e:
            self.logger.error(f"要約の生成中にエラーが発生しました: {str(e)}")
            thread.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(self, threads: list[Thread]) -> None:
        if not threads:
            self.logger.info("保存するスレッドがありません")
            return

        default_date = datetime.now().date()
        records = self._serialize_threads(threads)
        records_by_date = group_records_by_date(records, default_date=default_date)

        await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_threads,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("thread_id"),
            sort_key=self._thread_sort_key,
            limit=self.TOTAL_LIMIT,
            logger=self.logger,
        )

    def _serialize_threads(self, threads: list[Thread]) -> list[dict]:
        records: list[dict] = []
        for thread in threads:
            published = datetime.fromtimestamp(thread.timestamp, tz=timezone.utc)
            records.append(
                {
                    "thread_id": thread.thread_id,
                    "title": thread.title,
                    "url": thread.url,
                    "timestamp": thread.timestamp,
                    "summary": thread.summary,
                    "popularity_score": thread.popularity_score,
                    "board": thread.board,
                    "published_at": published.isoformat(),
                }
            )
        return records

    async def _load_existing_threads(self, target_date: datetime) -> list[dict]:
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        existing_json = await self.load_json(filename_json)
        if existing_json:
            if isinstance(existing_json, dict):
                flattened: list[dict] = []
                for board, items in existing_json.items():
                    for item in items:
                        flattened.append({"board": board, **item})
                return flattened
            return existing_json

        markdown = await self.storage.load(f"{date_str}.md")
        if not markdown:
            return []

        return self._parse_markdown(markdown)

    def _thread_sort_key(self, item: dict) -> tuple[float, datetime]:
        popularity = float(item.get("popularity_score", 0.0) or 0.0)
        published_raw = item.get("published_at")
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw)
            except ValueError:
                published = datetime.min.replace(tzinfo=timezone.utc)
        else:
            timestamp = item.get("timestamp")
            if timestamp:
                try:
                    published = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                except Exception:
                    published = datetime.min.replace(tzinfo=timezone.utc)
            else:
                published = datetime.min.replace(tzinfo=timezone.utc)
        return (popularity, published)

    def _extract_thread_id_from_url(self, url: str) -> int:
        if not url:
            return 0

        cleaned = url.strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")

        match = re.search(r"/thread/(\d+)", cleaned)
        if match:
            return int(match.group(1))

        for part in reversed(cleaned.split("/")):
            if part.isdigit():
                return int(part)

        return 0

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        content = f"# 4chan AI関連スレッド ({today.strftime('%Y-%m-%d')})\n\n"
        grouped: dict[str, list[dict]] = {}
        for record in records:
            board = record.get("board", "unknown")
            grouped.setdefault(board, []).append(record)

        for board, threads in grouped.items():
            content += f"## /{board}/\n\n"
            for thread in threads:
                title = (
                    thread.get("title") or f"無題スレッド #{thread.get('thread_id')}"
                )
                content += f"### [{title}]({thread.get('url')})\n\n"
                published_raw = thread.get("published_at")
                if published_raw:
                    try:
                        published_dt = datetime.fromisoformat(published_raw)
                        timestamp = int(published_dt.timestamp())
                    except ValueError:
                        timestamp = int(thread.get("timestamp", 0) or 0)
                else:
                    timestamp = int(thread.get("timestamp", 0) or 0)
                content += f"作成日時: <t:{timestamp}:F>\n\n"
                content += f"**要約**:\n{thread.get('summary', '')}\n\n"
                content += "---\n\n"
        return content

    def _parse_markdown(self, markdown: str) -> list[dict]:
        records: list[dict] = []
        board_pattern = re.compile(r"^##\s+/([^/]+)/$", re.MULTILINE)
        thread_pattern = re.compile(
            r"### \[(?P<title>.+?)\]\((?P<url>[^\)]+)\)\n\n"
            r"作成日時: <t:(?P<timestamp>\d+):F>\n\n"
            r"\*\*要約\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        sections = list(board_pattern.finditer(markdown))
        for idx, match in enumerate(sections):
            start = match.end()
            end = (
                sections[idx + 1].start() if idx + 1 < len(sections) else len(markdown)
            )
            block = markdown[start:end]
            board = match.group(1).strip()

            for thread_match in thread_pattern.finditer(block + "---"):
                title = thread_match.group("title")
                url = thread_match.group("url")
                summary = thread_match.group("summary").strip()
                timestamp = int(thread_match.group("timestamp") or 0)
                thread_id = self._extract_thread_id_from_url(url)
                record = {
                    "thread_id": thread_id,
                    "title": title.strip(),
                    "url": url.strip(),
                    "timestamp": timestamp,
                    "summary": summary,
                    "popularity_score": 0.0,
                    "board": board,
                }

                if timestamp:
                    record["published_at"] = datetime.fromtimestamp(
                        timestamp, tz=timezone.utc
                    ).isoformat()

                records.append(record)

        return records
