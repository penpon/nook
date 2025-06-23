# TASK-001: 基底クラスと共通モジュール作成

## 割り当て: backend
## worktree: worktrees/TASK-001-base-class

## 目的
すべてのサービスクラスが継承する基底クラスと、共通で使用されるモジュールを作成し、コードの重複を削減する。

## 背景
現在、各サービスクラス（github_trending.py、reddit_explorer.py等）で以下の処理が重複している：
- `__init__`メソッドでのストレージとGPTクライアントの初期化
- データ保存処理
- エラーハンドリング
- ログ出力（print文）

## 実装内容

### 1. BaseServiceクラスの作成
**ファイル**: `nook/common/base_service.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import logging
from datetime import datetime
import asyncio

from nook.common.storage import LocalStorage
from nook.common.gpt_client import GPTClient
from nook.common.logging import setup_logger
from nook.common.config import BaseConfig
from nook.common.decorators import handle_errors


class BaseService(ABC):
    """すべてのサービスの基底クラス"""
    
    def __init__(self, service_name: str, config: Optional[BaseConfig] = None):
        self.service_name = service_name
        self.config = config or BaseConfig()
        self.storage = LocalStorage(service_name)
        self.gpt_client = GPTClient()
        self.logger = setup_logger(service_name)
        self.request_delay = self.config.REQUEST_DELAY
        
    @abstractmethod
    async def collect(self) -> None:
        """データ収集のメイン処理（各サービスで実装）"""
        pass
    
    async def save_data(self, data: Any, filename: str) -> None:
        """共通のデータ保存処理"""
        try:
            await self.storage.save(data, filename)
            self.logger.info(f"Data saved successfully: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save data {filename}: {e}")
            raise
    
    async def save_markdown(self, content: str, filename: str) -> None:
        """Markdownファイルの保存"""
        await self.save_data(content, filename)
    
    @handle_errors(retries=3)
    async def fetch_with_retry(self, url: str) -> str:
        """リトライ機能付きのHTTP取得"""
        # AsyncHTTPClientを使用（後で実装）
        pass
    
    async def rate_limit(self) -> None:
        """レート制限のための待機"""
        await asyncio.sleep(self.request_delay)
```

### 2. 設定管理システム
**ファイル**: `nook/common/config.py`

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from typing import Optional


class BaseConfig(BaseSettings):
    """基本設定クラス"""
    # API関連
    OPENAI_API_KEY: SecretStr
    REDDIT_CLIENT_ID: Optional[SecretStr] = None
    REDDIT_CLIENT_SECRET: Optional[SecretStr] = None
    
    # ログ関連
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # リクエスト関連
    REQUEST_TIMEOUT: int = Field(default=30, ge=1, le=300)
    REQUEST_DELAY: float = Field(default=1.0, ge=0.1, le=10.0)
    MAX_RETRIES: int = Field(default=3, ge=1, le=10)
    
    # データ保存関連
    DATA_DIR: str = Field(default="data")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class RedditConfig(BaseConfig):
    """Reddit用の設定"""
    REDDIT_USER_AGENT: str = Field(
        default="NookBot/1.0 by YourUsername"
    )
    

class ServiceConfig(BaseConfig):
    """各サービス用の設定基底クラス"""
    SERVICE_ENABLED: bool = Field(default=True)
    COLLECTION_INTERVAL: int = Field(default=3600)  # 秒単位
```

### 3. ロギングシステム
**ファイル**: `nook/common/logging.py`

```python
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Dict, Any
import os


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッタ"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        # カスタムフィールドの追加
        for key, value in record.__dict__.items():
            if key not in ["message", "levelname", "name", "module", 
                          "funcName", "lineno", "exc_info", "exc_text",
                          "stack_info", "created", "msecs", "relativeCreated",
                          "thread", "threadName", "processName", "process"]:
                log_obj[key] = value
                
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: str = "logs",
    use_json: bool = True
) -> logging.Logger:
    """ロガーのセットアップ"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 既存のハンドラーをクリア
    logger.handlers.clear()
    
    # ログディレクトリの作成
    os.makedirs(log_dir, exist_ok=True)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    if use_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（ローテーション付き）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f"{name}.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter() if use_json else logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)
    
    return logger
```

### 4. エラーハンドリングデコレータ
**ファイル**: `nook/common/decorators.py`

```python
import functools
import asyncio
import logging
from typing import Callable, Any, TypeVar, cast
from datetime import datetime

from nook.common.exceptions import ServiceException, RetryException


T = TypeVar('T')


def handle_errors(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """エラーハンドリングとリトライのデコレータ"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None
            
            for attempt in range(retries):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt} retries"
                        )
                    return result
                    
                except Exception as e:
                    last_exception = e
                    wait_time = delay * (backoff ** attempt)
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{retries}): {e}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": retries,
                            "error": str(e),
                            "wait_time": wait_time
                        }
                    )
                    
                    if attempt < retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {retries} attempts",
                            exc_info=True
                        )
                        raise RetryException(
                            f"Failed after {retries} attempts: {e}"
                        ) from e
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None
            
            for attempt in range(retries):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt} retries"
                        )
                    return result
                    
                except Exception as e:
                    last_exception = e
                    wait_time = delay * (backoff ** attempt)
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{retries}): {e}"
                    )
                    
                    if attempt < retries - 1:
                        asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {retries} attempts",
                            exc_info=True
                        )
                        raise RetryException(
                            f"Failed after {retries} attempts: {e}"
                        ) from e
            
            raise last_exception
        
        # 非同期関数か同期関数かを判定
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)
    
    return decorator


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """実行時間をログに記録するデコレータ"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Function {func.__name__} completed",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time
                }
            )
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"Function {func.__name__} failed",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    if asyncio.iscoroutinefunction(func):
        return cast(Callable[..., T], async_wrapper)
    else:
        # 同期版も同様に実装（省略）
        return func
```

### 5. カスタム例外クラス
**ファイル**: `nook/common/exceptions.py`

```python
class NookException(Exception):
    """Nookアプリケーションの基底例外クラス"""
    pass


class ServiceException(NookException):
    """サービス関連の例外"""
    pass


class APIException(ServiceException):
    """外部API関連の例外"""
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ConfigurationException(NookException):
    """設定関連の例外"""
    pass


class DataException(NookException):
    """データ処理関連の例外"""
    pass


class RetryException(ServiceException):
    """リトライ失敗の例外"""
    pass
```

## テスト要件

### ユニットテスト
**ファイル**: `tests/common/test_base_service.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from nook.common.base_service import BaseService
from nook.common.config import BaseConfig


class TestService(BaseService):
    """テスト用の具体的なサービス実装"""
    async def collect(self):
        return "test data"


@pytest.fixture
def test_service():
    with patch('nook.common.base_service.LocalStorage'), \
         patch('nook.common.base_service.GPTClient'):
        return TestService("test_service")


class TestBaseService:
    @pytest.mark.asyncio
    async def test_save_data_success(self, test_service):
        """データ保存の成功テスト"""
        test_service.storage.save = AsyncMock()
        
        await test_service.save_data({"test": "data"}, "test.json")
        
        test_service.storage.save.assert_called_once_with(
            {"test": "data"}, "test.json"
        )
    
    @pytest.mark.asyncio
    async def test_save_data_failure(self, test_service):
        """データ保存の失敗テスト"""
        test_service.storage.save = AsyncMock(side_effect=Exception("Save failed"))
        
        with pytest.raises(Exception):
            await test_service.save_data({"test": "data"}, "test.json")
    
    @pytest.mark.asyncio
    async def test_rate_limit(self, test_service):
        """レート制限のテスト"""
        import time
        start = time.time()
        
        await test_service.rate_limit()
        
        elapsed = time.time() - start
        assert elapsed >= test_service.request_delay
```

## 完了条件

1. すべてのファイルが作成され、importエラーがないこと
2. 各モジュールの基本的な動作確認
3. ユニットテストが全て成功すること
4. 既存のサービスクラスの1つ（例：github_trending.py）をBaseServiceを継承するように修正し、動作確認

## 注意事項

1. 既存のコードを壊さないよう、段階的に移行する
2. Python 3.12との互換性を保つ
3. 型ヒントを完全に記述する
4. docstringを適切に記述する
5. 非同期処理を前提とした設計にする

## 依存関係

- pydantic >= 2.0
- pydantic-settings >= 2.0
- pytest >= 7.0
- pytest-asyncio >= 0.21.0

## 期限

2日間