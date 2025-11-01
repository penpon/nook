import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from nook.common.config import BaseConfig
from nook.common.decorators import handle_errors
from nook.common.gpt_client import GPTClient
from nook.common.logging import setup_logger
from nook.common.storage import LocalStorage


class BaseService(ABC):
    """すべてのサービスの基底クラス"""

    def __init__(self, service_name: str, config: BaseConfig | None = None):
        self.service_name = service_name
        self.config = config or BaseConfig()
        self.storage = LocalStorage(f"data/{service_name}")
        self.gpt_client = GPTClient()
        self.logger = setup_logger(service_name)
        self.request_delay = self.config.REQUEST_DELAY
        self.http_client = None  # グローバルHTTPクライアントで初期化

    @abstractmethod
    async def collect(self) -> None:
        """データ収集のメイン処理（各サービスで実装）"""
        pass

    async def save_data(self, data: Any, filename: str) -> Path:
        """共通のデータ保存処理"""
        try:
            file_path = await self.storage.save(data, filename)
            self.logger.info(f"Data saved successfully: {filename}")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save data {filename}: {e}")
            raise

    async def save_markdown(self, content: str, filename: str) -> Path:
        """Markdownファイルの保存"""
        file_path = await self.save_data(content, filename)
        self.logger.info(f"📝 Markdown saved: {file_path}")
        return file_path

    @handle_errors(retries=3)
    async def fetch_with_retry(self, url: str) -> str:
        """リトライ機能付きのHTTP取得"""
        # AsyncHTTPClientを使用（後で実装）
        pass

    async def rate_limit(self) -> None:
        """レート制限のための待機"""
        await asyncio.sleep(self.request_delay)

    def get_config_path(self, filename: str) -> Path:
        """サービス固有の設定ファイルパスを取得"""
        return Path(f"nook/services/{self.service_name}/{filename}")

    async def save_json(self, data: Any, filename: str) -> Path:
        """JSONデータを保存"""
        file_path = await self.storage.save(data, filename)
        self.logger.info(f"💾 JSON saved: {file_path}")
        return file_path

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

    async def setup_http_client(self):
        """グローバルHTTPクライアントをセットアップ"""
        if self.http_client is None:
            from nook.common.http_client import get_http_client

            self.http_client = await get_http_client()
            self.logger.debug("HTTP client setup completed")

    async def cleanup(self):
        """クリーンアップ処理（オーバーライド可能）"""
        # グローバルクライアントの場合はクローズ不要
        # サブクラスで追加のクリーンアップが必要な場合はオーバーライドする
        pass

    async def initialize(self):
        """非同期初期化処理（オーバーライド可能）"""
        # サービスの非同期初期化をサポート
        # 必要に応じてHTTPクライアントのセットアップも含む
        await self.setup_http_client()
