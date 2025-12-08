from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app  # noqa: E402
from nook.common.error_metrics import error_metrics  # noqa: E402


def test_root_endpoint_returns_api_info() -> None:
    """Test root endpoint returns API metadata as JSON."""

    # Given
    client = TestClient(app)

    # When
    resp = client.get("/")

    # Then
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "name": "Nook API",
        "version": "0.1.0",
        "description": "パーソナル情報ハブのAPI",
    }


def test_health_endpoint_returns_healthy() -> None:
    """Test /health endpoint returns healthy payload."""

    # Given
    client = TestClient(app)

    # When
    resp = client.get("/health")

    # Then
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_error_stats_endpoint_uses_error_metrics() -> None:
    """Test /api/health/errors reflects recorded metrics."""

    # Given
    client = TestClient(app)
    error_metrics.errors.clear()
    error_metrics.record_error("sample_error", {"status_code": 500, "detail": "x"})

    # When
    resp = client.get("/api/health/errors")

    # Then
    assert resp.status_code == 200
    data = resp.json()
    assert "sample_error" in data
    assert data["sample_error"]["count"] == 1
