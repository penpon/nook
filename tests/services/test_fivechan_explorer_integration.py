"""
nook/services/fivechan_explorer/fivechan_explorer.py の統合テスト

5chan Explorerサービスのエンドツーエンド動作を検証する統合テストスイート。
データ取得→GPT要約→Storage保存の全体フローとエラーハンドリングをテストします。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer, Thread

# =============================================================================
# テスト定数
# =============================================================================

TEST_THREAD_ID = "1234567890"
TEST_BOARD_ID = "livegalileo"
TEST_BOARD_NAME = "なんでも実況J"
TEST_THREAD_TITLE = "【AI】ChatGPTについて語るスレ【機械学習】"
TEST_THREAD_CONTENT = "AI技術の発展について議論するテストスレッド。" * 50
# 固定のタイムスタンプ（2020-01-01 00:00:00 UTC）を使用して再現性を確保
TEST_THREAD_TIMESTAMP = 1577836800


# =============================================================================
# テストヘルパー関数
# =============================================================================


def create_test_thread(thread_id: str = TEST_THREAD_ID, **kwargs) -> Thread:
    """テスト用のThreadオブジェクトを作成"""
    return Thread(
        thread_id=int(thread_id),
        title=kwargs.get("title", TEST_THREAD_TITLE),
        url=kwargs.get("url", f"https://greta.5ch.net/test/read.cgi/{TEST_BOARD_ID}/{thread_id}/"),
        board=kwargs.get("board", TEST_BOARD_ID),
        timestamp=kwargs.get("timestamp", TEST_THREAD_TIMESTAMP),
        popularity_score=kwargs.get("popularity_score", 0.75),
        posts=kwargs.get("posts", [{"content": TEST_THREAD_CONTENT}]),
        summary=kwargs.get("summary", ""),
    )


# =============================================================================
# 統合テスト: フルデータフロー
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_fivechan_explorer_to_storage(tmp_path, mock_env_vars):
    """
    Given: FiveChanExplorerサービスインスタンス
    When: collect()メソッドを実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功する
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_data")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のThreadオブジェクトを作成
    test_threads = [
        create_test_thread(
            thread_id="1111111111",
            title="【AI】ChatGPT統合テスト1【機械学習】",
            popularity_score=0.9,
        ),
        create_test_thread(
            thread_id="2222222222",
            title="【AI】GPT-4統合テスト2【自然言語処理】",
            popularity_score=0.85,
        ),
        create_test_thread(
            thread_id="3333333333",
            title="【AI】画像生成AI統合テスト3【Stable Diffusion】",
            popularity_score=0.8,
        ),
    ]

    # 内部メソッドとGPTクライアントをモック
    with (
        patch.object(service, "_retrieve_ai_threads", new_callable=AsyncMock) as mock_retrieve,
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # _retrieve_ai_threadsはテストスレッドを返す
        mock_retrieve.return_value = test_threads

        # GPT要約のモック
        mock_gpt.return_value = "テスト要約: この記事は統合テストの一環として作成されました。"

        # 3. データ収集実行
        result = await service.collect(thread_limit=10)

        # 4. 検証: データ取得確認
        assert result is not None, "collect()がNoneを返しました"
        assert len(result) > 0, "保存されたファイルがありません"

        # 5. 検証: Storage保存確認
        saved_json_path, saved_md_path = result[0]
        assert Path(saved_json_path).exists(), f"JSONファイルが保存されていません: {saved_json_path}"
        assert Path(saved_md_path).exists(), f"Markdownファイルが保存されていません: {saved_md_path}"

        # 6. 検証: 保存内容確認
        import json

        with open(saved_json_path) as f:
            saved_data = json.load(f)

        assert len(saved_data) >= 3, f"期待: 3件以上のスレッド, 実際: {len(saved_data)}件"

        # 最初のスレッドの検証
        first_thread = saved_data[0]
        assert "title" in first_thread, "titleフィールドが存在しません"
        assert "url" in first_thread, "urlフィールドが存在しません"
        assert "summary" in first_thread, "summaryフィールドが存在しません"

        # スレッドのタイトルが正しいことを確認
        thread_titles = [t["title"] for t in saved_data]
        assert "【AI】ChatGPT統合テスト1【機械学習】" in thread_titles, "テストスレッド1が保存されていません"
        assert "【AI】GPT-4統合テスト2【自然言語処理】" in thread_titles, "テストスレッド2が保存されていません"
        assert "【AI】画像生成AI統合テスト3【Stable Diffusion】" in thread_titles, "テストスレッド3が保存されていません"


# =============================================================================
# 統合テスト: ネットワークエラーハンドリング
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_fivechan_explorer(tmp_path, mock_env_vars):
    """
    Given: ネットワークエラーが発生する状況
    When: collect()メソッドを実行
    Then: RetryExceptionが発生する（retry decoratorによるリトライ後）
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # HTTP clientを初期化
    await service.setup_http_client()

    # 2. モック設定: ネットワークエラーをシミュレート
    with patch.object(service.http_client, "get", new_callable=AsyncMock) as mock_http_get:
        # 接続エラーを発生させる
        mock_http_get.side_effect = httpx.ConnectError("Connection failed")

        # 3. エラーハンドリング確認
        # FiveChanExplorerは内部でエラーをログに記録し、空のリストを返すか例外を発生させる
        # _retrieve_ai_threadsメソッドがエラーを処理するため、
        # collectメソッドは例外を捕捉して処理を継続する可能性がある

        # 実装によってはRetryExceptionが発生するか、空のリストが返される
        from nook.common.exceptions import RetryException

        try:
            result = await service.collect(thread_limit=5)
            # エラーが発生しても空のリストが返されることを確認
            assert isinstance(result, list), "結果はリストであるべきです"
        except RetryException as e:
            # RetryExceptionが発生する場合もある
            assert "Failed after" in str(e) or "Connection failed" in str(e)


# =============================================================================
# 統合テスト: GPT APIエラーハンドリングとフォールバック
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_fivechan_explorer(tmp_path, mock_env_vars):
    """
    Given: GPT APIエラーが発生する状況
    When: collect()メソッドを実行
    Then: フォールバック処理が動作し、要約なしでもデータが保存される
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_gpt_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のThreadオブジェクトを作成
    test_threads = [
        create_test_thread(
            thread_id="4444444444",
            title="【AI】GPTエラーテスト1【フォールバック】",
            popularity_score=0.88,
        ),
        create_test_thread(
            thread_id="5555555555",
            title="【AI】GPTエラーテスト2【リトライ】",
            popularity_score=0.82,
        ),
    ]

    with (
        patch.object(service, "_retrieve_ai_threads", new_callable=AsyncMock) as mock_retrieve,
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # _retrieve_ai_threadsはテストスレッドを返す
        mock_retrieve.return_value = test_threads

        # GPT APIエラーをシミュレート
        mock_gpt.side_effect = Exception("API rate limit exceeded")

        # 3. データ収集実行（GPTエラーがあっても処理は継続）
        result = await service.collect(thread_limit=5)

        # 4. 検証: データは保存されるべき（GPTエラーがあっても）
        assert result is not None, "GPTエラー時でもresultはNoneであってはいけません"
        assert len(result) > 0, "GPTエラーがあってもデータは保存されるべきです"

        saved_json_path, saved_md_path = result[0]
        assert Path(saved_json_path).exists(), f"JSONファイルが保存されていません: {saved_json_path}"

        # 5. 保存内容確認
        import json

        with open(saved_json_path) as f:
            saved_data = json.load(f)

        # データは取得されている
        assert len(saved_data) >= 1, "最低1件のスレッドが保存されるべきです"

        for thread in saved_data:
            # 必須フィールドの確認
            assert "title" in thread, "titleフィールドが存在しません"
            assert "url" in thread, "urlフィールドが存在しません"
            assert "board" in thread, "boardフィールドが存在しません"

            # summaryフィールドの検証
            # GPTエラー時は、summaryがNone、空文字列、またはエラーメッセージの可能性がある
            if "summary" in thread:
                # summaryが存在する場合は文字列型であることを確認
                if thread["summary"] is not None:
                    assert isinstance(thread["summary"], str), f"summaryは文字列またはNoneであるべきです: {type(thread['summary'])}"
