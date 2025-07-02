"""
5chanサービスのテストケース
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


class TestFiveChanExplorer:
    """5chanサービスのテストクラス"""
    
    @pytest.fixture
    def service(self):
        """テスト用のサービスインスタンスを作成"""
        return FiveChanExplorer()
    
    def test_build_board_url_basic(self, service):
        """基本的な板URL構築のテスト"""
        # esiteサーバーは egg.5ch.net であることが知られている
        board_id = "esite"
        expected_url = "https://egg.5ch.net/esite/"
        
        actual_url = service._build_board_url(board_id, "egg.5ch.net")
        assert actual_url == expected_url
    
    def test_build_board_url_with_different_servers(self, service):
        """異なるサーバーでの板URL構築テスト"""
        test_cases = [
            ("prog", "peace.5ch.net", "https://peace.5ch.net/prog/"),
            ("tech", "egg.5ch.net", "https://egg.5ch.net/tech/"),
            ("ai", "rio2016.5ch.net", "https://rio2016.5ch.net/ai/"),
        ]
        
        for board_id, server, expected_url in test_cases:
            actual_url = service._build_board_url(board_id, server)
            assert actual_url == expected_url
    
    @pytest.mark.asyncio
    async def test_get_board_server_from_bbsmenu(self, service):
        """bbsmenu.htmlから板のサーバー情報を取得するテスト"""
        # http_clientをモックに設定
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
        <a href="https://egg.5ch.net/esite/">ネットサービス</a>
        <a href="https://peace.5ch.net/prog/">プログラミング</a>
        </body>
        </html>
        """
        mock_client.get.return_value = mock_response
        service.http_client = mock_client
        
        # テスト実行
        server = await service._get_board_server("esite")
        assert server == "egg.5ch.net"
        
        server = await service._get_board_server("prog")  
        assert server == "peace.5ch.net"
        
        # 存在しない板の場合
        server = await service._get_board_server("nonexistent")
        assert server is None