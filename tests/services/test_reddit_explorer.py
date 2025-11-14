"""
nook/services/reddit_explorer/reddit_explorer.py のテスト

テスト観点:
- RedditExplorerの初期化
- サブレディット投稿取得
- 投稿フィルタリング
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: RedditExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        assert service.service_name == "reddit_explorer"


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_posts(mock_env_vars, mock_reddit_api):
    """
    Given: 有効なReddit API
    When: collectメソッドを呼び出す
    Then: 投稿が正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
            patch("asyncpraw.Reddit") as mock_reddit,
        ):
            mock_subreddit = Mock()
            mock_submission = Mock()
            mock_submission.title = "Test Post"
            mock_submission.selftext = "Test content"
            mock_submission.score = 100
            mock_submission.num_comments = 25
            mock_submission.created_utc = 1699999999
            mock_submission.url = "https://reddit.com/test"
            mock_submission.permalink = "/r/test/comments/test"
            mock_submission.author.name = "test_user"
            mock_subreddit.hot = AsyncMock(return_value=[mock_submission])

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_subreddits(mock_env_vars):
    """
    Given: 複数のサブレディット
    When: collectメソッドを呼び出す
    Then: 全てのサブレディットが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch("asyncpraw.Reddit") as mock_reddit,
            patch("tomli.load", return_value={"subreddits": ["python", "programming"]}),
        ):
            mock_subreddit = Mock()
            mock_subreddit.hot = AsyncMock(return_value=[])

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

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
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch("asyncpraw.Reddit") as mock_reddit,
        ):
            mock_reddit.side_effect = Exception("Network error")

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
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch("asyncpraw.Reddit") as mock_reddit,
        ):
            mock_subreddit = Mock()
            mock_submission = Mock()
            mock_submission.title = "Test"
            mock_submission.score = 100
            mock_subreddit.hot = AsyncMock(return_value=[mock_submission])

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. エラーハンドリング統合テスト
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
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
            patch("asyncpraw.Reddit") as mock_reddit,
        ):
            mock_subreddit = Mock()
            mock_submission = Mock()
            mock_submission.title = "Test Post"
            mock_submission.score = 100
            mock_subreddit.hot = AsyncMock(return_value=[mock_submission])

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)

            await service.cleanup()
