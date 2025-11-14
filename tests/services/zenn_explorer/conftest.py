"""
ZennExplorer tests用の共通フィクスチャとヘルパー関数
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def zenn_service_with_mocks(mock_env_vars):
    """ZennExplorerサービスと共通モックの統合セットアップ

    深いネストを解消し、テストコードを簡潔にするための統合フィクスチャ。
    collect()メソッドのテストで頻繁に使用される全モックをセットアップ。

    Returns:
        dict: 以下のキーを含む辞書
            - service: ZennExplorerインスタンス
            - mock_parse: feedparser.parseのモック
            - mock_load: load_existing_titles_from_storageのモック
            - mock_setup_http: setup_http_clientのモック
            - mock_get_dates: _get_all_existing_datesのモック
            - mock_storage_load: storage.loadのモック
            - mock_storage_save: storage.saveのモック

    使用例:
        def test_something(zenn_service_with_mocks):
            svc = zenn_service_with_mocks["service"]
            mock_parse = zenn_service_with_mocks["mock_parse"]
            # テストロジック...
    """
    # auto_mock_loggerが既に適用されているため、手動パッチ不要
    from nook.services.zenn_explorer.zenn_explorer import ZennExplorer

    service = ZennExplorer()
    service.http_client = AsyncMock()

    # LOAD_TITLES_PATHの定義
    load_titles_path = (
        "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage"
    )

    with (
        patch("feedparser.parse") as mock_parse,
        patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ) as mock_setup_http,
        patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ) as mock_get_dates,
        patch(load_titles_path, new_callable=AsyncMock) as mock_load,
        patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ) as mock_storage_load,
        patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ) as mock_storage_save,
    ):
        yield {
            "service": service,
            "mock_parse": mock_parse,
            "mock_load": mock_load,
            "mock_setup_http": mock_setup_http,
            "mock_get_dates": mock_get_dates,
            "mock_storage_load": mock_storage_load,
            "mock_storage_save": mock_storage_save,
        }
