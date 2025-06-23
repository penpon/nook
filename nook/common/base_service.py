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