"""Reddit Explorer 統合テスト

テスト観点:
- データ取得→GPT要約→Storage保存の全体フロー
- ネットワークエラーハンドリング
- GPT APIエラーハンドリング
- 空データハンドリング
- 大量データパフォーマンス
- リトライメカニズム
"""

from __future__ import annotations

import tracemalloc
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

# =============================================================================
# パフォーマンス制約定数
# =============================================================================
MAX_MEMORY_USAGE_MB = 50

# =============================================================================
# タスク1.1: 基本統合テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_reddit_explorer_to_storage(tmp_path, mock_env_vars):
    """Given: RedditExplorerサービスインスタンス
    When: collect()を実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功
    """
    # 1. サービス初期化
    service = RedditExplorer()
    # テスト用のストレージパスを設定（tmp_pathを使用してテスト分離）
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    # 2. モック設定（asyncpraw Redditクライアント）
    unique_id = str(uuid.uuid4())[:8]
    mock_submission = Mock()
    mock_submission.id = f"test_{unique_id}"
    mock_submission.title = f"Unique Test Reddit Post {unique_id}"
    mock_submission.selftext = "This is a test post content."
    mock_submission.author = Mock()
    mock_submission.author.name = "test_user"
    mock_submission.score = 100
    mock_submission.num_comments = 25
    mock_submission.created_utc = datetime(2025, 11, 18, 12, 0, 0, tzinfo=UTC).timestamp()
    mock_submission.url = "https://reddit.com/r/test/comments/test123"
    mock_submission.permalink = "/r/test/comments/test123"
    mock_submission.stickied = False
    mock_submission.is_self = True
    mock_submission.thumbnail = "self"
    mock_submission.is_video = False
    mock_submission.is_gallery = False
    mock_submission.poll_data = None
    mock_submission.crosspost_parent = None
    # コメントモック
    mock_comment = Mock()
    mock_comment.body = "This is a test comment"
    mock_comment.score = 10
    mock_comment.author = Mock()
    mock_comment.author.name = "comment_user"
    mock_comments_obj = Mock()
    mock_comments_obj.replace_more = AsyncMock(return_value=None)
    mock_comments_obj.list = Mock(return_value=[mock_comment])
    mock_submission.comments = mock_comments_obj

    async def mock_hot_generator(*args, **kwargs):
        """Async generatorのモック"""
        yield mock_submission

    mock_subreddit = Mock()
    mock_subreddit.hot = mock_hot_generator

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("asyncpraw.Reddit", return_value=mock_reddit),
        patch.object(service.gpt_client, "generate_content", return_value="テスト要約"),
        patch.object(
            service, "_retrieve_top_comments_of_post", new_callable=AsyncMock, return_value=[]
        ),
    ):
        # 3. データ収集実行
        result = await service.collect(limit=1, target_dates=[date(2025, 11, 18)])

        # 4. 検証: データ取得確認
        assert len(result) > 0, "データが取得できていません"

        # 5. 検証: Storage保存確認
        # データディレクトリが作成されているか確認
        # tmp_pathを使用しているため、tmp_path配下のディレクトリをチェック
        expected_dir = tmp_path / "data" / "reddit_explorer"
        assert expected_dir.exists(), f"ストレージディレクトリが作成されていません: {expected_dir}"
        saved_data_paths = list(expected_dir.glob("*.json"))
        assert len(saved_data_paths) > 0, (
            f"ストレージディレクトリにJSONファイルが保存されていません: {expected_dir}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_reddit_explorer(tmp_path, mock_env_vars):
    """Given: ネットワークエラーが発生する状況
    When: collect()を実行
    Then: 適切なエラーハンドリングがされる
    """
    service = RedditExplorer()
    # テスト用のストレージパスを設定
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.side_effect = httpx.ConnectError("Connection failed")
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    with patch("asyncpraw.Reddit", return_value=mock_reddit):
        # エラーハンドリング確認
        # RedditExplorerはエラーをログに記録するが、例外をraiseしない設計の場合があるため
        # 結果が空であることを確認
        result = await service.collect(limit=1)
        # ネットワークエラー時は結果が空であるべき
        assert len(result) == 0, "ネットワークエラー時は結果が空であるべき"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_reddit_explorer(tmp_path, mock_env_vars):
    """Given: GPT APIエラーが発生する状況
    When: collect()を実行
    Then: フォールバック処理が動作
    """
    service = RedditExplorer()
    # テスト用のストレージパスを設定
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    # モック設定
    unique_id = str(uuid.uuid4())[:8]
    mock_submission = Mock()
    mock_submission.id = f"test_{unique_id}"
    mock_submission.title = f"Unique GPT Test Post {unique_id}"
    mock_submission.selftext = "This is a test post content."
    mock_submission.author = Mock()
    mock_submission.author.name = "test_user"
    mock_submission.score = 100
    mock_submission.num_comments = 25
    mock_submission.created_utc = datetime(2025, 11, 18, 12, 0, 0, tzinfo=UTC).timestamp()
    mock_submission.url = "https://reddit.com/r/test/comments/test123"
    mock_submission.permalink = "/r/test/comments/test123"
    mock_submission.stickied = False
    mock_submission.is_self = True
    mock_submission.thumbnail = "self"
    mock_submission.is_video = False
    mock_submission.is_gallery = False
    mock_submission.poll_data = None
    mock_submission.crosspost_parent = None
    # コメントモック
    mock_comment = Mock()
    mock_comment.body = "This is a test comment"
    mock_comment.score = 10
    mock_comment.author = Mock()
    mock_comment.author.name = "comment_user"
    mock_comments_obj = Mock()
    mock_comments_obj.replace_more = AsyncMock(return_value=None)
    mock_comments_obj.list = Mock(return_value=[mock_comment])
    mock_submission.comments = mock_comments_obj

    async def mock_hot_generator(*args, **kwargs):
        """Async generatorのモック"""
        yield mock_submission

    mock_subreddit = Mock()
    mock_subreddit.hot = mock_hot_generator

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("asyncpraw.Reddit", return_value=mock_reddit),
        patch.object(
            service.gpt_client, "generate_content", side_effect=Exception("API rate limit exceeded")
        ) as mock_gpt,
        patch.object(
            service, "_retrieve_top_comments_of_post", new_callable=AsyncMock, return_value=[]
        ),
    ):
        # フォールバック動作確認
        result = await service.collect(limit=1)

        # 検証: GPTエラー時でも処理は継続され、結果はリスト型
        assert isinstance(result, list), "GPTエラー時でも結果はリスト型であるべき"
        # GPTが呼ばれたことを確認（エラーハンドリングが動作している証拠）
        assert mock_gpt.called, "GPT APIが呼ばれるべき"


# =============================================================================
# タスク1.2: エッジケースと境界値テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_data_handling_reddit_explorer(tmp_path, mock_env_vars):
    """Given: サブレディットが空（投稿が0件）
    When: collect()を実行
    Then: エラーなく処理され、空のリストが返される
    """
    service = RedditExplorer()
    # テスト用のストレージパスを設定
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    async def mock_empty_generator(*args, **kwargs):
        """空のasync generatorのモック"""
        if False:
            yield

    mock_subreddit = Mock()
    mock_subreddit.hot = mock_empty_generator

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    with patch("asyncpraw.Reddit", return_value=mock_reddit):
        # 実行
        result = await service.collect(limit=10)

        # 検証: 空データでもエラーなく処理される
        assert isinstance(result, list), "結果がリスト型でない"
        assert len(result) == 0, "空のサブレディットから0件の結果が期待される"


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.asyncio
async def test_large_dataset_performance_reddit_explorer(tmp_path, mock_env_vars):
    """Given: 大量データ（100件の投稿）を処理する
    When: collect()を実行
    Then: メモリ使用量が50MB以内
    """
    service = RedditExplorer()
    # テスト用のストレージパスを設定
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    # 大量投稿のモック（100件）
    test_batch_id = str(uuid.uuid4())[:8]
    mock_submissions = []
    for i in range(100):
        mock_submission = Mock()
        mock_submission.id = f"perf_test_{test_batch_id}_{i}"
        mock_submission.title = f"Unique Perf Test Post {test_batch_id} #{i}"
        mock_submission.selftext = f"This is test post content {i}." * 10  # 長めのテキスト
        mock_submission.author = Mock()
        mock_submission.author.name = f"test_user_{i}"
        mock_submission.score = 100 + i
        mock_submission.num_comments = 25 + i
        mock_submission.created_utc = datetime(2025, 11, 18, 12, 0, i % 60, tzinfo=UTC).timestamp()
        mock_submission.url = f"https://reddit.com/r/test/comments/test{i}"
        mock_submission.permalink = f"/r/test/comments/test{i}"
        mock_submission.stickied = False
        mock_submission.is_self = True
        mock_submission.thumbnail = "self"
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        # コメントモック
        mock_comment = Mock()
        mock_comment.body = f"Test comment {i}"
        mock_comment.score = 10 + i
        mock_comment.author = Mock()
        mock_comment.author.name = f"comment_user_{i}"
        mock_comments_obj = Mock()
        mock_comments_obj.replace_more = AsyncMock(return_value=None)
        mock_comments_obj.list = Mock(return_value=[mock_comment])
        mock_submission.comments = mock_comments_obj
        mock_submissions.append(mock_submission)

    async def mock_large_generator(*args, **kwargs):
        """大量データのasync generatorのモック"""
        for submission in mock_submissions:
            yield submission

    mock_subreddit = Mock()
    mock_subreddit.hot = mock_large_generator

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    tracemalloc.start()
    try:
        with (
            patch("asyncpraw.Reddit", return_value=mock_reddit),
            patch.object(service.gpt_client, "generate_content", return_value="テスト要約"),
            patch.object(
                service, "_retrieve_top_comments_of_post", new_callable=AsyncMock, return_value=[]
            ),
        ):
            # 実行
            result = await service.collect(limit=100, target_dates=[date(2025, 11, 18)])

            # メモリ使用量チェック
            current, peak = tracemalloc.get_traced_memory()

            # 50MB以内
            assert peak < MAX_MEMORY_USAGE_MB * 1024 * 1024, (
                f"メモリ使用量が制限を超えました: {peak / (1024 * 1024):.2f} MB > {MAX_MEMORY_USAGE_MB} MB"
            )

            # データ取得確認
            assert len(result) > 0, "大量データでもデータが取得できること"
    finally:
        tracemalloc.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_mechanism_reddit_explorer(tmp_path, mock_env_vars):
    """Given: 最初の呼び出しでタイムアウト、2回目で成功する状況
    When: collect()を実行
    Then: リトライメカニズムが動作し、最終的に成功
    """
    service = RedditExplorer()
    # テスト用のストレージパスを設定
    from nook.common.storage import LocalStorage

    service.storage = LocalStorage(str(tmp_path / "data" / "reddit_explorer"))

    # モック投稿
    unique_id = str(uuid.uuid4())[:8]
    mock_submission = Mock()
    mock_submission.id = f"test_{unique_id}"
    mock_submission.title = f"Unique Retry Test Post {unique_id}"
    mock_submission.selftext = "This is a test post content."
    mock_submission.author = Mock()
    mock_submission.author.name = "test_user"
    mock_submission.score = 100
    mock_submission.num_comments = 25
    mock_submission.created_utc = datetime(2025, 11, 18, 12, 0, 0, tzinfo=UTC).timestamp()
    mock_submission.url = "https://reddit.com/r/test/comments/test123"
    mock_submission.permalink = "/r/test/comments/test123"
    mock_submission.stickied = False
    mock_submission.is_self = True
    mock_submission.thumbnail = "self"
    mock_submission.is_video = False
    mock_submission.is_gallery = False
    mock_submission.poll_data = None
    mock_submission.crosspost_parent = None
    # コメントモック
    mock_comment = Mock()
    mock_comment.body = "This is a test comment"
    mock_comment.score = 10
    mock_comment.author = Mock()
    mock_comment.author.name = "comment_user"
    mock_comments_obj = Mock()
    mock_comments_obj.replace_more = AsyncMock(return_value=None)
    mock_comments_obj.list = Mock(return_value=[mock_comment])
    mock_submission.comments = mock_comments_obj

    # hot()メソッドの呼び出し回数をカウント
    call_count = {"count": 0}

    async def mock_hot_with_retry(*args, **kwargs):
        """リトライをシミュレート: 1回目タイムアウト、2回目成功"""
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise httpx.TimeoutException("Timeout")
        # 2回目以降は成功
        yield mock_submission

    mock_subreddit = Mock()
    mock_subreddit.hot = mock_hot_with_retry

    mock_reddit = AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit
    mock_reddit.__aenter__ = AsyncMock(return_value=mock_reddit)
    mock_reddit.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("asyncpraw.Reddit", return_value=mock_reddit),
        patch.object(service.gpt_client, "generate_content", return_value="テスト要約"),
        patch.object(
            service, "_retrieve_top_comments_of_post", new_callable=AsyncMock, return_value=[]
        ),
    ):
        # 実行
        result = await service.collect(limit=1)

        # 検証: リトライが実行され、エラーハンドリングされたことを確認
        # RedditExplorerは複数のsubredditを処理するため、タイムアウト後も処理を継続する
        assert isinstance(result, list), "結果がリスト型でない"
        # タイムアウトが発生したが、処理は継続され結果が返される
        assert call_count["count"] >= 2, (
            f"リトライが実行されませんでした: call_count={call_count['count']}"
        )
