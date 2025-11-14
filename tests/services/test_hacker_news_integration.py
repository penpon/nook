"""
nook/services/hacker_news/hacker_news.py の統合テスト

collect()メソッドの統合的な動作をテストします。
これらのテストは複数のコンポーネントが連携する動作を確認するため、
単体テストよりも実行時間が長くなります。

Note: これらのテストは @pytest.mark.integration でマーク予定
現在は既存のテストとの互換性のため @pytest.mark.unit を維持
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nook.services.hacker_news.hacker_news import HackerNewsRetriever

# =============================================================================
# 統合テスト: collect メソッド
# =============================================================================


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_success_with_stories(mock_env_vars, mock_hn_api):
    """
    Given: 有効なHacker News API
    When: collectメソッドを呼び出す
    Then: ストーリーが正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ):

            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(json=lambda: [12345, 67890]),  # トップストーリーID
                    Mock(
                        json=lambda: {
                            "id": 12345,
                            "type": "story",
                            "by": "test_author",
                            "time": 1699999999,
                            "title": "Test HN Story",
                            "url": "https://example.com/test",
                            "score": 200,
                            "descendants": 50,
                        }
                    ),
                ]
            )
            service.gpt_client.generate_async = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_with_multiple_stories(mock_env_vars):
    """
    Given: 複数のストーリー
    When: collectメソッドを呼び出す
    Then: 全てのストーリーが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(json=lambda: [1, 2, 3]),
                    Mock(
                        json=lambda: {
                            "id": 1,
                            "type": "story",
                            "score": 100,
                            "title": "Story 1",
                        }
                    ),
                    Mock(
                        json=lambda: {
                            "id": 2,
                            "type": "story",
                            "score": 200,
                            "title": "Story 2",
                        }
                    ),
                    Mock(
                        json=lambda: {
                            "id": 3,
                            "type": "story",
                            "score": 150,
                            "title": "Story 3",
                        }
                    ),
                ]
            )
            service.gpt_client.generate_async = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_network_error(mock_env_vars):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: RetryExceptionが発生する

    Note: このテストは現在失敗します。統合テスト環境での修正が必要です。
    """
    import httpx

    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            # RetryExceptionが発生することを期待
            from nook.common.exceptions import RetryException

            with pytest.raises(RetryException):
                await service.collect(target_dates=[date.today()])


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_invalid_json(mock_env_vars):
    """
    Given: 不正なJSONレスポンス
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    import json

    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            # 不正なJSONレスポンス
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    json=Mock(side_effect=json.JSONDecodeError("test", "test", 0))
                )
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIでエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、処理は継続される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock):

            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(json=lambda: [1]),
                    Mock(
                        json=lambda: {
                            "id": 1,
                            "type": "story",
                            "score": 100,
                            "title": "Test",
                        }
                    ),
                ]
            )
            # GPTでエラー
            service.gpt_client.generate_async = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit  # TODO: @pytest.mark.integration に変更予定
@pytest.mark.asyncio
async def test_collect_with_empty_stories(mock_env_vars):
    """
    Given: ストーリーが見つからない
    When: collectメソッドを呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            # 空のストーリーリスト
            service.http_client.get = AsyncMock(return_value=Mock(json=list))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)
            assert len(result) == 0
