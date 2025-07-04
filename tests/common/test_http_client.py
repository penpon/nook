import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from nook.common.http_client import AsyncHTTPClient


class TestAsyncHTTPClient:
    """AsyncHTTPClientのテストクラス"""
    
    @patch('nook.common.http_client.BaseConfig')
    def test_get_browser_headers_returns_chrome_headers(self, mock_config):
        """get_browser_headers()がChromeブラウザヘッダーを返すことをテスト"""
        # Arrange
        mock_config_instance = MagicMock()
        mock_config_instance.REQUEST_TIMEOUT = 30
        mock_config.return_value = mock_config_instance
        
        client = AsyncHTTPClient()
        
        # Act
        headers = client.get_browser_headers()
        
        # Assert
        assert isinstance(headers, dict)
        assert 'User-Agent' in headers
        assert 'Chrome' in headers['User-Agent']
        assert 'Accept' in headers
        assert 'Accept-Language' in headers
        assert 'Accept-Encoding' in headers
        assert 'sec-ch-ua' in headers