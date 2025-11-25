"""FiveChanExplorer helper methods の単体テスト

ヘルパーメソッドのロジックを検証。
バックオフ遅延計算、User-Agent選択、URL構築、サーバー取得をテスト。
"""


from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer


def test_calculate_backoff_delay(tmp_path):
    """Given: リトライ回数
    When: _calculate_backoff_delay()を呼び出す
    Then: 指数バックオフによる遅延時間を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute & Verify
    assert service._calculate_backoff_delay(0) == 1  # 2^0
    assert service._calculate_backoff_delay(1) == 2  # 2^1
    assert service._calculate_backoff_delay(2) == 4  # 2^2
    assert service._calculate_backoff_delay(3) == 8  # 2^3
    assert service._calculate_backoff_delay(10) == 300  # 2^10 > 300, capped at 300


def test_get_random_user_agent(tmp_path):
    """Given: user_agentsリスト
    When: _get_random_user_agent()を呼び出す
    Then: user_agentsからランダムに選択した文字列を返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    user_agent = service._get_random_user_agent()

    # Verify
    assert user_agent in service.user_agents
    assert isinstance(user_agent, str)
    assert len(user_agent) > 0


def test_build_board_url(tmp_path):
    """Given: 板IDとサーバー
    When: _build_board_url()を呼び出す
    Then: 正しい板URLを構築して返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    url = service._build_board_url("ai", "krsw.5ch.net")

    # Verify
    assert url == "https://krsw.5ch.net/ai/"


def test_get_board_server_known_board(tmp_path):
    """Given: 既知の板ID
    When: _get_board_server()を呼び出す
    Then: boards.tomlから読み込んだサーバーを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    server = service._get_board_server("ai")

    # Verify
    assert server == "krsw.5ch.net"  # boards.tomlの設定値


def test_get_board_server_unknown_board(tmp_path):
    """Given: 未知の板ID
    When: _get_board_server()を呼び出す
    Then: デフォルトサーバーを返す
    """
    # Setup
    service = FiveChanExplorer(storage_dir=str(tmp_path))

    # Execute
    server = service._get_board_server("unknown_board_xyz")

    # Verify
    assert server == "mevius.5ch.net"  # デフォルト値
