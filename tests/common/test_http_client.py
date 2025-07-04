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
    
    @pytest.mark.asyncio
    @patch('nook.common.http_client.BaseConfig')
    async def test_get_uses_browser_headers_by_default(self, mock_config):
        """getメソッドがデフォルトでブラウザヘッダーを使用することをテスト"""
        # Arrange
        mock_config_instance = MagicMock()
        mock_config_instance.REQUEST_TIMEOUT = 30
        mock_config.return_value = mock_config_instance
        
        client = AsyncHTTPClient()
        mock_httpx_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response
        client._client = mock_httpx_client
        
        # Act
        await client.get("https://example.com")
        
        # Assert
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        headers = call_args.kwargs.get('headers', {})
        assert 'User-Agent' in headers
        assert 'Chrome' in headers['User-Agent']