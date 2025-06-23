# TASK-005: サービスクラスのリファクタリング

## 割り当て: backend

## 目的
すべての既存サービスクラスを新しい基底クラス（BaseService）を継承するように修正し、共通処理を統一化する。

## 背景
TASK-001で作成された基底クラスとTASK-003で実装された非同期処理を活用し、既存のサービスクラスをリファクタリングする必要がある。

## 前提条件
- TASK-001（基底クラス）が完了していること
- TASK-003（非同期処理）が完了していること

## 実装内容

### 1. GitHubTrendingServiceのリファクタリング
**ファイル**: `nook/services/github_trending.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
import toml

from nook.common.base_service import BaseService
from nook.common.decorators import handle_errors, log_execution_time
from nook.common.exceptions import ServiceException, DataException
from nook.common.http_client import get_http_client
from nook.common.async_utils import gather_with_errors, run_with_semaphore


class GitHubTrendingService(BaseService):
    """GitHub Trending リポジトリ収集サービス"""
    
    def __init__(self):
        super().__init__("github_trending")
        self.api_base_url = "https://api.github.com"
        self.languages = self._load_languages()
    
    def _load_languages(self) -> List[str]:
        """言語設定を読み込み"""
        config_path = self.get_config_path("languages.toml")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
                languages = config.get("languages", [])
                self.logger.info(f"Loaded {len(languages)} languages")
                return languages
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}")
            return ["python", "javascript", "go"]
        except Exception as e:
            raise DataException(f"Failed to load languages config: {e}") from e
    
    @log_execution_time
    @handle_errors(retries=3)
    async def collect(self) -> None:
        """トレンドリポジトリを収集"""
        self.logger.info("Starting GitHub trending collection")
        
        async with await get_http_client() as client:
            # 各言語のトレンドを並行取得
            tasks = [
                self._collect_language_repos(client, lang)
                for lang in self.languages
            ]
            
            results = await gather_with_errors(
                *tasks,
                task_names=self.languages
            )
            
            # 成功した結果のみを統合
            all_repos = []
            for result in results:
                if result.success and result.result:
                    all_repos.extend(result.result)
                elif not result.success:
                    self.logger.error(
                        f"Failed to collect {result.name}: {result.error}"
                    )
            
            if not all_repos:
                raise ServiceException("No repositories collected")
            
            # リポジトリ詳細を並行取得
            enriched_repos = await self._enrich_repositories(client, all_repos)
            
            # レポート生成と保存
            report = await self._generate_report(enriched_repos)
            filename = f"github_trending_{datetime.now():%Y-%m-%d}.md"
            await self.save_markdown(report, filename)
            
            # サマリーデータも保存
            summary = self._create_summary(enriched_repos)
            await self.save_json(summary, f"summary_{datetime.now():%Y-%m-%d}.json")
            
            self.logger.info(
                f"Successfully collected {len(enriched_repos)} repositories"
            )
    
    async def _collect_language_repos(
        self,
        client,
        language: str
    ) -> List[Dict[str, Any]]:
        """特定言語のリポジトリを収集"""
        params = {
            "q": f"language:{language} created:>={datetime.now():%Y-%m-%d}",
            "sort": "stars",
            "order": "desc",
            "per_page": 10
        }
        
        url = f"{self.api_base_url}/search/repositories"
        response = await client.get_json(url, params=params)
        
        repos = response.get("items", [])
        self.logger.debug(f"Found {len(repos)} repos for {language}")
        
        return repos
    
    async def _enrich_repositories(
        self,
        client,
        repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """リポジトリに詳細情報を追加"""
        async def enrich_single_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # READMEを取得
                readme = await self._fetch_readme(client, repo)
                if readme:
                    # 要約を生成
                    summary = await self._summarize_content(readme, repo["name"])
                    repo["ai_summary"] = summary
                else:
                    repo["ai_summary"] = repo.get("description", "")
                
                # 追加の統計情報
                repo["quality_score"] = self._calculate_quality_score(repo)
                
                return repo
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to enrich {repo['name']}: {e}",
                    extra={"repo": repo["full_name"]}
                )
                repo["ai_summary"] = repo.get("description", "")
                return repo
        
        # 並行処理（レート制限を考慮）
        tasks = [enrich_single_repo(repo) for repo in repos]
        enriched = await run_with_semaphore(tasks, max_concurrent=5)
        
        return enriched
    
    async def _fetch_readme(
        self,
        client,
        repo: Dict[str, Any]
    ) -> Optional[str]:
        """READMEコンテンツを取得"""
        try:
            url = f"{repo['url']}/readme"
            headers = {"Accept": "application/vnd.github.v3.raw"}
            
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text[:5000]  # 最大5000文字
                
        except Exception as e:
            self.logger.debug(f"README not found for {repo['name']}: {e}")
        
        return None
    
    async def _summarize_content(self, content: str, repo_name: str) -> str:
        """コンテンツをAIで要約"""
        prompt = f"""
        以下のGitHubリポジトリ「{repo_name}」のREADMEを、
        日本語で100文字以内で要約してください。
        技術的な特徴と主な用途を含めてください。
        
        README:
        {content}
        """
        
        return await self.gpt_client.generate_async(
            prompt,
            max_tokens=200,
            temperature=0.5
        )
    
    def _calculate_quality_score(self, repo: Dict[str, Any]) -> float:
        """リポジトリの品質スコアを計算"""
        score = 0.0
        
        # スター数（対数スケール）
        stars = repo.get("stargazers_count", 0)
        if stars > 0:
            import math
            score += min(math.log10(stars) * 10, 40)
        
        # フォーク数
        forks = repo.get("forks_count", 0)
        if forks > 0:
            score += min(forks / 10, 20)
        
        # 更新頻度
        updated = repo.get("updated_at", "")
        if updated:
            from datetime import datetime, timezone
            updated_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - updated_date).days
            if days_ago < 30:
                score += 20
            elif days_ago < 90:
                score += 10
        
        # ドキュメント
        if repo.get("description"):
            score += 10
        if repo.get("homepage"):
            score += 10
        
        return min(score, 100.0)
    
    async def _generate_report(self, repos: List[Dict[str, Any]]) -> str:
        """Markdownレポートを生成"""
        lines = [
            f"# GitHub Trending - {datetime.now():%Y年%m月%d日}",
            "",
            "本日のトレンドリポジトリをAIが分析しました。",
            "",
            "## サマリー",
            f"- 収集リポジトリ数: {len(repos)}",
            f"- 対象言語: {', '.join(self.languages)}",
            ""
        ]
        
        # 言語別にグループ化
        by_language = {}
        for repo in repos:
            lang = repo.get("language", "Other")
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(repo)
        
        # 品質スコアでソート
        for lang, lang_repos in sorted(by_language.items()):
            lines.extend([
                f"## {lang}",
                ""
            ])
            
            sorted_repos = sorted(
                lang_repos,
                key=lambda x: x.get("quality_score", 0),
                reverse=True
            )
            
            for repo in sorted_repos[:5]:  # 各言語上位5件
                lines.extend([
                    f"### [{repo['name']}]({repo['html_url']})",
                    "",
                    f"- ⭐ **{repo['stargazers_count']:,}** stars"
                    f" | 🍴 **{repo['forks_count']:,}** forks",
                    f"- 📊 品質スコア: {repo['quality_score']:.1f}/100",
                    f"- 🏷️ トピック: {', '.join(repo.get('topics', [])[:5]) or 'なし'}",
                    "",
                    "**概要**:",
                    repo.get("ai_summary", repo.get("description", "")),
                    "",
                    "---",
                    ""
                ])
        
        return "\n".join(lines)
    
    def _create_summary(self, repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """サマリーデータを作成"""
        return {
            "date": datetime.now().isoformat(),
            "total_repos": len(repos),
            "languages": list({r.get("language") for r in repos if r.get("language")}),
            "top_repos": [
                {
                    "name": r["name"],
                    "url": r["html_url"],
                    "stars": r["stargazers_count"],
                    "language": r.get("language"),
                    "score": r.get("quality_score", 0)
                }
                for r in sorted(repos, key=lambda x: x.get("quality_score", 0), reverse=True)[:10]
            ],
            "stats": {
                "avg_stars": sum(r["stargazers_count"] for r in repos) / len(repos) if repos else 0,
                "avg_forks": sum(r["forks_count"] for r in repos) / len(repos) if repos else 0,
                "total_stars": sum(r["stargazers_count"] for r in repos)
            }
        }
```

### 2. RedditExplorerServiceのリファクタリング
**ファイル**: `nook/services/reddit_explorer.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import toml
import praw
from prawcore.exceptions import ResponseException, RequestException

from nook.common.base_service import BaseService
from nook.common.decorators import handle_errors, log_execution_time
from nook.common.exceptions import ServiceException, APIException, ConfigurationException
from nook.common.async_utils import gather_with_errors, run_sync_in_thread


class RedditExplorerService(BaseService):
    """Reddit投稿収集・分析サービス"""
    
    def __init__(self):
        super().__init__("reddit_explorer")
        self.reddit_client = self._initialize_reddit()
        self.subreddits = self._load_subreddits()
    
    def _initialize_reddit(self) -> praw.Reddit:
        """Redditクライアントを初期化"""
        try:
            client_id = self.config.REDDIT_CLIENT_ID
            client_secret = self.config.REDDIT_CLIENT_SECRET
            
            if not client_id or not client_secret:
                raise ConfigurationException(
                    "Reddit credentials not found in environment"
                )
            
            return praw.Reddit(
                client_id=client_id.get_secret_value(),
                client_secret=client_secret.get_secret_value(),
                user_agent=self.config.REDDIT_USER_AGENT
            )
            
        except Exception as e:
            raise ConfigurationException(
                f"Failed to initialize Reddit client: {e}"
            ) from e
    
    def _load_subreddits(self) -> Dict[str, List[str]]:
        """サブレディット設定を読み込み"""
        config_path = self.get_config_path("subreddits.toml")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
                self.logger.info(
                    f"Loaded {sum(len(v) for v in config.values())} subreddits"
                )
                return config
        except Exception as e:
            raise DataException(f"Failed to load subreddits: {e}") from e
    
    @log_execution_time
    @handle_errors(retries=3)
    async def collect(self) -> None:
        """Reddit投稿を収集・分析"""
        self.logger.info("Starting Reddit collection")
        
        # カテゴリごとに並行処理
        tasks = []
        for category, subreddit_list in self.subreddits.items():
            for subreddit in subreddit_list:
                tasks.append(self._collect_subreddit(subreddit, category))
        
        results = await gather_with_errors(
            *tasks,
            task_names=[f"{cat}/{sub}" for cat, subs in self.subreddits.items() for sub in subs]
        )
        
        # 結果を統合
        all_posts = []
        failed_subreddits = []
        
        for result in results:
            if result.success and result.result:
                all_posts.extend(result.result)
            else:
                failed_subreddits.append(result.name)
                self.logger.error(f"Failed to collect {result.name}: {result.error}")
        
        if not all_posts:
            raise ServiceException("No posts collected from Reddit")
        
        # 投稿を分析
        analyzed_posts = await self._analyze_posts(all_posts)
        
        # レポート生成
        report = await self._generate_report(analyzed_posts, failed_subreddits)
        filename = f"reddit_{datetime.now():%Y-%m-%d}.md"
        await self.save_markdown(report, filename)
        
        # 統計情報を保存
        stats = self._generate_statistics(analyzed_posts)
        await self.save_json(stats, f"stats_{datetime.now():%Y-%m-%d}.json")
        
        self.logger.info(
            f"Collected {len(analyzed_posts)} posts from "
            f"{len(set(p['subreddit'] for p in analyzed_posts))} subreddits"
        )
    
    async def _collect_subreddit(
        self,
        subreddit_name: str,
        category: str
    ) -> List[Dict[str, Any]]:
        """特定のサブレディットから投稿を収集"""
        try:
            # Reddit APIは同期的なので、別スレッドで実行
            posts = await run_sync_in_thread(
                self._fetch_subreddit_posts,
                subreddit_name,
                limit=20
            )
            
            # カテゴリ情報を追加
            for post in posts:
                post["category"] = category
            
            self.logger.debug(
                f"Collected {len(posts)} posts from r/{subreddit_name}"
            )
            
            return posts
            
        except ResponseException as e:
            if e.response.status_code == 404:
                raise APIException(
                    f"Subreddit r/{subreddit_name} not found",
                    status_code=404
                ) from e
            else:
                raise APIException(
                    f"Reddit API error for r/{subreddit_name}: {e}",
                    status_code=e.response.status_code
                ) from e
        except Exception as e:
            raise ServiceException(
                f"Failed to collect from r/{subreddit_name}: {e}"
            ) from e
    
    def _fetch_subreddit_posts(self, subreddit_name: str, limit: int) -> List[Dict[str, Any]]:
        """サブレディットの投稿を取得（同期）"""
        subreddit = self.reddit_client.subreddit(subreddit_name)
        posts = []
        
        for submission in subreddit.hot(limit=limit):
            post_data = {
                "id": submission.id,
                "title": submission.title,
                "author": str(submission.author) if submission.author else "[deleted]",
                "subreddit": subreddit_name,
                "score": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "url": f"https://reddit.com{submission.permalink}",
                "is_self": submission.is_self,
                "selftext": submission.selftext[:1000] if submission.is_self else "",
                "link_url": submission.url if not submission.is_self else None,
                "flair": submission.link_flair_text
            }
            posts.append(post_data)
        
        return posts
    
    async def _analyze_posts(
        self,
        posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """投稿を分析"""
        # 分析が必要な投稿をフィルタ
        posts_to_analyze = [
            p for p in posts
            if p["score"] > 100 or p["num_comments"] > 50
        ]
        
        self.logger.info(f"Analyzing {len(posts_to_analyze)} high-quality posts")
        
        async def analyze_single_post(post: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # タイトルと内容から要約を生成
                content = f"Title: {post['title']}\n"
                if post.get("selftext"):
                    content += f"Content: {post['selftext']}"
                
                analysis = await self._generate_post_analysis(content, post["subreddit"])
                post["ai_analysis"] = analysis
                
                # センチメント分析
                post["sentiment"] = await self._analyze_sentiment(content)
                
                # 重要度スコア
                post["importance_score"] = self._calculate_importance(post)
                
                return post
                
            except Exception as e:
                self.logger.warning(f"Failed to analyze post {post['id']}: {e}")
                post["ai_analysis"] = ""
                return post
        
        # 並行分析（レート制限を考慮）
        tasks = [analyze_single_post(post) for post in posts_to_analyze]
        analyzed = await run_with_semaphore(tasks, max_concurrent=3)
        
        # 分析されなかった投稿も含める
        analyzed_ids = {p["id"] for p in analyzed}
        for post in posts:
            if post["id"] not in analyzed_ids:
                post["ai_analysis"] = ""
                post["importance_score"] = self._calculate_importance(post)
        
        return posts
    
    async def _generate_post_analysis(self, content: str, subreddit: str) -> str:
        """投稿の分析を生成"""
        prompt = f"""
        以下のReddit投稿（r/{subreddit}）を分析し、
        日本語で要点を50文字以内でまとめてください：
        
        {content}
        
        技術的な内容の場合は、その技術的価値も含めてください。
        """
        
        return await self.gpt_client.generate_async(
            prompt,
            max_tokens=150,
            temperature=0.3
        )
    
    async def _analyze_sentiment(self, content: str) -> str:
        """センチメント分析"""
        prompt = f"""
        以下のテキストのセンチメントを分析し、
        「ポジティブ」「ネガティブ」「中立」のいずれかで答えてください：
        
        {content[:500]}
        """
        
        response = await self.gpt_client.generate_async(
            prompt,
            max_tokens=10,
            temperature=0
        )
        
        return response.strip()
    
    def _calculate_importance(self, post: Dict[str, Any]) -> float:
        """投稿の重要度を計算"""
        score = 0.0
        
        # スコアの重み
        score += min(post["score"] / 100, 30)
        
        # コメント数の重み
        score += min(post["num_comments"] / 50, 20)
        
        # アップvote率
        score += post.get("upvote_ratio", 0.5) * 20
        
        # 新しさ（24時間以内なら加点）
        age_hours = (datetime.now().timestamp() - post["created_utc"]) / 3600
        if age_hours < 24:
            score += (24 - age_hours) / 24 * 20
        
        # フレアがある場合
        if post.get("flair"):
            score += 10
        
        return min(score, 100.0)
    
    async def _generate_report(
        self,
        posts: List[Dict[str, Any]],
        failed_subreddits: List[str]
    ) -> str:
        """Markdownレポートを生成"""
        lines = [
            f"# Reddit トレンド分析 - {datetime.now():%Y年%m月%d日}",
            "",
            "AIが選んだ今日の注目投稿",
            ""
        ]
        
        if failed_subreddits:
            lines.extend([
                "## ⚠️ 収集に失敗したサブレディット",
                ", ".join(failed_subreddits),
                ""
            ])
        
        # カテゴリ別に整理
        by_category = {}
        for post in posts:
            cat = post.get("category", "Other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(post)
        
        for category, cat_posts in sorted(by_category.items()):
            lines.extend([
                f"## {category}",
                ""
            ])
            
            # 重要度でソート
            sorted_posts = sorted(
                cat_posts,
                key=lambda x: x.get("importance_score", 0),
                reverse=True
            )[:10]  # 各カテゴリ上位10件
            
            for post in sorted_posts:
                sentiment_emoji = {
                    "ポジティブ": "😊",
                    "ネガティブ": "😞",
                    "中立": "😐"
                }.get(post.get("sentiment", ""), "")
                
                lines.extend([
                    f"### [{post['title']}]({post['url']})",
                    f"r/{post['subreddit']} | "
                    f"👤 u/{post['author']} | "
                    f"⬆️ {post['score']:,} | "
                    f"💬 {post['num_comments']:,} | "
                    f"{sentiment_emoji}",
                    "",
                ])
                
                if post.get("ai_analysis"):
                    lines.extend([
                        "**AI分析**:",
                        post["ai_analysis"],
                        ""
                    ])
                
                if post.get("link_url") and not post["is_self"]:
                    lines.extend([
                        f"🔗 [外部リンク]({post['link_url']})",
                        ""
                    ])
                
                lines.append("---")
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_statistics(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """統計情報を生成"""
        total_score = sum(p["score"] for p in posts)
        total_comments = sum(p["num_comments"] for p in posts)
        
        sentiment_counts = {}
        for post in posts:
            sentiment = post.get("sentiment", "不明")
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        return {
            "date": datetime.now().isoformat(),
            "total_posts": len(posts),
            "subreddits": list({p["subreddit"] for p in posts}),
            "categories": list({p.get("category", "Other") for p in posts}),
            "total_score": total_score,
            "total_comments": total_comments,
            "avg_score": total_score / len(posts) if posts else 0,
            "avg_comments": total_comments / len(posts) if posts else 0,
            "sentiment_distribution": sentiment_counts,
            "top_posts": [
                {
                    "title": p["title"],
                    "url": p["url"],
                    "score": p["score"],
                    "subreddit": p["subreddit"],
                    "importance": p.get("importance_score", 0)
                }
                for p in sorted(
                    posts,
                    key=lambda x: x.get("importance_score", 0),
                    reverse=True
                )[:20]
            ]
        }
```

### 3. 共通ユーティリティの追加
**ファイル**: `nook/common/base_service.py` (追加メソッド)

```python
# BaseServiceクラスに以下のメソッドを追加

    def get_config_path(self, filename: str) -> Path:
        """サービス固有の設定ファイルパスを取得"""
        return Path(f"nook/services/{self.service_name}/{filename}")
    
    async def save_json(self, data: Any, filename: str) -> None:
        """JSONデータを保存"""
        import json
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        await self.save_data(json_str, filename)
    
    async def load_json(self, filename: str) -> Any:
        """JSONデータを読み込み"""
        import json
        content = await self.storage.load(filename)
        return json.loads(content) if content else None
    
    async def save_with_backup(self, data: Any, filename: str, keep_backups: int = 3):
        """バックアップ付きでデータを保存"""
        # 既存ファイルをバックアップ
        existing = await self.storage.exists(filename)
        if existing:
            for i in range(keep_backups - 1, 0, -1):
                old_backup = f"{filename}.{i}"
                new_backup = f"{filename}.{i + 1}"
                if await self.storage.exists(old_backup):
                    await self.storage.rename(old_backup, new_backup)
            
            await self.storage.rename(filename, f"{filename}.1")
        
        # 新しいデータを保存
        await self.save_data(data, filename)
```

### 4. 残りのサービスのリファクタリング指針

以下のサービスも同様にリファクタリングする：

1. **HackerNewsService**
   - 非同期HTTP通信への移行
   - エラーハンドリングの統一
   - AIによるコメント分析の追加

2. **TechFeedService / BusinessFeedService**
   - RSS解析の非同期化
   - 複数フィードの並行取得
   - 記事の重要度スコアリング

3. **PaperSummarizerService**
   - arXiv APIの非同期化
   - 論文の並行ダウンロード
   - 要約生成の最適化

4. **FourchanExplorer / FivechanExplorer**
   - スレッド収集の並行化
   - レート制限の実装
   - コンテンツフィルタリング

各サービスで実装すべき共通要素：
- `BaseService`の継承
- 非同期メソッド（`async def`）の使用
- 統一されたエラーハンドリング
- 構造化ログの出力
- 設定ファイルの外部化
- AIによる分析・要約機能
- 統計情報の生成

## テスト要件

各リファクタリングされたサービスに対して：

1. **ユニットテスト**を作成
2. **モックを使用**して外部依存を排除
3. **非同期処理**のテスト
4. **エラーケース**のテスト
5. **パフォーマンス**の計測

## 完了条件

1. すべてのサービスが`BaseService`を継承していること
2. 非同期処理に移行していること
3. エラーハンドリングが統一されていること
4. ログ出力が構造化されていること
5. テストが作成され、パスしていること
6. ドキュメントが更新されていること

## 注意事項

1. 既存の機能を壊さないよう段階的に移行
2. 外部APIのレート制限を考慮
3. メモリ使用量の増加に注意
4. 並行処理数を適切に制限
5. エラー時のリトライ戦略を実装

## 依存関係

- TASK-001（基底クラス）の完了
- TASK-002（エラーハンドリング）の完了
- TASK-003（非同期処理）の完了

## 期限

3日間