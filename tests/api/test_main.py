from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app
from nook.common.error_metrics import error_metrics


def test_root_endpoint_returns_api_info():
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "name": "Nook API",
        "version": "0.1.0",
        "description": "パーソナル情報ハブのAPI",
    }


def test_health_endpoint_returns_healthy():
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_error_stats_endpoint_uses_error_metrics():
    client = TestClient(app)

    # メトリクス状態をリセット
    error_metrics.errors.clear()

    error_metrics.record_error("sample_error", {"status_code": 500, "detail": "x"})

    resp = client.get("/api/health/errors")
    assert resp.status_code == 200
    data = resp.json()
    assert "sample_error" in data
    assert data["sample_error"]["count"] == 1
