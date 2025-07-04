import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import cloudscraper
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.gpt_client import GPTClient
from nook.common.storage import LocalStorage


@dataclass
class Thread:
    """
    5chanスレッド情報。
    
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
    posts : List[Dict[str, Any]]
        投稿リスト。
    timestamp : int
        作成タイムスタンプ。
    """
    
    thread_id: int
    title: str
    url: str
    board: str
    posts: List[Dict[str, Any]]
    timestamp: int
    summary: str = field(default="")


class FiveChanExplorer(BaseService):
    """
    5chan（旧2ちゃんねる）から情報を収集するクラス。
    
    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """
    
    def __init__(self, storage_dir: str = "data"):
        """
        FiveChanExplorerを初期化します。
        
        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("fivechan_explorer")
        self.http_client = None  # setup_http_clientで初期化
        self.gpt_client = GPTClient()
        self.storage = LocalStorage(storage_dir)
        
        # 対象となる板
        self.target_boards = self._load_boards()
        
        # 試すサブドメインのリスト（すべての板で試す）
        self.subdomains = [
            "mevius.5ch.net", 
            "egg.5ch.net", 
            "medaka.5ch.net", 
            "hayabusa9.5ch.net", 
            "mi.5ch.net",
            "lavender.5ch.net",
            "eagle.5ch.net",
            "rosie.5ch.net",
            "fate.5ch.net"
        ]
        
        # AIに関連するキーワード
        self.ai_keywords = [
            "ai", "人工知能", "機械学習", "ディープラーニング", 
            "ニューラルネットワーク", "gpt", "llm", "chatgpt", "claude", "gemini", "grok", 
            "anthropic", "openai", "stable diffusion", "dalle", "midjourney",
            "自然言語処理", "大規模言語モデル", "チャットボット", "対話型ai",
            "生成ai", "画像生成", "alphaゴー", "alphago", "deepmind",
            "強化学習", "自己学習", "強い人工知能", "弱い人工知能", "特化型人工知能", 
            "pixai", "comfyui", "stablediffusion", "ai画像", "ai動画"
        ]
        
        # 改善されたリクエスト制御設定
        self.min_request_delay = 5  # 最小遅延時間（秒）
        self.max_request_delay = 10  # 最大遅延時間（秒）
        self.request_delay = 2  # 下位互換性のため保持
        
        # User-Agentローテーション用のリスト
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
        ]
        
        # ブラウザヘッダーの完全設定（User-Agentは動的に設定）
        self.browser_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Referer": "https://5ch.net/"
        }
    
    def _load_boards(self) -> Dict[str, str]:
        """
        対象となる板の設定を読み込みます。
        
        Returns
        -------
        Dict[str, str]
            板のID: 板の名前のディクショナリ
        """
        script_dir = Path(__file__).parent
        with open(script_dir / "boards.toml", "rb") as f:
            import tomli
            config = tomli.load(f)
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
        """
        ランダムなUser-Agentを取得します。
        
        Returns
        -------
        str
            ランダムに選択されたUser-Agent文字列。
        """
        import random
        return random.choice(self.user_agents)
    
    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        指数バックオフによる遅延時間を計算します。
        
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
        base_delay = min(2 ** retry_count, 300)
        return base_delay
    
    async def _get_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> any:
        """
        リトライ機能付きHTTP GETリクエスト。
        
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
        import asyncio
        
        for attempt in range(max_retries + 1):
            try:
                # 動的なUser-Agentでヘッダーを更新
                headers = self.browser_headers.copy()
                headers["User-Agent"] = self._get_random_user_agent()
                
                response = await self.http_client.get(url, headers=headers, **kwargs)
                
                # 成功レスポンス（200番台）の場合は返す
                if 200 <= response.status_code < 300:
                    return response
                
                # レート制限エラー（429）の場合
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = self._calculate_backoff_delay(attempt)
                    
                    self.logger.warning(f"レート制限検知 (429): {wait_time}秒待機します")
                    await asyncio.sleep(wait_time)
                    continue
                
                # サーバーエラー（503等）の場合
                if response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = self._calculate_backoff_delay(attempt)
                        self.logger.warning(f"サーバーエラー ({response.status_code}): {wait_time}秒後にリトライします")
                        await asyncio.sleep(wait_time)
                        continue
                
                # その他のエラーは最後の試行の場合は返す
                if attempt == max_retries:
                    return response
                    
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                wait_time = self._calculate_backoff_delay(attempt)
                self.logger.warning(f"リクエストエラー: {e}, {wait_time}秒後にリトライします")
                await asyncio.sleep(wait_time)
        
        # ここには到達しないはずですが、安全のため
        return response
    
    def run(self, thread_limit: int = 5) -> None:
        """
        5chanからAI関連スレッドを収集して保存します。
        
        Parameters
        ----------
        thread_limit : int, default=5
            各板から取得するスレッド数。
        """
        asyncio.run(self.collect(thread_limit))
    
    async def collect(self, thread_limit: int = 5) -> None:
        """
        5chanからAI関連スレッドを収集して保存します（非同期版）。
        
        Parameters
        ----------
        thread_limit : int, default=5
            各板から取得するスレッド数。
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()
        
        all_threads = []
        
        try:
            # 各板からスレッドを取得
            for board_id, board_name in self.target_boards.items():
                try:
                    self.logger.info(f"板 /{board_id}/({board_name}) からのスレッド取得を開始します...")
                    threads = await self._retrieve_ai_threads(board_id, thread_limit)
                    self.logger.info(f"板 /{board_id}/({board_name}) から {len(threads)} 件のスレッドを取得しました")
                    
                    # スレッドを要約
                    for thread in threads:
                        await self._summarize_thread(thread)
                    
                    all_threads.extend(threads)
                    
                    # 改善されたリクエスト間遅延（ランダム化）
                    import random
                    delay = random.uniform(self.min_request_delay, self.max_request_delay)
                    self.logger.debug(f"リクエスト間遅延: {delay:.1f}秒")
                    await asyncio.sleep(delay)
                
                except Exception as e:
                    self.logger.error(f"Error processing board /{board_id}/: {str(e)}")
            
            self.logger.info(f"合計 {len(all_threads)} 件のスレッドを取得しました")
            
            # 要約を保存
            if all_threads:
                await self._store_summaries(all_threads)
                self.logger.info(f"スレッドの要約を保存しました")
            else:
                self.logger.info("保存するスレッドがありません")
                
        finally:
            # グローバルクライアントなのでクローズ不要
            pass
    
    def _build_board_url(self, board_id: str, server: str) -> str:
        """
        板URLを構築します。
        
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
        """
        boards.tomlから板のサーバー情報を取得します。
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
    
    async def _get_with_403_tolerance(self, url: str, board_id: str) -> any:
        """
        403エラー耐性HTTP GETリクエスト - think harderの結果
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
        # 段階的User-Agent戦略（古い順に試行）
        user_agent_strategies = [
            # 戦略1: 最古典的ブラウザ（2010年代前半）
            "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)",
            # 戦略2: 古いFirefox（検出回避）
            "Mozilla/5.0 (Windows NT 6.1; rv:12.0) Gecko/20100101 Firefox/12.0",
            # 戦略3: 古いChrome（最低限）
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36",
            # 戦略4: モバイル回避（サーバー負荷軽減と判断される場合）
            "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53",
            # 戦略5: 検索エンジンbot模倣（アクセス許可される場合）
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        ]
        
        for i, user_agent in enumerate(user_agent_strategies):
            try:
                self.logger.info(f"403対策戦略 {i+1}/{len(user_agent_strategies)}: {user_agent[:50]}...")
                
                # 極限まで簡素化されたヘッダー
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html",
                    "Connection": "close"  # 持続接続を回避
                }
                
                # 戦略別の待機時間（段階的に延長）
                wait_time = 2 + (i * 3)  # 2秒から始まり3秒ずつ増加
                await asyncio.sleep(wait_time)
                
                # HTTPクライアントに直接アクセス（リトライ処理を回避）
                try:
                    response = await self.http_client._client.get(
                        url,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    # レスポンス内容の詳細分析（Cloudflare検出）
                    is_cloudflare = "Just a moment..." in response.text or "challenge" in response.text.lower()
                    
                    if response.status_code == 200:
                        if not is_cloudflare:
                            self.logger.info(f"成功: 戦略{i+1}で正常アクセス")
                            return response
                        else:
                            self.logger.warning(f"戦略{i+1}: Cloudflareチャレンジページ検出")
                    elif response.status_code == 403:
                        if is_cloudflare:
                            self.logger.warning(f"戦略{i+1}: Cloudflare保護により403エラー")
                            # Cloudflareの場合は長時間待機後にリトライ
                            if i < 2:  # 最初の2戦略のみリトライ
                                self.logger.info(f"Cloudflare回避: 30秒待機後にリトライ")
                                await asyncio.sleep(30)
                                continue
                        elif response.text and len(response.text) > 100 and not is_cloudflare:
                            self.logger.warning(f"403エラーだが有効コンテンツ取得: 戦略{i+1} ({len(response.text)}文字)")
                            return response
                        else:
                            self.logger.warning(f"戦略{i+1}: 403エラー（利用不可コンテンツ）")
                    else:
                        self.logger.warning(f"戦略{i+1}: HTTPエラー {response.status_code}")
                        
                except Exception as e:
                    self.logger.warning(f"戦略{i+1}: リクエストエラー - {str(e)}")
                    continue
                    
            except Exception as e:
                self.logger.error(f"戦略{i+1}: 予期しないエラー - {str(e)}")
                continue
        
        # 最終戦略: 代替エンドポイント試行
        self.logger.info("代替エンドポイント戦略を開始...")
        alternative_response = await self._try_alternative_endpoints(url, board_id)
        if alternative_response:
            return alternative_response
        
        # すべての戦略が失敗
        self.logger.error(f"全戦略失敗: 板 {board_id} へのアクセスを断念")
        return None
    
    async def _try_alternative_endpoints(self, original_url: str, board_id: str) -> any:
        """
        代替エンドポイント戦略 - 最終手段のアクセス方法
        
        Parameters
        ----------
        original_url : str
            元のURL
        board_id : str
            板ID
            
        Returns
        -------
        any
            成功時のレスポンス、失敗時はNone
        """
        # URL解析
        from urllib.parse import urlparse
        parsed = urlparse(original_url)
        server = parsed.netloc
        
        alternative_strategies = [
            # 戦略1: スマートフォン版
            f"https://sp.5ch.net/{board_id}/",
            # 戦略2: 旧形式URL
            f"https://{server.replace('.5ch.net', '.2ch.net')}/{board_id}/",
            # 戦略3: 読み取り専用API風
            f"https://{server}/{board_id}/subject.txt",
            # 戦略4: 別サブドメイン
            f"https://itest.5ch.net/{board_id}/",
            # 戦略5: HTTPSなし（最終手段）
            f"http://{server}/{board_id}/"
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.80 Mobile Safari/537.36",
            "Accept": "text/plain, text/html, */*",
            "Accept-Language": "ja,en;q=0.9",
            "Connection": "close"
        }
        
        for i, alt_url in enumerate(alternative_strategies):
            try:
                self.logger.info(f"代替戦略 {i+1}/{len(alternative_strategies)}: {alt_url}")
                await asyncio.sleep(3)  # 短い間隔
                
                response = await self.http_client._client.get(
                    alt_url,
                    headers=headers,
                    timeout=20.0
                )
                
                # 成功判定を緩く設定
                if response.status_code in [200, 403]:
                    content = response.text
                    is_valid = (
                        len(content) > 50 and 
                        "Just a moment" not in content and
                        "challenge" not in content.lower() and
                        ("5ch" in content or "2ch" in content or "\n" in content)  # 最低限のコンテンツ検証
                    )
                    
                    if is_valid:
                        self.logger.info(f"代替戦略{i+1}成功: {response.status_code} ({len(content)}文字)")
                        return response
                    else:
                        self.logger.warning(f"代替戦略{i+1}: 無効コンテンツ ({len(content)}文字)")
                else:
                    self.logger.warning(f"代替戦略{i+1}: HTTPエラー {response.status_code}")
                    
            except Exception as e:
                self.logger.warning(f"代替戦略{i+1}: エラー - {str(e)}")
                continue
        
        return None
    
    async def _get_subject_txt_data(self, board_id: str) -> List[dict]:
        """
        subject.txt形式でスレッド一覧を取得（Cloudflare突破成功手法）
        
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
            'ai': ['egg.5ch.net', 'mevius.5ch.net'],
            'prog': ['medaka.5ch.net', 'mevius.5ch.net'], 
            'tech': ['mevius.5ch.net'],  # 修正: techはmevius.5ch.netのみ
            'esite': ['mevius.5ch.net'],  # 修正: esiteはmevius.5ch.netのみ
            'software': ['egg.5ch.net'],
            'bizplus': ['egg.5ch.net'],
            'news': ['hayabusa9.5ch.net']
        }
        
        servers = server_mapping.get(board_id, [self._get_board_server(board_id)])
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; 5ch subject reader)',
            'Accept': 'text/plain'
        }
        
        for server in servers:
            try:
                url = f"https://{server}/{board_id}/subject.txt"
                self.logger.info(f"subject.txt取得: {url}")
                
                # 直接httpxクライアントを使用（403回避のため）
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    # 文字化け対策（Shift_JIS + フォールバック）
                    try:
                        content = response.content.decode('shift_jis', errors='ignore')
                    except:
                        try:
                            content = response.content.decode('cp932', errors='ignore')
                        except:
                            try:
                                content = response.content.decode('utf-8', errors='ignore')
                            except:
                                content = response.text
                    
                    threads_data = []
                    lines = content.split('\n')
                    
                    import re
                    for line in lines:
                        if line.strip():
                            # dat形式解析: timestamp.dat<>title (post_count)
                            match = re.match(r'(\d+)\.dat<>(.+?)\s+\((\d+)\)', line)
                            if match:
                                timestamp, title, post_count = match.groups()
                                threads_data.append({
                                    'server': server,
                                    'board': board_id,
                                    'timestamp': timestamp,
                                    'title': title.strip(),
                                    'post_count': int(post_count),
                                    'dat_url': f"https://{server}/{board_id}/dat/{timestamp}.dat",
                                    'html_url': f"https://{server}/test/read.cgi/{board_id}/{timestamp}/"
                                })
                    
                    self.logger.info(f"subject.txt成功: {len(threads_data)}スレッド取得")
                    return threads_data
                    
            except Exception as e:
                self.logger.warning(f"subject.txt失敗 {server}: {e}")
                continue
        
        return []
    
    async def _get_thread_posts_from_dat(self, dat_url: str) -> List[Dict[str, Any]]:
        """
        dat形式でスレッドの投稿を取得（cloudscraper使用版）
        """
        try:
            self.logger.info(f"dat取得開始: {dat_url}")
            
            # cloudscraper セッションを作成
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            # Monazilla形式のヘッダーを設定
            scraper.headers.update({
                'User-Agent': 'Monazilla/1.00 (NookCrawler/1.0)',
                'Accept-Encoding': 'gzip',
                'Referer': dat_url.replace('/dat/', '/test/read.cgi/').replace('.dat', '/')
            })
            
            # 同期的にリクエスト（cloudscraperは同期ライブラリ）
            # asyncio.to_threadで非同期化
            response = await asyncio.to_thread(scraper.get, dat_url, timeout=30)
            self.logger.info(f"dat取得レスポンス: {response.status_code}")
            
            if response.status_code == 200:
                # 文字化け対策（Shift_JIS + フォールバック）
                try:
                    content = response.content.decode('shift_jis', errors='ignore')
                except:
                    try:
                        content = response.content.decode('cp932', errors='ignore')
                    except:
                        content = response.text
                
                posts = []
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if line.strip():
                        # dat形式: name<>mail<>date ID<>message<>title(1行目のみ)
                        parts = line.split('<>')
                        if len(parts) >= 4:
                            post_data = {
                                'no': i + 1,
                                'name': parts[0],
                                'mail': parts[1], 
                                'date': parts[2],
                                'com': parts[3],
                                'time': parts[2]  # 互換性のため
                            }
                            
                            # 1行目の場合はタイトルも含まれる
                            if i == 0 and len(parts) >= 5:
                                post_data['title'] = parts[4]
                            
                            posts.append(post_data)
                
                self.logger.info(f"dat解析完了: 総行数{len(lines)}, 有効投稿{len(posts)}件")
                if posts:
                    self.logger.info(f"dat取得成功: {len(posts)}投稿")
                    return posts[:10]  # 最初の10投稿
                else:
                    self.logger.warning(f"dat内容は取得したが投稿データなし")
                    return []
            else:
                self.logger.error(f"dat取得HTTP error: {response.status_code}")
                if "Just a moment" in response.text:
                    self.logger.error("Cloudflareチャレンジページが検出されました")
                return []
                
        except Exception as e:
            self.logger.error(f"dat取得エラー {dat_url}: {e}")
            import traceback
            self.logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        return []

    async def _retrieve_ai_threads(self, board_id: str, limit: int) -> List[Thread]:
        """
        特定の板からAI関連スレッドを取得します。
        【Cloudflare突破成功版】subject.txt + dat形式による完全実装
        
        Parameters
        ----------
        board_id : str
            板のID。
        limit : int
            取得するスレッド数。
            
        Returns
        -------
        List[Thread]
            取得したスレッドのリスト。
        """
        try:
            self.logger.info(f"【突破手法】板 {board_id} からAI関連スレッドを取得します")
            
            # 1. subject.txtからスレッド一覧を取得（突破成功手法）
            threads_data = await self._get_subject_txt_data(board_id)
            if not threads_data:
                self.logger.warning(f"subject.txt取得失敗: 板 {board_id}")
                return []
            
            # 2. AI関連スレッドをフィルタリング
            ai_threads = []
            self.logger.info(f"AI関連スレッド検索中... 対象: {len(threads_data)}スレッド")
            
            for thread_data in threads_data:
                title = thread_data['title']
                title_lower = title.lower()
                
                # AIキーワードマッチング
                is_ai_related = any(keyword.lower() in title_lower for keyword in self.ai_keywords)
                
                if is_ai_related:
                    self.logger.info(f"AI関連スレッド発見: {title}")
                    
                    # 3. dat形式で投稿データを取得（突破成功手法）
                    posts = await self._get_thread_posts_from_dat(thread_data['dat_url'])
                    
                    if posts:  # 投稿取得成功時のみスレッド作成
                        thread = Thread(
                            thread_id=int(thread_data['timestamp']),
                            title=title,
                            url=thread_data['html_url'],  # HTML版URL
                            board=board_id,
                            posts=posts,
                            timestamp=int(thread_data['timestamp'])
                        )
                        
                        ai_threads.append(thread)
                        self.logger.info(f"スレッド追加成功: {title} ({len(posts)}投稿)")
                        
                        # 制限数に達したら終了
                        if len(ai_threads) >= limit:
                            break
                    else:
                        self.logger.warning(f"投稿取得失敗: {title}")
                    
                    # アクセス間隔（丁寧なアクセス）
                    await asyncio.sleep(2)
            
            self.logger.info(f"【突破成功】板 {board_id}: {len(ai_threads)}件のAI関連スレッド取得完了")
            return ai_threads
            
        except Exception as e:
            self.logger.error(f"【突破手法エラー】板 {board_id}: {str(e)}")
            return []
    
    async def _summarize_thread(self, thread: Thread) -> None:
        """
        スレッドを要約します。
        
        Parameters
        ----------
        thread : Thread
            要約するスレッド。
        """
        # スレッドのコンテンツを抽出
        thread_content = ""
        
        # スレッドのタイトルを追加
        thread_content += f"タイトル: {thread.title}\n\n"
        
        # オリジナルポスト（OP）を追加
        if thread.posts and len(thread.posts) > 0:
            op = thread.posts[0]
            op_text = op.get("com", "")
            if op_text:
                thread_content += f">>1: {op_text}\n\n"
        
        # 返信を追加（最大5件）
        replies = thread.posts[1:6] if len(thread.posts) > 1 else []
        for i, reply in enumerate(replies):
            reply_text = reply.get("com", "")
            if reply_text:
                post_number = reply.get("no", i+2)
                thread_content += f">>{post_number}: {reply_text}\n\n"
        
        prompt = f"""
        以下の5chan（旧2ちゃんねる）スレッドを要約してください。

        板: /{thread.board}/
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
                max_tokens=1000
            )
            thread.summary = summary
        except Exception as e:
            self.logger.error(f"要約の生成中にエラーが発生しました: {str(e)}")
            thread.summary = f"要約の生成中にエラーが発生しました: {str(e)}"
    
    async def _store_summaries(self, threads: List[Thread]) -> None:
        """
        要約を保存します。
        
        Parameters
        ----------
        threads : List[Thread]
            保存するスレッドのリスト。
        """
        today = datetime.now()
        content = f"# 5chan AI関連スレッド ({today.strftime('%Y-%m-%d')})\n\n"
        
        # 板ごとに整理
        boards = {}
        for thread in threads:
            if thread.board not in boards:
                boards[thread.board] = []
            
            boards[thread.board].append(thread)
        
        # Markdownを生成
        for board, board_threads in boards.items():
            board_name = self.target_boards.get(board, board)
            content += f"## {board_name} (/{board}/)\n\n"
            
            for thread in board_threads:
                formatted_title = thread.title if thread.title else f"無題スレッド #{thread.thread_id}"
                content += f"### [{formatted_title}]({thread.url})\n\n"
                
                # 投稿日時
                date_str = datetime.fromtimestamp(thread.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                content += f"作成日時: {date_str}\n\n"
                
                content += f"**要約**:\n{thread.summary}\n\n"
                
                content += "---\n\n"
        
        # 保存
        self.logger.info(f"fivechan_explorer ディレクトリに保存します: {today.strftime('%Y-%m-%d')}.md")
        try:
            self.storage.save_markdown(content, "fivechan_explorer", today)
            self.logger.info("保存が完了しました")
        except Exception as e:
            self.logger.error(f"保存中にエラーが発生しました: {str(e)}")
            # ディレクトリを作成して再試行
            try:
                fivechan_explorer_dir = Path(self.storage.base_dir) / "fivechan_explorer"
                fivechan_explorer_dir.mkdir(parents=True, exist_ok=True)
    
                file_path = fivechan_explorer_dir / f"{today.strftime('%Y-%m-%d')}.md"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info(f"再試行で保存に成功しました: {file_path}")
            except Exception as e2:
                self.logger.error(f"再試行でも保存に失敗しました: {str(e2)}")
