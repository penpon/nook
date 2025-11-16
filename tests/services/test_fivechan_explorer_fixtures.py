"""
5ちゃんねるエクスプローラーテスト用フィクスチャ

このファイルは tests/services/test_fivechan_explorer.py から
pytestによって自動的に読み込まれます（インポート不要）。

提供されるフィクスチャ：
- fivechan_service: FiveChanExplorerインスタンス
- mock_shift_jis_subject_data: Shift_JISエンコードのsubject.txtモックデータ
- mock_dat_data: DAT形式のモックデータ
- mock_httpx_response: httpx.Responseのモックファクトリー
- mock_cloudscraper: cloudscraperのモック
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def fivechan_service(mock_env_vars):
    """FiveChanExplorerインスタンスを提供（logger自動モック）"""
    with patch("nook.common.logging.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()
        yield service


@pytest.fixture
def mock_shift_jis_subject_data():
    """Shift_JISエンコードのsubject.txtモックデータ"""
    return "1234567890.dat<>AI・人工知能について語るスレ (100)\n9876543210.dat<>機械学習の最新動向 (50)\n".encode(
        "shift_jis"
    )


@pytest.fixture
def mock_dat_data():
    """DAT形式のモックデータ"""
    return """名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:test1234<>AIについて語りましょう
名無しさん<>sage<>2024/11/14(木) 12:01:00.00 ID:test5678<>機械学習は面白い
""".encode("shift_jis")


@pytest.fixture
def mock_httpx_response():
    """httpx.Responseのモックファクトリー"""

    def _create_response(status_code=200, content=b"", headers=None):
        response = Mock()
        response.status_code = status_code
        response.content = content
        response.headers = headers or {}
        response.text = content.decode("shift_jis", errors="ignore") if content else ""
        return response

    return _create_response


@pytest.fixture
def mock_cloudscraper():
    """cloudscraperのモック"""

    def _create_scraper(response=None):
        scraper = Mock()
        scraper.headers = {}
        if response:
            scraper.get = Mock(return_value=response)
        return scraper

    return _create_scraper
