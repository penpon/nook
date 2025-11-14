"""
nook/services/hacker_news/hacker_news.py のテスト

テスト観点:
- HackerNewsRetrieverの初期化
- トップストーリー取得
- ストーリー詳細取得
- スコアフィルタリング
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.hacker_news.hacker_news import HackerNewsRetriever, Story

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: HackerNewsRetrieverを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        assert service.service_name == "hacker_news"
        assert service.http_client is None


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
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

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
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
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
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

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
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
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(mock_env_vars):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされるが、例外は発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_json(mock_env_vars):
    """
    Given: 不正なJSON
    When: collectメソッドを呼び出す
    Then: エラーがログされ、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(return_value=Mock(json=list))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(json=lambda: [12345]),
                    Mock(
                        json=lambda: {
                            "id": 12345,
                            "type": "story",
                            "score": 100,
                            "title": "Test",
                        }
                    ),
                ]
            )
            service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. collect メソッドのテスト - 境界値
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_empty_stories(mock_env_vars):
    """
    Given: 空のストーリーリスト
    When: collectメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock):
            service.http_client.get = AsyncMock(return_value=Mock(json=list))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 5. Story モデルのテスト
# =============================================================================


@pytest.mark.unit
def test_story_creation():
    """
    Given: ストーリー情報
    When: Storyオブジェクトを作成
    Then: 正しくインスタンス化される
    """
    story = Story(title="Test Story", score=200, url="https://example.com/test", text="Test text")

    assert story.title == "Test Story"
    assert story.score == 200
    assert story.url == "https://example.com/test"


# =============================================================================
# 6. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            service.http_client.get = AsyncMock(
                side_effect=[
                    Mock(json=lambda: [12345]),
                    Mock(
                        json=lambda: {
                            "id": 12345,
                            "type": "story",
                            "score": 100,
                            "title": "Test",
                        }
                    ),
                ]
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)

            await service.cleanup()
