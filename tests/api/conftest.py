"""API tests用の共通フィクスチャ"""

import pytest
from fastapi.testclient import TestClient

from nook.api.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_storage(tmp_path, monkeypatch):
    """LocalStorageのモック（一時ディレクトリ）"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    return data_dir
