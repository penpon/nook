# TASK-006: ドメイン構造への再編成

## 割り当て: backend

## 目的
現在のフラットなディレクトリ構造をドメイン駆動設計（DDD）に基づいた構造に再編成し、コードの保守性と拡張性を向上させる。

## 背景
現在のプロジェクト構造は機能別に分かれているが、ドメインの境界が不明確で、依存関係が複雑になりやすい。DDDアプローチにより、ビジネスロジックを明確に分離する。

## 実装内容

### 1. 新しいディレクトリ構造

```
nook/
├── src/                              # ソースコードルート
│   ├── core/                        # コアドメイン（共通基盤）
│   │   ├── __init__.py
│   │   ├── base/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # BaseService
│   │   │   ├── repository.py       # BaseRepository
│   │   │   └── entity.py           # BaseEntity
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py         # 設定管理
│   │   │   └── constants.py        # 定数定義
│   │   ├── exceptions/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # 基底例外
│   │   │   ├── domain.py          # ドメイン例外
│   │   │   └── application.py     # アプリケーション例外
│   │   ├── interfaces/
│   │   │   ├── __init__.py
│   │   │   ├── http_client.py     # HTTPクライアントインターフェース
│   │   │   ├── storage.py         # ストレージインターフェース
│   │   │   └── ai_client.py       # AIクライアントインターフェース
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── async_utils.py     # 非同期ユーティリティ
│   │       ├── decorators.py      # デコレータ
│   │       └── logging.py         # ロギング
│   │
│   ├── domain/                      # ドメイン層
│   │   ├── __init__.py
│   │   ├── content/                # コンテンツドメイン
│   │   │   ├── __init__.py
│   │   │   ├── entities/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── article.py     # 記事エンティティ
│   │   │   │   ├── repository.py  # リポジトリエンティティ
│   │   │   │   └── post.py        # 投稿エンティティ
│   │   │   ├── value_objects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── score.py       # スコア値オブジェクト
│   │   │   │   ├── sentiment.py   # センチメント値オブジェクト
│   │   │   │   └── language.py    # プログラミング言語
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   └── content.py     # コンテンツリポジトリインターフェース
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── analyzer.py    # コンテンツ分析サービス
│   │   │
│   │   └── collection/             # 収集ドメイン
│   │       ├── __init__.py
│   │       ├── entities/
│   │       ├── value_objects/
│   │       └── services/
│   │
│   ├── application/                # アプリケーション層
│   │   ├── __init__.py
│   │   ├── collectors/            # データ収集サービス
│   │   │   ├── __init__.py
│   │   │   ├── github/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py    # GitHubサービス
│   │   │   │   ├── dto.py        # データ転送オブジェクト
│   │   │   │   └── mapper.py     # エンティティマッパー
│   │   │   ├── reddit/
│   │   │   ├── hackernews/
│   │   │   ├── feeds/            # RSS系
│   │   │   └── forums/           # 掲示板系
│   │   │
│   │   ├── use_cases/             # ユースケース
│   │   │   ├── __init__.py
│   │   │   ├── collect_trending.py
│   │   │   ├── analyze_content.py
│   │   │   └── generate_report.py
│   │   │
│   │   └── services/              # アプリケーションサービス
│   │       ├── __init__.py
│   │       ├── orchestrator.py   # サービスオーケストレーター
│   │       └── scheduler.py      # スケジューラー
│   │
│   ├── infrastructure/            # インフラストラクチャ層
│   │   ├── __init__.py
│   │   ├── clients/              # 外部サービスクライアント
│   │   │   ├── __init__.py
│   │   │   ├── http/
│   │   │   │   ├── __init__.py
│   │   │   │   └── async_client.py
│   │   │   ├── openai/
│   │   │   │   ├── __init__.py
│   │   │   │   └── gpt_client.py
│   │   │   └── reddit/
│   │   │       ├── __init__.py
│   │   │       └── praw_client.py
│   │   │
│   │   ├── persistence/          # 永続化
│   │   │   ├── __init__.py
│   │   │   ├── file/
│   │   │   │   ├── __init__.py
│   │   │   │   └── local_storage.py
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── content.py   # コンテンツリポジトリ実装
│   │   │
│   │   └── config/              # 設定ファイル
│   │       ├── __init__.py
│   │       └── loaders/
│   │           ├── __init__.py
│   │           ├── toml_loader.py
│   │           └── env_loader.py
│   │
│   └── presentation/             # プレゼンテーション層
│       ├── __init__.py
│       ├── api/                 # REST API
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPIアプリケーション
│       │   ├── dependencies/   # 依存性注入
│       │   ├── middleware/     # ミドルウェア
│       │   └── routes/         # ルート定義
│       │       ├── __init__.py
│       │       ├── content.py
│       │       ├── chat.py
│       │       └── health.py
│       │
│       └── cli/                # CLIインターフェース
│           ├── __init__.py
│           └── commands/
│               ├── __init__.py
│               ├── collect.py
│               └── analyze.py
│
├── config/                     # 設定ファイル（TOML, YAML等）
│   ├── services/
│   │   ├── github.toml
│   │   ├── reddit.toml
│   │   └── feeds.toml
│   └── application.toml
│
├── data/                       # データ保存ディレクトリ
├── logs/                       # ログディレクトリ
├── tests/                      # テスト
└── scripts/                    # ユーティリティスクリプト
```

### 2. ドメインエンティティの定義

**ファイル**: `src/domain/content/entities/article.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from src.domain.content.value_objects import Score, Sentiment, Language


@dataclass
class Article:
    """記事エンティティ"""
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    url: str = ""
    author: Optional[str] = None
    source: str = ""  # GitHub, Reddit, HackerNews等
    source_id: str = ""  # 元サービスでのID
    content: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime = field(default_factory=datetime.utcnow)
    
    # 値オブジェクト
    score: Optional[Score] = None
    sentiment: Optional[Sentiment] = None
    language: Optional[Language] = None
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.id:
            self.id = uuid4()
    
    def update_summary(self, summary: str) -> None:
        """要約を更新"""
        self.summary = summary
        self.metadata["summary_updated_at"] = datetime.utcnow().isoformat()
    
    def add_tag(self, tag: str) -> None:
        """タグを追加"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def calculate_importance(self) -> float:
        """重要度を計算"""
        base_score = self.score.value if self.score else 0
        
        # センチメントによる調整
        if self.sentiment and self.sentiment.is_positive():
            base_score *= 1.1
        
        # 新しさによる調整
        if self.published_at:
            age_hours = (datetime.utcnow() - self.published_at).total_seconds() / 3600
            if age_hours < 24:
                base_score *= 1.2
            elif age_hours > 168:  # 1週間以上
                base_score *= 0.8
        
        return min(base_score, 100.0)
```

**ファイル**: `src/domain/content/value_objects/score.py`

```python
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Score:
    """スコア値オブジェクト"""
    value: float
    max_value: float = 100.0
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Score cannot be negative")
        if self.value > self.max_value:
            raise ValueError(f"Score cannot exceed {self.max_value}")
    
    @classmethod
    def from_reddit(cls, upvotes: int, downvotes: int = 0) -> "Score":
        """Redditのvoteからスコアを作成"""
        total = upvotes - downvotes
        # 対数スケールで正規化
        import math
        if total > 0:
            normalized = math.log10(total + 1) * 10
        else:
            normalized = 0
        return cls(value=min(normalized, 100.0))
    
    @classmethod
    def from_github(cls, stars: int) -> "Score":
        """GitHubのスターからスコアを作成"""
        import math
        if stars > 0:
            normalized = math.log10(stars + 1) * 15
        else:
            normalized = 0
        return cls(value=min(normalized, 100.0))
    
    def __add__(self, other: Union["Score", float]) -> "Score":
        if isinstance(other, Score):
            return Score(min(self.value + other.value, self.max_value))
        return Score(min(self.value + other, self.max_value))
    
    def __str__(self) -> str:
        return f"{self.value:.1f}/{self.max_value}"
```

### 3. リポジトリインターフェース

**ファイル**: `src/domain/content/repositories/content.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from src.domain.content.entities import Article


class ContentRepository(ABC):
    """コンテンツリポジトリのインターフェース"""
    
    @abstractmethod
    async def save(self, article: Article) -> None:
        """記事を保存"""
        pass
    
    @abstractmethod
    async def save_many(self, articles: List[Article]) -> None:
        """複数の記事を保存"""
        pass
    
    @abstractmethod
    async def find_by_id(self, article_id: UUID) -> Optional[Article]:
        """IDで記事を検索"""
        pass
    
    @abstractmethod
    async def find_by_source(
        self,
        source: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Article]:
        """ソースで記事を検索"""
        pass
    
    @abstractmethod
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        sources: Optional[List[str]] = None
    ) -> List[Article]:
        """日付範囲で記事を検索"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Article]:
        """記事を検索"""
        pass
    
    @abstractmethod
    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """統計情報を取得"""
        pass
```

### 4. アプリケーションサービス

**ファイル**: `src/application/collectors/github/service.py`

```python
from typing import List, Dict, Any
from datetime import datetime

from src.core.base import BaseService
from src.core.interfaces import HTTPClientInterface
from src.domain.content.entities import Article
from src.domain.content.value_objects import Score, Language
from src.domain.content.repositories import ContentRepository
from src.application.collectors.github.dto import GitHubRepositoryDTO
from src.application.collectors.github.mapper import GitHubMapper


class GitHubCollectorService(BaseService):
    """GitHub収集サービス（アプリケーション層）"""
    
    def __init__(
        self,
        http_client: HTTPClientInterface,
        content_repository: ContentRepository,
        config: Dict[str, Any]
    ):
        super().__init__("github_collector")
        self.http_client = http_client
        self.content_repository = content_repository
        self.config = config
        self.mapper = GitHubMapper()
    
    async def collect_trending(self) -> List[Article]:
        """トレンドリポジトリを収集"""
        self.logger.info("Collecting GitHub trending repositories")
        
        articles = []
        
        for language in self.config["languages"]:
            try:
                repos = await self._fetch_repositories(language)
                
                # DTOからエンティティに変換
                for repo_dto in repos:
                    article = self.mapper.to_entity(repo_dto)
                    
                    # AIによる要約を追加
                    if self.config.get("enable_ai_summary", True):
                        summary = await self._generate_summary(article)
                        article.update_summary(summary)
                    
                    articles.append(article)
                    
            except Exception as e:
                self.logger.error(f"Failed to collect {language}: {e}")
        
        # リポジトリに保存
        if articles:
            await self.content_repository.save_many(articles)
            self.logger.info(f"Saved {len(articles)} articles")
        
        return articles
    
    async def _fetch_repositories(self, language: str) -> List[GitHubRepositoryDTO]:
        """GitHubAPIからリポジトリを取得"""
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"language:{language} stars:>100",
            "sort": "stars",
            "order": "desc",
            "per_page": self.config.get("per_language_limit", 10)
        }
        
        response = await self.http_client.get(url, params=params)
        data = response.json()
        
        return [
            GitHubRepositoryDTO.from_api_response(item)
            for item in data.get("items", [])
        ]
    
    async def _generate_summary(self, article: Article) -> str:
        """記事の要約を生成"""
        # 実装は省略（AIクライアントを使用）
        return f"Summary of {article.title}"
```

### 5. 依存性注入の設定

**ファイル**: `src/presentation/api/dependencies/__init__.py`

```python
from typing import AsyncGenerator

from fastapi import Depends

from src.core.interfaces import HTTPClientInterface, StorageInterface
from src.infrastructure.clients.http import AsyncHTTPClient
from src.infrastructure.persistence.file import LocalFileStorage
from src.infrastructure.persistence.repositories import FileContentRepository
from src.domain.content.repositories import ContentRepository
from src.application.collectors.github import GitHubCollectorService


# インフラストラクチャの依存性
async def get_http_client() -> AsyncGenerator[HTTPClientInterface, None]:
    """HTTPクライアントを取得"""
    client = AsyncHTTPClient()
    await client.start()
    try:
        yield client
    finally:
        await client.close()


def get_storage() -> StorageInterface:
    """ストレージを取得"""
    return LocalFileStorage(base_path="data")


def get_content_repository(
    storage: StorageInterface = Depends(get_storage)
) -> ContentRepository:
    """コンテンツリポジトリを取得"""
    return FileContentRepository(storage)


# アプリケーションサービスの依存性
def get_github_collector(
    http_client: HTTPClientInterface = Depends(get_http_client),
    repository: ContentRepository = Depends(get_content_repository)
) -> GitHubCollectorService:
    """GitHub収集サービスを取得"""
    config = {
        "languages": ["python", "javascript", "go"],
        "per_language_limit": 10,
        "enable_ai_summary": True
    }
    return GitHubCollectorService(http_client, repository, config)
```

### 6. APIルートの更新

**ファイル**: `src/presentation/api/routes/content.py`

```python
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime, date

from src.presentation.api.dependencies import get_github_collector
from src.application.collectors.github import GitHubCollectorService
from src.presentation.api.schemas import ArticleResponse, CollectionStatus


router = APIRouter(prefix="/api/v1/content", tags=["content"])


@router.post("/collect/github", response_model=CollectionStatus)
async def collect_github(
    service: GitHubCollectorService = Depends(get_github_collector)
) -> CollectionStatus:
    """GitHubトレンドを収集"""
    try:
        articles = await service.collect_trending()
        
        return CollectionStatus(
            source="github",
            status="success",
            collected_count=len(articles),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        return CollectionStatus(
            source="github",
            status="failed",
            collected_count=0,
            error=str(e),
            timestamp=datetime.utcnow()
        )


@router.get("/articles", response_model=List[ArticleResponse])
async def get_articles(
    source: Optional[str] = Query(None, description="記事のソース"),
    date: Optional[date] = Query(None, description="日付"),
    limit: int = Query(100, ge=1, le=1000)
) -> List[ArticleResponse]:
    """記事を取得"""
    # 実装は省略
    return []
```

### 7. マイグレーションスクリプト

**ファイル**: `scripts/migrate_structure.py`

```python
#!/usr/bin/env python3
"""
既存のコードを新しいドメイン構造に移行するスクリプト
"""
import os
import shutil
from pathlib import Path
import ast
import re


class StructureMigrator:
    """構造移行ツール"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.old_root = project_root / "nook"
        self.new_root = project_root / "src"
        
        # マッピング定義
        self.mapping = {
            # Core
            "nook/common/base_service.py": "src/core/base/service.py",
            "nook/common/storage.py": "src/infrastructure/persistence/file/local_storage.py",
            "nook/common/gpt_client.py": "src/infrastructure/clients/openai/gpt_client.py",
            "nook/common/http_client.py": "src/infrastructure/clients/http/async_client.py",
            "nook/common/logging.py": "src/core/utils/logging.py",
            "nook/common/decorators.py": "src/core/utils/decorators.py",
            "nook/common/exceptions.py": "src/core/exceptions/base.py",
            
            # Services → Application
            "nook/services/github_trending.py": "src/application/collectors/github/service.py",
            "nook/services/reddit_explorer.py": "src/application/collectors/reddit/service.py",
            "nook/services/hacker_news.py": "src/application/collectors/hackernews/service.py",
            
            # API
            "nook/api/main.py": "src/presentation/api/app.py",
            "nook/api/routers/": "src/presentation/api/routes/",
            
            # Config files
            "nook/services/*/": "config/services/",
        }
    
    def migrate(self):
        """移行を実行"""
        print("Starting domain structure migration...")
        
        # 1. 新しい構造を作成
        self._create_new_structure()
        
        # 2. ファイルを移動
        self._move_files()
        
        # 3. インポートを更新
        self._update_imports()
        
        # 4. __init__.pyを生成
        self._create_init_files()
        
        print("Migration completed!")
    
    def _create_new_structure(self):
        """新しいディレクトリ構造を作成"""
        directories = [
            "src/core/base",
            "src/core/config",
            "src/core/exceptions",
            "src/core/interfaces",
            "src/core/utils",
            
            "src/domain/content/entities",
            "src/domain/content/value_objects",
            "src/domain/content/repositories",
            "src/domain/content/services",
            
            "src/application/collectors/github",
            "src/application/collectors/reddit",
            "src/application/collectors/hackernews",
            "src/application/use_cases",
            "src/application/services",
            
            "src/infrastructure/clients/http",
            "src/infrastructure/clients/openai",
            "src/infrastructure/persistence/file",
            "src/infrastructure/persistence/repositories",
            
            "src/presentation/api/routes",
            "src/presentation/api/dependencies",
            "src/presentation/api/middleware",
            "src/presentation/api/schemas",
            
            "config/services",
        ]
        
        for directory in directories:
            path = self.project_root / directory
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {directory}")
    
    def _move_files(self):
        """ファイルを新しい場所に移動"""
        for old_path, new_path in self.mapping.items():
            old_full = self.project_root / old_path
            new_full = self.project_root / new_path
            
            if old_full.exists():
                if old_full.is_file():
                    new_full.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old_full, new_full)
                    print(f"Moved: {old_path} → {new_path}")
                elif old_full.is_dir():
                    # ディレクトリの場合は中身をコピー
                    for file in old_full.glob("**/*"):
                        if file.is_file():
                            relative = file.relative_to(old_full)
                            new_file = new_full / relative
                            new_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file, new_file)
    
    def _update_imports(self):
        """インポート文を更新"""
        # 実装は省略（ASTを使用してインポートを書き換え）
        pass
    
    def _create_init_files(self):
        """__init__.pyファイルを生成"""
        for root, dirs, files in os.walk(self.new_root):
            if "__pycache__" in root:
                continue
            
            init_file = Path(root) / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"Created: {init_file.relative_to(self.project_root)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        project_root = Path.cwd()
    
    migrator = StructureMigrator(project_root)
    
    # 確認
    response = input("This will restructure your project. Continue? (y/n): ")
    if response.lower() == 'y':
        migrator.migrate()
    else:
        print("Migration cancelled.")
```

## テスト要件

1. **ディレクトリ構造のテスト**
   - すべての必要なディレクトリが存在すること
   - __init__.pyが適切に配置されていること

2. **インポートのテスト**
   - すべてのモジュールが正しくインポートできること
   - 循環参照が発生していないこと

3. **機能テスト**
   - 既存の機能が新しい構造でも動作すること
   - APIエンドポイントが正常に応答すること

## 完了条件

1. 新しいディレクトリ構造が作成されていること
2. すべてのコードが適切な場所に配置されていること
3. インポートが更新され、エラーがないこと
4. テストがすべてパスすること
5. ドキュメントが更新されていること

## 注意事項

1. **段階的移行**: 一度にすべてを移行せず、段階的に行う
2. **バックアップ**: 移行前に必ずバックアップを取る
3. **依存関係**: 外部からのインポートに注意
4. **設定ファイル**: パスの変更に対応
5. **CI/CD**: ビルドプロセスの更新

## 依存関係

- TASK-001〜005の完了
- 特にTASK-005（サービスのリファクタリング）が重要

## 期限

2日間