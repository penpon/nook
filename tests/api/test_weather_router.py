from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app  # noqa: E402


def _make_client() -> TestClient:
    return TestClient(app)


def test_get_weather_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful weather data retrieval."""
    client = _make_client()

    # Mock environment variable
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "dummy_key")

    # Mock requests.get
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "main": {"temp": 25.5},
        "weather": [{"icon": "10d"}],
    }

    with patch(
        "nook.api.routers.weather.requests.get", return_value=mock_response
    ) as mock_get:
        resp = client.get("/api/weather")

        assert resp.status_code == 200
        data = resp.json()
        assert data["temperature"] == 25.5
        assert data["icon"] == "10d"

        # Verify call arguments
        args, _ = mock_get.call_args
        assert "api.openweathermap.org" in args[0]
        assert "appid=dummy_key" in args[0]


def test_get_weather_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fallback to dummy data when no API key is set."""
    client = _make_client()

    # Ensure no API Key
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

    resp = client.get("/api/weather")
    assert resp.status_code == 200
    data = resp.json()
    # Expect dummy data
    assert data["temperature"] == 20.5
    assert data["icon"] == "01d"


def test_get_weather_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error handling when external API fails (non-200)."""
    client = _make_client()
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "dummy_key")

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("nook.api.routers.weather.requests.get", return_value=mock_response):
        resp = client.get("/api/weather")
        assert resp.status_code == 500
        assert "Failed to fetch weather data" in resp.json()["detail"]


def test_get_weather_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error handling when request raises exception."""
    client = _make_client()
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "dummy_key")

    import requests

    with patch(
        "nook.api.routers.weather.requests.get",
        side_effect=requests.RequestException("Connection error"),
    ):
        resp = client.get("/api/weather")
        assert resp.status_code == 500
        assert "Error fetching weather data" in resp.json()["detail"]
