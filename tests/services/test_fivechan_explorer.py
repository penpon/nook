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