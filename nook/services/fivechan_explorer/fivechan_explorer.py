import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import cloudscraper
import httpx

from nook.common.base_service import BaseService
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.date_utils import (
    is_within_target_dates,
    target_dates_set,
)
from nook.common.dedup import DedupTracker
from nook.common.logging_utils import (
    log_article_counts,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)

# 定数: スレッドあたりの最大投稿取得数
# メモリ効率とパフォーマンスのバランスを保つため、大規模スレッドでも制限を設ける
MAX_POSTS_PER_THREAD = 10


@dataclass
class Thread:
    """5chanスレッド情報。

    Parameters
    ----------
    thread_id : int
        スレッドID。
    title : str
        スレッドタイトル。
    url : str
        スレッドURL。
    board : str
        板名。
    timestamp : int
        スレッド作成時刻（UNIXタイムスタンプ）。
    posts : list[Post]
        投稿リスト。
    summary : str
        スレッド要約。
    popularity_score : float
        人気度スコア（投稿数ベース）。

    """

    thread_id: int
    title: str
    url: str
    board: str
    timestamp: int
    posts: list["Post"] = field(default_factory=list)
    summary: str = ""
    popularity_score: float = 0.0


@dataclass
class Post:
    """5chan投稿情報。

    Parameters
    ----------
    no : int
        投稿番号。
    name : str
        投稿者名。
    mail : str
        メールアドレス。
    date : str
        投稿日時。
    content : str
        投稿内容。

    """

    no: int
    name: str
    mail: str
    date: str
    content: str


class FiveChanExplorer(BaseService):
    """5chan（旧2ちゃんねる）からAI関連スレッドを収集するサービス。

    Parameters
    ----------
    storage : LocalStorage, optional
        ストレージインスタンス。
    gpt_client : GPTClient, optional
        GPTクライアントインスタンス。

    """

    TOTAL_LIMIT = 15  # 1日あたりの最大スレッド数

    def __init__(self, storage_dir: str | None = None):
        super().__init__(service_name="fivechan_explorer")
        if storage_dir:
            from nook.common.storage import LocalStorage

            self.storage = LocalStorage(storage_dir)

        self.target_boards = self._load_boards_config()
        self.dedup_tracker = DedupTracker()
        self.http_client = None
        self.browser_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]

    def _load_boards_config(self) -> dict[str, str]:
        """boards.tomlから板設定を読み込みます。

        Returns
        -------
        dict[str, str]
            板ID→板名のマッピング。

        """
        config_path = Path(__file__).parent / "boards.toml"
        with open(config_path, "rb") as f:
            import tomllib

            config = tomllib.load(f)
            boards_config = config.get("boards", {})

            # 新しい形式対応: {board_id: {name: "名前", server: "サーバー"}}
            # 旧形式も対応: {board_id: "名前"}
            boards = {}
            self.board_servers = {}  # サーバー情報を保存

            for board_id, board_info in boards_config.items():
                if isinstance(board_info, dict):
                    # 新形式: {name: "名前", server: "サーバー"}
                    boards[board_id] = board_info.get("name", board_id)
                    self.board_servers[board_id] = board_info.get("server", "mevius.5ch.net")
                else:
                    # 旧形式: "名前"
                    boards[board_id] = board_info
                    self.board_servers[board_id] = "mevius.5ch.net"  # デフォルト

            return boards

    def _get_random_user_agent(self) -> str:
        """ランダムなUser-Agentを取得します。

        Returns
        -------
        str
            ランダムに選択されたUser-Agent文字列。

        """
        import random

        return random.choice(self.user_agents)

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """指数バックオフによる遅延時間を計算します。

        Parameters
        ----------
        retry_count : int
            リトライ回数。

        Returns
        -------
        float
            遅延時間（秒）。

        """
        # 基本遅延時間: 2^retry_count秒、最大300秒
        base_delay = min(2**retry_count, 300)
        return base_delay

    async def _get_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> Any:
        """リトライ機能付きHTTP GETリクエスト。

        Parameters
        ----------
        url : str
            リクエストURL。
        max_retries : int, default=3
            最大リトライ回数。

        Returns
        -------
        any
            HTTPレスポンス。

        """
        for attempt in range(max_retries + 1):
            try:
                # 動的なUser-Agentでヘッダーを更新
                headers = self.browser_headers.copy()
                headers["User-Agent"] = self._get_random_user_agent()

                if not self.http_client:
                    return None
                response = await self.http_client.get(url, headers=headers, **kwargs)

                # 成功レスポンス（200番台）の場合は返す
                if 200 <= response.status_code < 300:
                    return response

                # レート制限エラー（429）の場合
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(float(retry_after))
                    else:
                        wait_time = int(self._calculate_backoff_delay(attempt))

                    self.logger.warning(f"レート制限検知 (429): {wait_time}秒待機します")
                    await asyncio.sleep(wait_time)
                    continue

                # サーバーエラー（503等）の場合
                if response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = int(self._calculate_backoff_delay(attempt))
                        self.logger.warning(
                            f"サーバーエラー ({response.status_code}): {wait_time}秒後にリトライします"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                # その他のエラーは最後の試行の場合は返す
                if attempt == max_retries:
                    return response

            except Exception as e:
                if attempt == max_retries:
                    raise e

                wait_time = int(self._calculate_backoff_delay(attempt))
                self.logger.warning(f"リクエストエラー: {e}, {wait_time}秒後にリトライします")
                await asyncio.sleep(wait_time)

        return None

    async def collect(
        self,
        target_dates: list[date] | None = None,
        **kwargs,
    ) -> list[tuple[str, str]]:
        """5chanからAI関連スレッドを収集します。

        Parameters
        ----------
        target_dates : list[date], optional
            収集対象日付リスト。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト（JSON, Markdown）。

        """
        try:
            log_processing_start(self.logger, "5chan AI関連スレッド")

            # 対象日付の正規化
            effective_target_dates = set(target_dates) if target_dates else target_dates_set(1)

            # 既存タイトルを読み込み
            existing_titles: set[str] = set()
            for target_date in effective_target_dates:
                target_datetime = datetime.combine(target_date, datetime.min.time())
                existing_records = await self._load_existing_threads(target_datetime)
                existing_titles.update(r.get("title", "") for r in existing_records)

            self.logger.info(f"🔍 既存タイトル数: {len(existing_titles)}件")

            # 各板からスレッド一覧を取得
            all_threads: list[Thread] = []
            self.logger.info("\n📡 板からスレッド取得中...")

            for board_id in self.target_boards.keys():
                try:
                    threads_data = await self._get_subject_txt_data(board_id)

                    if not threads_data:
                        self.logger.warning(f"   • {board_id}: スレッド一覧の取得に失敗")
                        continue

                    self.logger.info(f"   • {board_id}: {len(threads_data)}件のスレッドを取得")

                    # スレッドオブジェクトを作成
                    for thread_data in threads_data:
                        # 既存タイトルと重複チェック
                        if thread_data["title"] in existing_titles:
                            continue

                        # 日付フィルタリング
                        thread_timestamp = int(thread_data["timestamp"])
                        thread_datetime = datetime.fromtimestamp(thread_timestamp, tz=timezone.utc)
                        if not is_within_target_dates(thread_datetime, effective_target_dates):
                            continue

                        # スレッド詳細を取得
                        posts, error = await self._get_thread_posts_from_dat(thread_data["dat_url"])

                        if error or not posts:
                            continue

                        # Threadオブジェクトを作成
                        thread = Thread(
                            thread_id=thread_timestamp,
                            title=thread_data["title"],
                            url=thread_data["html_url"],
                            board=board_id,
                            timestamp=thread_timestamp,
                            posts=posts,
                            popularity_score=float(len(posts)),
                        )

                        all_threads.append(thread)

                except Exception as e:
                    self.logger.error(f"   • {board_id}: エラー - {e}")
                    continue

            # 日付ごとにスレッドをグループ化
            threads_by_date: dict[date, list[Thread]] = {}
            for thread in all_threads:
                thread_date = datetime.fromtimestamp(thread.timestamp, tz=timezone.utc).date()
                if thread_date not in threads_by_date:
                    threads_by_date[thread_date] = []
                threads_by_date[thread_date].append(thread)

            # 各日独立で上位15件を選択して結合
            selected_threads = []
            for target_date in sorted(effective_target_dates):
                if target_date in threads_by_date:
                    date_threads = threads_by_date[target_date]
                    if len(date_threads) <= self.TOTAL_LIMIT:
                        selected_threads.extend(date_threads)
                    else:

                        def sort_key(thread: Thread):
                            created = datetime.fromtimestamp(thread.timestamp, tz=timezone.utc)
                            return (thread.popularity_score, created)

                        sorted_threads = sorted(date_threads, key=sort_key, reverse=True)
                        selected_threads.extend(sorted_threads[: self.TOTAL_LIMIT])

            # 既存/新規スレッド数をカウント
            existing_count = 0  # 既存スレッド数（簡略化）
            new_count = len(selected_threads)  # 新規スレッド数

            # スレッド情報を表示
            log_article_counts(self.logger, existing_count, new_count)

            if selected_threads:
                log_summary_candidates(self.logger, selected_threads, "popularity_score")

                # 要約生成
                log_summarization_start(self.logger)
                for idx, thread in enumerate(selected_threads, 1):
                    await self._summarize_thread(thread)
                    log_summarization_progress(
                        self.logger, idx, len(selected_threads), thread.title
                    )

            # 要約を保存
            saved_files: list[tuple[str, str]] = []
            if selected_threads:
                # スレッドを保存
                saved_files = await self._store_summaries(
                    selected_threads, sorted(effective_target_dates)
                )

                # 処理完了メッセージ
                if saved_files:
                    self.logger.info(f"\n💾 {len(saved_files)}日分のデータを保存完了")
                    for json_path, md_path in saved_files:
                        log_storage_complete(self.logger, json_path, md_path)
                else:
                    log_no_new_articles(self.logger)
            else:
                log_no_new_articles(self.logger)

            return saved_files

        finally:
            # グローバルクライアントなのでクローズ不要
            pass

    def _build_board_url(self, board_id: str, server: str) -> str:
        """板URLを構築します。

        Parameters
        ----------
        board_id : str
            板のID。
        server : str
            サーバーのホスト名。

        Returns
        -------
        str
            構築された板URL。

        """
        return f"https://{server}/{board_id}/"

    def _get_board_server(self, board_id: str) -> str:
        """boards.tomlから板のサーバー情報を取得します。
        TASK-068: bbsmenu.html依存を除去し、静的設定から取得

        Parameters
        ----------
        board_id : str
            板のID。

        Returns
        -------
        str
            サーバーのホスト名。存在しない場合はデフォルト値。

        """
        # boards.tomlから直接サーバー情報を取得（bbsmenu.html依存除去）
        server = self.board_servers.get(board_id, "mevius.5ch.net")
        self.logger.info(f"板 {board_id} のサーバー: {server} (静的設定)")
        return server

    async def _get_with_403_tolerance(self, url: str, board_id: str) -> Any:
        """403エラー耐性HTTP GETリクエスト - think harderの結果
        複数のUser-Agent、ヘッダー戦略、間隔調整を試行

        Parameters
        ----------
        url : str
            リクエストURL
        board_id : str
            板ID（ログ用）

        Returns
        -------
        any
            HTTPレスポンス（成功時のみ、失敗時はNone）

        """
        strategies: list[dict[str, dict[str, str] | float]] = [
            # 戦略1: 標準的なブラウザヘッダー
            {
                "headers": {
                    **self.browser_headers,
                    "User-Agent": self._get_random_user_agent(),
                },
                "wait": 1.0,
            },
            # 戦略2: より詳細なブラウザヘッダー
            {
                "headers": {
                    **self.browser_headers,
                    "User-Agent": self._get_random_user_agent(),
                    "Referer": f"https://mevius.5ch.net/{board_id}/",
                },
                "wait": 2.0,
            },
            # 戦略3: シンプルなヘッダー
            {
                "headers": {
                    "User-Agent": self._get_random_user_agent(),
                    "Accept": "text/html",
                },
                "wait": 3.0,
            },
        ]

        for idx, strategy in enumerate(strategies, 1):
            try:
                headers = strategy["headers"]
                if not isinstance(headers, dict):
                    continue
                if not self.http_client:
                    return None
                response = await self.http_client.get(
                    url,
                    headers=headers,
                    timeout=10.0,
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    self.logger.info(f"   ✓ 戦略{idx}で成功: {board_id}")
                    return response

                if response.status_code == 403:
                    self.logger.warning(f"   ✗ 戦略{idx}で403エラー: {board_id}, 次の戦略を試行...")
                    wait_time = strategy["wait"]
                    if isinstance(wait_time, (int, float)):
                        await asyncio.sleep(wait_time)
                    continue

                # その他のエラー
                self.logger.warning(f"   ✗ 戦略{idx}でエラー ({response.status_code}): {board_id}")
                wait_time = strategy["wait"]
                if isinstance(wait_time, (int, float)):
                    await asyncio.sleep(wait_time)

            except Exception as e:
                self.logger.warning(f"   ✗ 戦略{idx}で例外: {board_id} - {e}")
                wait_time = strategy["wait"]
                if isinstance(wait_time, (int, float)):
                    await asyncio.sleep(wait_time)

        self.logger.error(f"   ✗ 全戦略失敗: {board_id}")
        return None

    async def _get_subject_txt_data(self, board_id: str) -> list[dict]:
        """subject.txt形式でスレッド一覧を取得（Cloudflare突破成功手法）

        Parameters
        ----------
        board_id : str
            板ID

        Returns
        -------
        List[dict]
            スレッド情報リスト

        """
        # 成功確認済みサーバーマッピング（実際のテスト結果に基づく）
        server_mapping = {
            "ai": ["krsw.5ch.net", "egg.5ch.net", "mevius.5ch.net"],
            "prog": ["medaka.5ch.net", "mevius.5ch.net"],
            "tech": ["mevius.5ch.net"],  # 修正: techはmevius.5ch.netのみ
            "esite": ["mevius.5ch.net"],  # 修正: esiteはmevius.5ch.netのみ
            "software": ["egg.5ch.net"],
            "bizplus": ["egg.5ch.net"],
            "news": ["hayabusa9.5ch.net"],
        }

        servers = server_mapping.get(board_id, [self._get_board_server(board_id)])

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; 5ch subject reader)",
            "Accept": "text/plain",
        }

        for server in servers:
            try:
                url = f"https://{server}/{board_id}/subject.txt"
                self.logger.info(f"subject.txt取得: {url}")

                # 直接httpxクライアントを使用（403回避のため）

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    # 文字化け対策（Shift_JIS + フォールバック）
                    try:
                        content = response.content.decode("shift_jis", errors="ignore")
                    except (UnicodeDecodeError, LookupError):
                        try:
                            content = response.content.decode("cp932", errors="ignore")
                        except (UnicodeDecodeError, LookupError):
                            try:
                                content = response.content.decode("utf-8", errors="ignore")
                            except (UnicodeDecodeError, LookupError):
                                content = response.text

                    threads_data = []
                    lines = content.split("\n")

                    import re

                    for line in lines:
                        if line.strip():
                            # dat形式解析: timestamp.dat<>title (post_count)
                            match = re.match(r"(\d+)\.dat<>(.+?)\s+\((\d+)\)", line)
                            if match:
                                timestamp, title, post_count = match.groups()
                                threads_data.append(
                                    {
                                        "server": server,
                                        "board": board_id,
                                        "timestamp": timestamp,
                                        "title": title.strip(),
                                        "post_count": int(post_count),
                                        "dat_url": f"https://{server}/{board_id}/dat/{timestamp}.dat",
                                        "html_url": f"https://{server}/test/read.cgi/{board_id}/{timestamp}/",
                                    }
                                )

                    self.logger.info(f"subject.txt成功: {len(threads_data)}スレッド取得")
                    return threads_data

            except Exception as e:
                self.logger.warning(f"subject.txt失敗 {server}: {e}")
                continue

        self.logger.error(f"subject.txt取得失敗（全サーバー）: {board_id}")
        return []

    async def _get_thread_posts_from_dat(self, dat_url: str) -> tuple[list[Post], str | None]:
        """.datファイルから投稿を取得します。

        Parameters
        ----------
        dat_url : str
            .datファイルのURL。

        Returns
        -------
        tuple[list[Post], str | None]
            投稿リストとエラーメッセージ（エラーがない場合はNone）。

        """
        try:
            # cloudscraperを使用してCloudflare保護を突破
            scraper = cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "mobile": False,
                }
            )

            # 非同期実行のためにasyncio.to_threadを使用
            response = await asyncio.to_thread(scraper.get, dat_url, timeout=10)

            if response.status_code != 200:
                return [], f"HTTP {response.status_code}"

            # Shift_JISでデコード
            try:
                content = response.content.decode("shift_jis", errors="ignore")
            except (UnicodeDecodeError, LookupError):
                try:
                    content = response.content.decode("cp932", errors="ignore")
                except (UnicodeDecodeError, LookupError):
                    content = response.text

            # .dat形式をパース
            posts = []
            lines = content.split("\n")

            # 最大投稿数を制限（メモリ効率化）
            limited_lines = lines[:MAX_POSTS_PER_THREAD]

            for idx, line in enumerate(limited_lines, 1):
                if not line.strip():
                    continue

                # .dat形式: name<>mail<>date<>content<>title
                parts = line.split("<>")
                if len(parts) >= 4:
                    post = Post(
                        no=idx,
                        name=parts[0].strip(),
                        mail=parts[1].strip(),
                        date=parts[2].strip(),
                        content=parts[3].strip(),
                    )
                    posts.append(post)

            return posts, None

        except Exception as e:
            return [], str(e)

    async def _summarize_thread(self, thread: Thread) -> None:
        """スレッドを要約します。

        Parameters
        ----------
        thread : Thread
            要約対象のスレッド。

        """
        # 投稿内容を結合
        thread_content = "\n".join(
            f"[{post.no}] {post.name} ({post.date}): {post.content}"
            for post in thread.posts[:MAX_POSTS_PER_THREAD]
        )

        prompt = f"""
        以下の5chanスレッドを要約してください:

        タイトル: {thread.title}
        板: {thread.board}

        {thread_content}

        要約は以下の形式で行い、日本語で回答してください:
        1. スレッドの主な内容（1-2文）
        2. 議論の主要ポイント（箇条書き3-5点）
        3. スレッドの全体的な論調

        注意：攻撃的な内容やヘイトスピーチは緩和し、主要な技術的議論に焦点を当ててください。
        """

        system_instruction = """
        あなたは5chan（旧2ちゃんねる）スレッドの要約を行うアシスタントです。
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
            self.logger.error(f"要約の生成中にエラーが発生しました: {e!s}")
            thread.summary = f"要約の生成中にエラーが発生しました: {e!s}"

    async def _store_summaries(
        self, threads: list[Thread], target_dates: list[date]
    ) -> list[tuple[str, str]]:
        if not threads:
            self.logger.info("保存するスレッドがありません")
            return []

        default_date = max(target_dates) if target_dates else datetime.now().date()
        records = self._serialize_threads(threads)
        records_by_date = group_records_by_date(records, default_date=default_date)

        saved_files = await store_daily_snapshots(
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

        return saved_files

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
        published: datetime
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

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        content = f"# 5chan AI関連スレッド ({today.strftime('%Y-%m-%d')})\n\n"
        grouped: dict[str, list[dict]] = {}
        for record in records:
            board = record.get("board", "unknown")
            grouped.setdefault(board, []).append(record)

        for board, threads in grouped.items():
            board_name = self.target_boards.get(board, board)
            content += f"## {board_name} (/{board}/)\n\n"
            for thread in threads:
                title = thread.get("title") or f"無題スレッド #{thread.get('thread_id')}"
                content += f"### [{title}]({thread.get('url')})\n\n"
                published_raw = thread.get("published_at")
                if published_raw:
                    try:
                        date_str = datetime.fromisoformat(published_raw).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        date_str = published_raw
                else:
                    timestamp = thread.get("timestamp")
                    if timestamp:
                        try:
                            date_str = datetime.fromtimestamp(
                                int(timestamp), tz=timezone.utc
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            date_str = "N/A"
                    else:
                        date_str = "N/A"
                content += f"作成日時: {date_str}\n\n"
                content += f"**要約**:\n{thread.get('summary', '')}\n\n"
                content += "---\n\n"
        return content

    def _parse_markdown(self, markdown: str) -> list[dict]:
        records: list[dict] = []
        board_pattern = re.compile(r"^##\s+(.+) \(/(.+)/\)$", re.MULTILINE)
        thread_pattern = re.compile(
            r"### \[(?P<title>.+?)\]\((?P<url>[^\)]+)\)\n\n"
            r"作成日時: (?P<datetime>.+?)\n\n"
            r"\*\*要約\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        sections = list(board_pattern.finditer(markdown))
        for idx, match in enumerate(sections):
            start = match.end()
            end = sections[idx + 1].start() if idx + 1 < len(sections) else len(markdown)
            block = markdown[start:end]
            board_id = match.group(2).strip()

            for thread_match in thread_pattern.finditer(block + "---"):
                title = thread_match.group("title")
                url = thread_match.group("url")
                summary = thread_match.group("summary").strip()
                datetime_str = thread_match.group("datetime")
                try:
                    published = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    published = None

                record = {
                    "thread_id": 0,
                    "title": title.strip(),
                    "url": url.strip(),
                    "summary": summary,
                    "popularity_score": 0.0,
                    "board": board_id,
                }

                if published:
                    record["published_at"] = published.replace(tzinfo=timezone.utc).isoformat()
                    record["timestamp"] = int(published.timestamp())

                records.append(record)

        return records
