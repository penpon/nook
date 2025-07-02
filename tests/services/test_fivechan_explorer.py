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
    
    @pytest.mark.asyncio
    async def test_retrieve_ai_threads_uses_correct_url_structure(self, service):
        """_retrieve_ai_threadsが正しいURL構造を使用するテスト"""
        # http_clientをモックに設定
        mock_client = AsyncMock()
        
        # bbsmenu.htmlのレスポンス（サーバー情報取得用）
        bbsmenu_response = MagicMock()
        bbsmenu_response.status_code = 200
        bbsmenu_response.text = '<a href="https://egg.5ch.net/esite/">ネットサービス</a>'
        
        # 板ページのレスポンス（スレッド一覧取得用）
        board_response = MagicMock()
        board_response.status_code = 200
        board_response.text = '''
        <html>
        <body>
        <p><a href="/test/read.cgi/esite/1234567890/">AI関連のスレッド</a> (123)</p>
        </body>
        </html>
        '''
        
        # getメソッドの動作をURL別に設定
        def mock_get_side_effect(url, **kwargs):
            if "bbsmenu.html" in url:
                return bbsmenu_response
            elif "egg.5ch.net/esite/" in url:
                return board_response
            else:
                raise Exception(f"Unexpected URL: {url}")
        
        mock_client.get.side_effect = mock_get_side_effect
        service.http_client = mock_client
        
        # テスト実行
        threads = await service._retrieve_ai_threads("esite", 10)
        
        # 呼び出されたURLを検証
        calls = mock_client.get.call_args_list
        assert len(calls) == 2
        
        # bbsmenu.html へのアクセス
        assert "menu.5ch.net/bbsmenu.html" in calls[0][0][0]
        
        # 正しい板URL（egg.5ch.net/esite/）へのアクセス
        assert "egg.5ch.net/esite/" in calls[1][0][0]
        
        # 間違ったURL（menu.5ch.net/test/read.cgi/esite/）は使用されていない
        for call in calls:
            assert "menu.5ch.net/test/read.cgi" not in call[0][0]