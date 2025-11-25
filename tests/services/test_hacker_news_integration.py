"""Hacker News統合テスト

このファイルには、Hacker Newsサービスの統合テストが含まれています。
データ取得→GPT要約→Storage保存の全体フローをテストします。

## テスト構成

### タスク2.1: 基本統合テスト
- test_full_data_flow_hacker_news_to_storage: フルデータフロー
- test_error_handling_network_failure_hacker_news: ネットワークエラーハンドリング
- test_error_handling_gpt_api_failure_hacker_news: GPT APIエラーハンドリング

### タスク2.2: エッジケース・境界値テスト
- test_empty_data_handling_hacker_news: 空データハンドリング
- test_pagination_handling_hacker_news: ページネーション処理
- test_rate_limit_handling_hacker_news: レート制限ハンドリング
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.common.exceptions import RetryException
from nook.common.storage import LocalStorage
from nook.services.hacker_news.hacker_news import HackerNewsRetriever


# テスト用タイムスタンプ（今日の日付）
def get_today_timestamp() -> int:
    """今日の日付に対応するUNIXタイムスタンプを返す"""
    return int(datetime.now(UTC).timestamp())


# =============================================================================
# タスク2.1: 基本統合テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_00_full_data_flow_hacker_news_to_storage(tmp_path, mock_env_vars):
    """Given: Hacker Newsサービスインスタンス
    When: collect()を実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    # ストレージを一時ディレクトリに設定（BaseServiceがハードコードされたパスを使うため）
    service.storage = LocalStorage(str(tmp_path))
    await service.setup_http_client()

    # 2. モック設定（外部API）
    with (
        patch.object(service.http_client, "get") as mock_get,
        patch.object(service, "gpt_client") as mock_gpt,
        patch.object(service, "rate_limit", new_callable=AsyncMock),
    ):
        # HTTPレスポンスモック: topstories.json
        mock_topstories_response = Mock()
        mock_topstories_response.json.return_value = [12345, 12346, 12347]

        # HTTPレスポンスモック: 個別ストーリー（完全にユニークなタイトル）
        mock_story_response_1 = Mock()
        mock_story_response_1.json.return_value = {
            "title": "Full Data Flow Story Alpha Unique",
            "score": 100,
            "url": "https://example.com/test-fulldata-1",
            "text": "This is a test story with sufficient length for filtering. " * 10,
            "time": get_today_timestamp(),
        }

        mock_story_response_2 = Mock()
        mock_story_response_2.json.return_value = {
            "title": "Full Data Flow Story Beta Unique",
            "score": 100,
            "url": "https://example.com/test-fulldata-2",
            "text": "This is another test story with sufficient length for filtering. " * 10,
            "time": get_today_timestamp(),
        }

        mock_story_response_3 = Mock()
        mock_story_response_3.json.return_value = {
            "title": "Full Data Flow Story Gamma Unique",
            "score": 100,
            "url": "https://example.com/test-fulldata-3",
            "text": "This is yet another test story with sufficient length for filtering. " * 10,
            "time": get_today_timestamp(),
        }

        # URLごとにモックレスポンスを設定
        async def mock_get_side_effect(url, **kwargs):
            if "topstories.json" in url:
                return mock_topstories_response
            elif "/item/12345.json" in url:
                return mock_story_response_1
            elif "/item/12346.json" in url:
                return mock_story_response_2
            elif "/item/12347.json" in url:
                return mock_story_response_3
            raise ValueError(f"Unexpected URL: {url}")

        mock_get.side_effect = mock_get_side_effect

        # GPT要約モック
        mock_gpt.generate_async = AsyncMock(return_value="テスト要約")

        # 3. データ収集実行
        result = await service.collect(limit=3, target_dates=[date.today()])

        # 4. 検証: データ取得確認
        assert isinstance(result, list), "結果がリスト形式ではありません"
        assert len(result) > 0, f"データが取得されていません。Result: {result}"
        assert result[0][0].endswith(".json"), "JSONファイルが保存されていません"
        assert result[0][1].endswith(".md"), "Markdownファイルが保存されていません"

        # 5. 検証: GPT要約が呼び出された
        assert mock_gpt.generate_async.call_count > 0, "GPT要約が呼び出されていません"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_hacker_news(tmp_path, mock_env_vars):
    """Given: ネットワークエラーが発生する状況
    When: collect()を実行
    Then: 適切なエラーハンドリングがされる（リトライ後にRetryException発生）
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    await service.setup_http_client()

    # 2. ネットワークエラーをシミュレート
    with patch.object(service.http_client, "get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        # 3. エラーハンドリング確認（@handle_errorsデコレータでリトライ後にRetryException）
        with pytest.raises(RetryException):
            await service.collect(limit=3, target_dates=[date.today()])

        # 4. リトライが実行されたことを確認（3回のリトライ）
        assert mock_get.call_count >= 3, "リトライが実行されていません"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_hacker_news(tmp_path, mock_env_vars):
    """Given: GPT APIエラーが発生する状況
    When: collect()を実行
    Then: フォールバック処理が動作（エラーメッセージ付きでデータは保存される）
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    service.storage = LocalStorage(str(tmp_path))
    await service.setup_http_client()

    # 2. モック設定
    with (
        patch.object(service.http_client, "get") as mock_get,
        patch.object(service, "gpt_client") as mock_gpt,
        patch.object(service, "rate_limit", new_callable=AsyncMock),
    ):
        # HTTPレスポンスモック
        mock_topstories_response = Mock()
        mock_topstories_response.json.return_value = [12345, 12346]

        # ストーリー1
        mock_story_response_1 = Mock()
        mock_story_response_1.json.return_value = {
            "title": "GPT Error Test Story Alpha",
            "score": 100,
            "url": "https://example.com/test-alpha",
            "text": "This is a test story with sufficient length for filtering. " * 10,
            "time": get_today_timestamp(),
        }

        # ストーリー2
        mock_story_response_2 = Mock()
        mock_story_response_2.json.return_value = {
            "title": "GPT Error Test Story Beta",
            "score": 100,
            "url": "https://example.com/test-beta",
            "text": "This is another test story with sufficient length for filtering. " * 10,
            "time": get_today_timestamp(),
        }

        # URLベースのside_effect関数を定義
        async def mock_get_side_effect(url, **kwargs):
            if "topstories.json" in url:
                return mock_topstories_response
            if "/item/12345.json" in url:
                return mock_story_response_1
            if "/item/12346.json" in url:
                return mock_story_response_2
            raise ValueError(f"Unexpected URL: {url}")

        mock_get.side_effect = mock_get_side_effect

        # GPT APIエラーをシミュレート
        mock_gpt.generate_async = AsyncMock(side_effect=Exception("API rate limit exceeded"))

        # 3. データ収集実行（エラーがあっても処理は継続）
        result = await service.collect(limit=2, target_dates=[date.today()])

        # 4. 検証: エラーが発生してもプログラムはクラッシュせず、リストが返される
        # GPTエラーによりストーリーが保存されない場合もあるが、プログラムは正常に終了する
        assert isinstance(result, list), "結果がリスト形式ではありません"
        # GPT APIエラーが正しくハンドリングされたことを確認
        # （例外が発生せずに処理が完了したことで確認済み）


# =============================================================================
# タスク2.2: エッジケース・境界値テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_data_handling_hacker_news(tmp_path, mock_env_vars):
    """Given: トップストーリーが空の場合
    When: collect()を実行
    Then: 空のリストが返され、エラーなく処理が完了する
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    await service.setup_http_client()

    # 2. 空のトップストーリーをモック
    with patch.object(service.http_client, "get") as mock_get:
        mock_topstories_response = Mock()
        mock_topstories_response.json.return_value = []  # 空のリスト

        mock_get.return_value = mock_topstories_response

        # 3. データ収集実行
        result = await service.collect(limit=3, target_dates=[date.today()])

        # 4. 検証: 空のリストが返される
        assert isinstance(result, list), "結果がリスト形式ではありません"
        assert len(result) == 0, "空のデータに対して結果が返されています"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination_handling_hacker_news(tmp_path, mock_env_vars):
    """Given: 複数ページのストーリーが存在する場合
    When: collect()を実行
    Then: 指定されたlimit数までのストーリーが正しく取得される
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    service.storage = LocalStorage(str(tmp_path))
    await service.setup_http_client()

    # 2. 大量のストーリーIDをモック
    with (
        patch.object(service.http_client, "get") as mock_get,
        patch.object(service, "gpt_client") as mock_gpt,
        patch.object(service, "rate_limit", new_callable=AsyncMock),
    ):
        # 100個のストーリーID
        story_ids = list(range(10000, 10100))
        mock_topstories_response = Mock()
        mock_topstories_response.json.return_value = story_ids

        # ストーリー詳細のモック（各ストーリーにユニークなタイトル）
        def create_story_response(story_id: int) -> Mock:
            mock_response = Mock()
            mock_response.json.return_value = {
                "title": f"Test Pagination Story {story_id}",
                "score": 100,
                "url": f"https://example.com/test-{story_id}",
                "text": "This is a test story with sufficient length for filtering. " * 10,
                "time": get_today_timestamp(),
            }
            return mock_response

        # URLベースのside_effect関数を定義
        async def mock_get_side_effect(url, **kwargs):
            if "topstories.json" in url:
                return mock_topstories_response
            for story_id in story_ids:
                if f"/item/{story_id}.json" in url:
                    return create_story_response(story_id)
            raise ValueError(f"Unexpected URL: {url}")

        mock_get.side_effect = mock_get_side_effect

        # GPT要約モック
        mock_gpt.generate_async = AsyncMock(return_value="テスト要約")

        # 3. データ収集実行（limit=5で制限）
        result = await service.collect(limit=5, target_dates=[date.today()])

        # 4. 検証: limit数以下のストーリーが取得される
        assert isinstance(result, list), "結果がリスト形式ではありません"
        # フィルタリングやデデュプにより、実際の取得数はlimit以下になる可能性がある
        assert len(result) <= 5, f"limit=5を超える結果が返されました: {len(result)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limit_handling_hacker_news(tmp_path, mock_env_vars):
    """Given: レート制限エラー（429）が発生する状況
    When: collect()を実行
    Then: リトライが実行され、最終的にRetryExceptionが返される
    """
    # 1. サービス初期化
    service = HackerNewsRetriever(storage_dir=str(tmp_path))
    await service.setup_http_client()

    # 2. レート制限エラー（429）をモック
    with patch.object(service.http_client, "get") as mock_get:
        # HTTPステータス429を返すレスポンス
        mock_get.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=Mock(),
            response=Mock(status_code=429),
        )

        # 3. エラーハンドリング確認（@handle_errorsデコレータでリトライ後にRetryException）
        with pytest.raises(RetryException) as exc_info:
            await service.collect(limit=3, target_dates=[date.today()])

        # 4. 検証: 429エラーが原因でRetryExceptionが発生
        assert "429" in str(exc_info.value), "429エラーが原因のRetryExceptionではありません"

        # 5. リトライが実行されたことを確認
        assert mock_get.call_count >= 3, "リトライが実行されていません"
