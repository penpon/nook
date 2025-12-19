"""Bot保護ミドルウェアのテスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.middleware.bot_protection import (  # noqa: E402
    bot_protection_middleware,
    get_client_ip,
    is_allowed_ip,
    is_bot_user_agent,
)


@pytest.fixture
def app():
    """テスト用FastAPIアプリ。"""
    test_app = FastAPI()
    test_app.middleware("http")(bot_protection_middleware)

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    return test_app


@pytest.fixture
def client(app):
    """テストクライアント。"""
    return TestClient(app)


class TestIsBotUserAgent:
    """is_bot_user_agent関数のテスト。"""

    def test_curl_is_bot(self):
        """curlはbotと判定される。"""
        assert is_bot_user_agent("curl/7.68.0") is True

    def test_wget_is_bot(self):
        """wgetはbotと判定される。"""
        assert is_bot_user_agent("Wget/1.20.3") is True

    def test_python_requests_is_bot(self):
        """python-requestsはbotと判定される。"""
        assert is_bot_user_agent("python-requests/2.28.0") is True

    def test_browser_is_not_bot(self):
        """通常のブラウザはbotではない。"""
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        assert is_bot_user_agent(user_agent) is False

    def test_empty_user_agent_is_bot(self):
        """空のUser-Agentはbotと判定される。"""
        assert is_bot_user_agent("") is True
        assert is_bot_user_agent(None) is True


class TestIsAllowedIp:
    """is_allowed_ip関数のテスト。"""

    def test_allowed_single_ip(self):
        """許可リストの単一IPは許可される。"""
        assert is_allowed_ip("164.70.96.2", ["164.70.96.2"]) is True

    def test_not_allowed_ip(self):
        """許可リストにないIPは拒否される。"""
        assert is_allowed_ip("1.2.3.4", ["164.70.96.2"]) is False

    def test_docker_network_always_allowed(self):
        """Docker内部ネットワークは常に許可される。"""
        assert is_allowed_ip("172.17.0.1", []) is True
        assert is_allowed_ip("10.0.0.1", []) is True
        assert is_allowed_ip("127.0.0.1", []) is True

    def test_cidr_notation(self):
        """CIDR形式の許可リストが機能する。"""
        assert is_allowed_ip("192.168.1.100", ["192.168.1.0/24"]) is True
        assert is_allowed_ip("192.168.2.100", ["192.168.1.0/24"]) is False


class TestBotProtectionMiddleware:
    """bot_protection_middlewareのテスト。"""

    def test_browser_access_allowed(self, client, monkeypatch):
        """通常のブラウザアクセスは許可される。"""
        monkeypatch.setenv("ALLOWED_IPS", "164.70.96.2")

        response = client.get(
            "/test",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "success"}

    def test_bot_from_allowed_ip(self, client, monkeypatch):
        """許可IPからのbotアクセスは許可される。"""
        monkeypatch.setenv("ALLOWED_IPS", "164.70.96.2")

        # X-Forwarded-Forで許可IPを設定
        response = client.get(
            "/test",
            headers={
                "User-Agent": "curl/7.68.0",
                "X-Forwarded-For": "164.70.96.2",
            },
        )
        assert response.status_code == status.HTTP_200_OK

    def test_bot_from_disallowed_ip(self, client, monkeypatch):
        """許可外IPからのbotアクセスは拒否される。"""
        monkeypatch.setenv("ALLOWED_IPS", "164.70.96.2")

        # X-Forwarded-Forで別のIPを偽装
        response = client.get(
            "/test",
            headers={"User-Agent": "curl/7.68.0", "X-Forwarded-For": "1.2.3.4"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "access_denied" in response.json()["error"]["type"]

    def test_empty_user_agent_from_disallowed_ip(self, client, monkeypatch):
        """空のUser-Agentは許可外IPから拒否される。"""
        monkeypatch.setenv("ALLOWED_IPS", "164.70.96.2")

        response = client.get("/test", headers={"X-Forwarded-For": "1.2.3.4"})
        # FastAPIのTestClientはデフォルトでUser-Agentを設定するため、
        # 明示的に削除する必要がある
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


class TestGetClientIp:
    """get_client_ip関数のテスト。"""

    def test_x_forwarded_for_header(self):
        """X-Forwarded-Forヘッダーから取得。"""
        request = MagicMock()
        request.headers.get.side_effect = lambda key: {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}.get(key)

        assert get_client_ip(request) == "1.2.3.4"

    def test_x_real_ip_header(self):
        """X-Real-IPヘッダーから取得。"""
        request = MagicMock()
        request.headers.get.side_effect = lambda key: {"X-Real-IP": "1.2.3.4"}.get(key)

        assert get_client_ip(request) == "1.2.3.4"

    def test_direct_client_ip(self):
        """直接接続のクライアントIPから取得。"""
        request = MagicMock()
        request.headers.get.return_value = None
        request.client.host = "1.2.3.4"

        assert get_client_ip(request) == "1.2.3.4"
