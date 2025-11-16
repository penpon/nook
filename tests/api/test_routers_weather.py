"""nook/api/routers/weather.py のテスト"""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestWeatherRouter:
    """天気APIルーターのテスト"""

    def test_weather_endpoint_without_api_key(self, client, monkeypatch):
        """APIキーなし（デモモード）の天気データ取得"""
        # APIキーを削除
        monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

        response = client.get("/api/weather")

        assert response.status_code == 200
        data = response.json()
        assert "temperature" in data
        assert "icon" in data
        assert data["temperature"] == 20.5
        assert data["icon"] == "01d"

    @pytest.mark.unit
    def test_weather_endpoint_with_api_key_success(self, client, monkeypatch):
        """APIキーありで正常に天気データを取得"""
        # APIキーを設定
        monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-api-key")

        # OpenWeatherMap APIのモックレスポンス
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 15.5},
            "weather": [{"icon": "10d"}],
        }

        with patch("requests.get", return_value=mock_response):
            response = client.get("/api/weather")

        assert response.status_code == 200
        data = response.json()
        assert data["temperature"] == 15.5
        assert data["icon"] == "10d"

    @pytest.mark.unit
    def test_weather_endpoint_api_error(self, client, monkeypatch):
        """OpenWeatherMap APIエラー時の処理"""
        monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-api-key")

        # APIエラーをモック
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("requests.get", return_value=mock_response):
            response = client.get("/api/weather")

        assert response.status_code == 500

    @pytest.mark.unit
    def test_weather_endpoint_invalid_response(self, client, monkeypatch):
        """無効なレスポンス形式の処理"""
        monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-api-key")

        # 無効なレスポンスデータ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "data"}

        with patch("requests.get", return_value=mock_response):
            response = client.get("/api/weather")

        assert response.status_code == 500

    @pytest.mark.unit
    def test_weather_response_format(self, client, monkeypatch):
        """レスポンス形式の確認（デモモード）"""
        monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

        response = client.get("/api/weather")

        assert response.status_code == 200
        data = response.json()

        # 必須フィールドの確認
        assert "temperature" in data
        assert "icon" in data

        # 型の確認
        assert isinstance(data["temperature"], (int, float))
        assert isinstance(data["icon"], str)
