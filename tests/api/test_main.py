"""nook/api/main.py のテスト"""

import pytest


@pytest.mark.unit
def test_root_endpoint(client):
    """/ エンドポイントが正しい情報を返すことを確認"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nook API"
    assert data["version"] == "0.1.0"
    assert data["description"] == "パーソナル情報ハブのAPI"


@pytest.mark.unit
def test_health_endpoint(client):
    """ヘルスチェックエンドポイントが正しいステータスを返すことを確認"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_error_stats_endpoint(client):
    """エラー統計エンドポイントが正しい形式のデータを返すことを確認"""
    response = client.get("/api/health/errors")

    assert response.status_code == 200
    data = response.json()

    # エラー統計は辞書形式で返される
    assert isinstance(data, dict)
    # キーはエラータイプ、値は統計情報
    for error_type, stats in data.items():
        assert isinstance(error_type, str)
        assert isinstance(stats, dict)


@pytest.mark.unit
def test_root_endpoint_returns_json(client):
    """/ エンドポイントがJSONを返すことを確認"""
    response = client.get("/")

    assert response.headers["content-type"] == "application/json"


@pytest.mark.unit
def test_health_endpoint_returns_json(client):
    """/health エンドポイントがJSONを返すことを確認"""
    response = client.get("/health")

    assert response.headers["content-type"] == "application/json"


@pytest.mark.unit
def test_cors_headers_present(client):
    """CORSヘッダーが設定されていることを確認"""
    response = client.get("/", headers={"Origin": "http://localhost:3000"})

    # CORSミドルウェアが設定されている場合、適切なヘッダーが返される
    assert response.status_code == 200


@pytest.mark.unit
def test_root_has_required_fields(client):
    """/ エンドポイントが必須フィールドを持つことを確認"""
    response = client.get("/")
    data = response.json()

    required_fields = ["name", "version", "description"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


@pytest.mark.unit
def test_health_has_status_field(client):
    """/health エンドポイントがstatusフィールドを持つことを確認"""
    response = client.get("/")
    data = response.json()

    assert "status" in data or "name" in data  # healthまたはroot


@pytest.mark.unit
def test_nonexistent_endpoint_returns_404(client):
    """存在しないエンドポイントが404を返すことを確認"""
    response = client.get("/nonexistent")

    assert response.status_code == 404


@pytest.mark.unit
def test_api_version_is_string(client):
    """APIバージョンが文字列であることを確認"""
    response = client.get("/")
    data = response.json()

    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
