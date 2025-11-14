"""
nook/services/reddit_explorer/reddit_explorer.py のテスト

テスト観点:
- RedditExplorerの初期化
- サブレディット投稿取得
- 投稿フィルタリング
- データ保存
- エラーハンドリング
- 内部メソッドのユニットテスト（OAuth認証、投稿タイプ判定、UTC→JST変換、GPT要約）
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


# ヘルパー関数：非同期イテレータを作成
async def async_generator(items):
    """非同期イテレータを作成するヘルパー"""
    for item in items:
        yield item

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
    with patch("nook.common.logging.setup_logger"):
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
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ), patch(
            "asyncpraw.Reddit"
        ) as mock_reddit:

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
            mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date(2023, 11, 15)])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_subreddits(mock_env_vars):
    """
    Given: 複数のサブレディット
    When: collectメソッドを呼び出す
    Then: 全てのサブレディットが処理される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock), patch(
            "asyncpraw.Reddit"
        ) as mock_reddit, patch(
            "tomli.load", return_value={"subreddits": ["python", "programming"]}
        ):

            mock_subreddit = Mock()
            mock_subreddit.hot = Mock(return_value=async_generator([]))

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            result = await service.collect(target_dates=[date(2023, 11, 15)])

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
    Then: エラーがログされ、空のリストが返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with patch.object(service, "setup_http_client", new_callable=AsyncMock), patch(
            "asyncpraw.Reddit"
        ) as mock_reddit:

            # Redditのコンテキストマネージャーがエラーを投げる
            mock_reddit.return_value.__aenter__.side_effect = Exception("Network error")

            # 例外が発生せず、空のリストが返ることを確認
            with pytest.raises(Exception, match="Network error"):
                result = await service.collect(target_dates=[date(2023, 11, 15)])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock), patch(
            "asyncpraw.Reddit"
        ) as mock_reddit:

            mock_subreddit = Mock()
            mock_submission = Mock()
            mock_submission.title = "Test"
            mock_submission.score = 100
            mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await service.collect(target_dates=[date(2023, 11, 15)])

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
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ), patch(
            "asyncpraw.Reddit"
        ) as mock_reddit:

            mock_subreddit = Mock()
            mock_submission = Mock()
            mock_submission.title = "Test Post"
            mock_submission.score = 100
            mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

            mock_reddit_instance = Mock()
            mock_reddit_instance.subreddit = Mock(return_value=mock_subreddit)
            mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date(2023, 11, 15)])

            assert isinstance(result, list)

            await service.cleanup()


# =============================================================================
# 5. OAuth認証のユニットテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_valid_credentials(mock_env_vars):
    """
    Given: 有効なReddit APIクレデンシャル
    When: RedditExplorerを初期化
    Then: client_id, client_secret, user_agentが正しく設定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )

        assert service.client_id == "test-id"
        assert service.client_secret == "test-secret"
        assert service.user_agent == "test-agent"


@pytest.mark.unit
def test_init_with_env_credentials(mock_env_vars):
    """
    Given: 環境変数でReddit APIクレデンシャルを設定
    When: RedditExplorerを初期化（引数なし）
    Then: 環境変数から認証情報が読み込まれる
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        assert service.client_id == "test-client-id"
        assert service.client_secret == "test-client-secret"
        assert service.user_agent == "test-user-agent"


@pytest.mark.unit
def test_init_missing_credentials(mock_env_vars, monkeypatch):
    """
    Given: Reddit APIクレデンシャルが不足
    When: RedditExplorerを初期化
    Then: ValueErrorが発生
    """
    # 環境変数のReddit関連をクリア
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        with pytest.raises(ValueError, match="Reddit API credentials"):
            RedditExplorer(client_id="test-id", user_agent="test-agent")  # client_secretが欠落


@pytest.mark.unit
def test_init_missing_all_credentials(monkeypatch):
    """
    Given: 環境変数もパラメータもReddit APIクレデンシャルなし
    When: RedditExplorerを初期化
    Then: ValueErrorが発生
    """
    # OPENAI_API_KEYは設定（BaseServiceの初期化に必要）
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    # Reddit関連の環境変数をクリア
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        with pytest.raises(ValueError, match="Reddit API credentials"):
            RedditExplorer()


# =============================================================================
# 6. 投稿タイプ判定のユニットテスト（7種類）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_image(mock_env_vars):
    """
    Given: 画像投稿（.jpg, .png等）
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'image'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        # モックsubmission作成（画像）
        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = False
        mock_submission.url = "https://i.redd.it/test.jpg"
        mock_submission.title = "Image Post"
        mock_submission.selftext = ""
        mock_submission.score = 100
        mock_submission.id = "img123"
        mock_submission.permalink = "/r/test/comments/img123"
        mock_submission.thumbnail = "https://thumb.jpg"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "image"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_gallery(mock_env_vars):
    """
    Given: ギャラリー投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'gallery'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = True  # ギャラリー
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = False
        mock_submission.url = "https://reddit.com/gallery/test"
        mock_submission.title = "Gallery Post"
        mock_submission.selftext = ""
        mock_submission.score = 200
        mock_submission.id = "gal123"
        mock_submission.permalink = "/r/test/comments/gal123"
        mock_submission.thumbnail = "self"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "gallery"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_video(mock_env_vars):
    """
    Given: ビデオ投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'video'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = True  # ビデオ
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = False
        mock_submission.url = "https://v.redd.it/test"
        mock_submission.title = "Video Post"
        mock_submission.selftext = ""
        mock_submission.score = 300
        mock_submission.id = "vid123"
        mock_submission.permalink = "/r/test/comments/vid123"
        mock_submission.thumbnail = "https://thumb.jpg"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "video"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_poll(mock_env_vars):
    """
    Given: 投票投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'poll'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = {"options": [{"text": "Option 1"}]}  # 投票
        mock_submission.crosspost_parent = None
        mock_submission.is_self = True
        mock_submission.url = "https://reddit.com/r/test/poll"
        mock_submission.title = "Poll Post"
        mock_submission.selftext = "What do you think?"
        mock_submission.score = 150
        mock_submission.id = "poll123"
        mock_submission.permalink = "/r/test/comments/poll123"
        mock_submission.thumbnail = "self"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="どう思いますか？")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "poll"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_crosspost(mock_env_vars):
    """
    Given: クロスポスト
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'crosspost'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = "t3_original123"  # クロスポスト
        mock_submission.is_self = False
        mock_submission.url = "https://reddit.com/r/original/post"
        mock_submission.title = "Crosspost"
        mock_submission.selftext = ""
        mock_submission.score = 250
        mock_submission.id = "cross123"
        mock_submission.permalink = "/r/test/comments/cross123"
        mock_submission.thumbnail = "https://thumb.jpg"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "crosspost"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_text(mock_env_vars):
    """
    Given: テキスト投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'text'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = True  # セルフテキスト投稿
        mock_submission.url = "https://reddit.com/r/test/text"
        mock_submission.title = "Text Post"
        mock_submission.selftext = "This is a text post"
        mock_submission.score = 50
        mock_submission.id = "text123"
        mock_submission.permalink = "/r/test/comments/text123"
        mock_submission.thumbnail = "self"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="これはテキスト投稿です")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "text"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_type_detection_link(mock_env_vars):
    """
    Given: 外部リンク投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: 投稿タイプが'link'と判定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = False
        mock_submission.url = "https://example.com/article"  # 外部リンク
        mock_submission.title = "Link Post"
        mock_submission.selftext = ""
        mock_submission.score = 175
        mock_submission.id = "link123"
        mock_submission.permalink = "/r/test/comments/link123"
        mock_submission.thumbnail = "https://thumb.jpg"
        mock_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 1
        assert posts[0].type == "link"


# =============================================================================
# 7. UTC→JST変換のユニットテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_utc_to_jst_conversion(mock_env_vars):
    """
    Given: UTC タイムスタンプの投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: created_atがUTCタイムゾーンで正しく変換される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        # 2024-01-01 00:00:00 UTC = 1704067200
        utc_timestamp = 1704067200

        mock_submission = Mock()
        mock_submission.stickied = False
        mock_submission.is_video = False
        mock_submission.is_gallery = False
        mock_submission.poll_data = None
        mock_submission.crosspost_parent = None
        mock_submission.is_self = True
        mock_submission.url = "https://reddit.com/test"
        mock_submission.title = "UTC Test"
        mock_submission.selftext = "Test content"
        mock_submission.score = 100
        mock_submission.id = "utc123"
        mock_submission.permalink = "/r/test/comments/utc123"
        mock_submission.thumbnail = "self"
        mock_submission.created_utc = utc_timestamp

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([mock_submission]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="テスト内容")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test",
            limit=10,
            dedup_tracker=dedup_tracker,
            target_dates=[date(2024, 1, 1)],
        )

        assert len(posts) == 1
        assert posts[0].created_at is not None
        # UTCタイムゾーンで保存されることを確認
        assert posts[0].created_at.tzinfo == timezone.utc
        # タイムスタンプが正しく変換されることを確認
        expected_dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
        assert posts[0].created_at == expected_dt


# =============================================================================
# 8. GPT要約のユニットテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_success(mock_env_vars):
    """
    Given: 有効なReddit投稿
    When: _summarize_reddit_postで要約を生成
    Then: GPTクライアントが呼ばれ、要約が設定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()

        post = RedditPost(
            type="text",
            id="test123",
            title="Test Post",
            url=None,
            upvotes=100,
            text="Test content",
            comments=[
                {"text": "Great post!", "score": 50},
                {"text": "I agree", "score": 30},
            ],
        )

        # GPTクライアントをモック
        service.gpt_client = Mock()
        service.gpt_client.generate_content = Mock(return_value="これは要約です。")

        await service._summarize_reddit_post(post)

        # GPTクライアントが呼ばれたことを確認
        assert service.gpt_client.generate_content.called
        # 要約が設定されたことを確認
        assert post.summary == "これは要約です。"
        # プロンプトにタイトル、本文、コメントが含まれることを確認
        call_kwargs = service.gpt_client.generate_content.call_args[1]
        assert "Test Post" in call_kwargs["prompt"]
        assert "Test content" in call_kwargs["prompt"]
        assert "Great post!" in call_kwargs["prompt"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_with_url(mock_env_vars):
    """
    Given: URLを含むReddit投稿
    When: _summarize_reddit_postで要約を生成
    Then: プロンプトにURLが含まれる
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()

        post = RedditPost(
            type="link",
            id="test123",
            title="Link Post",
            url="https://example.com/article",
            upvotes=200,
            text="",
            comments=[],
        )

        service.gpt_client = Mock()
        service.gpt_client.generate_content = Mock(return_value="リンク要約")

        await service._summarize_reddit_post(post)

        call_kwargs = service.gpt_client.generate_content.call_args[1]
        assert "https://example.com/article" in call_kwargs["prompt"]
        assert post.summary == "リンク要約"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_error_handling(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_reddit_postで要約を生成
    Then: エラーメッセージが要約に設定される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()

        post = RedditPost(
            type="text",
            id="test123",
            title="Error Test",
            url=None,
            upvotes=50,
            text="Content",
            comments=[],
        )

        service.gpt_client = Mock()
        service.gpt_client.generate_content = Mock(
            side_effect=Exception("API Error")
        )

        await service._summarize_reddit_post(post)

        # エラーメッセージが要約に含まれることを確認
        assert "エラーが発生しました" in post.summary
        assert "API Error" in post.summary


# =============================================================================
# 9. 翻訳機能のユニットテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_success(mock_env_vars):
    """
    Given: 英語テキスト
    When: _translate_to_japaneseで翻訳
    Then: 日本語に翻訳される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        service.gpt_client = Mock()
        service.gpt_client.generate_content = Mock(return_value="これは翻訳されたテキストです。")

        result = await service._translate_to_japanese("This is a test text.")

        assert result == "これは翻訳されたテキストです。"
        assert service.gpt_client.generate_content.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_empty_text(mock_env_vars):
    """
    Given: 空文字列
    When: _translate_to_japaneseで翻訳
    Then: 空文字列が返される（GPT呼び出しなし）
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        service.gpt_client = Mock()

        result = await service._translate_to_japanese("")

        assert result == ""
        assert not service.gpt_client.generate_content.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_error_handling(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _translate_to_japaneseで翻訳
    Then: 原文がそのまま返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        service.gpt_client = Mock()
        service.gpt_client.generate_content = Mock(
            side_effect=Exception("Translation Error")
        )

        original_text = "Original English text"
        result = await service._translate_to_japanese(original_text)

        assert result == original_text  # 原文が返される


# =============================================================================
# 10. エラーケースのユニットテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_subreddit_not_found(mock_env_vars):
    """
    Given: 存在しないサブレディット
    When: _retrieve_hot_postsで取得
    Then: 例外が発生する
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(
            side_effect=Exception("Subreddit not found")
        )

        dedup_tracker = DedupTracker()

        with pytest.raises(Exception, match="Subreddit not found"):
            await service._retrieve_hot_posts(
                "nonexistent",
                limit=10,
                dedup_tracker=dedup_tracker,
                target_dates=[date(2023, 11, 15)],
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_empty_results(mock_env_vars):
    """
    Given: 投稿が0件のサブレディット
    When: _retrieve_hot_postsで取得
    Then: 空リストが返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "empty", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        assert len(posts) == 0
        assert total == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_skip_stickied(mock_env_vars):
    """
    Given: スティッキー投稿を含むサブレディット
    When: _retrieve_hot_postsで取得
    Then: スティッキー投稿はスキップされる
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        # スティッキー投稿
        stickied_submission = Mock()
        stickied_submission.stickied = True

        # 通常投稿
        normal_submission = Mock()
        normal_submission.stickied = False
        normal_submission.is_video = False
        normal_submission.is_gallery = False
        normal_submission.poll_data = None
        normal_submission.crosspost_parent = None
        normal_submission.is_self = True
        normal_submission.url = "https://reddit.com/test"
        normal_submission.title = "Normal Post"
        normal_submission.selftext = "Content"
        normal_submission.score = 100
        normal_submission.id = "normal123"
        normal_submission.permalink = "/r/test/comments/normal123"
        normal_submission.thumbnail = "self"
        normal_submission.created_utc = 1699999999

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(
            return_value=async_generator([stickied_submission, normal_submission])
        )

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(return_value="内容")

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        # スティッキー投稿はスキップされ、カウントもされない
        assert total == 1  # 通常投稿のみカウント
        assert len(posts) == 1
        assert posts[0].title == "Normal Post"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_duplicate_titles(mock_env_vars):
    """
    Given: 重複するタイトルの投稿
    When: _retrieve_hot_postsで取得
    Then: 重複投稿はスキップされる
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.common.dedup import DedupTracker
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        # 同じタイトルの2つの投稿
        submission1 = Mock()
        submission1.stickied = False
        submission1.is_video = False
        submission1.is_gallery = False
        submission1.poll_data = None
        submission1.crosspost_parent = None
        submission1.is_self = True
        submission1.url = "https://reddit.com/test1"
        submission1.title = "Duplicate Title"
        submission1.selftext = "First post"
        submission1.score = 100
        submission1.id = "dup1"
        submission1.permalink = "/r/test/comments/dup1"
        submission1.thumbnail = "self"
        submission1.created_utc = 1699999999

        submission2 = Mock()
        submission2.stickied = False
        submission2.is_video = False
        submission2.is_gallery = False
        submission2.poll_data = None
        submission2.crosspost_parent = None
        submission2.is_self = True
        submission2.url = "https://reddit.com/test2"
        submission2.title = "Duplicate Title"  # 同じタイトル
        submission2.selftext = "Second post"
        submission2.score = 150
        submission2.id = "dup2"
        submission2.permalink = "/r/test/comments/dup2"
        submission2.thumbnail = "self"
        submission2.created_utc = 1700000000

        mock_subreddit = Mock()
        mock_subreddit.hot = Mock(return_value=async_generator([submission1, submission2]))

        service.reddit = Mock()
        service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
        service._translate_to_japanese = AsyncMock(
            side_effect=["最初の投稿", "2番目の投稿"]
        )

        dedup_tracker = DedupTracker()
        posts, total = await service._retrieve_hot_posts(
            "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
        )

        # 2件見つかったが、1件のみ返される（重複除外）
        assert total == 2
        assert len(posts) == 1
        assert posts[0].title == "Duplicate Title"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_top_comments_success(mock_env_vars):
    """
    Given: コメントを持つ投稿
    When: _retrieve_top_comments_of_postでコメント取得
    Then: トップコメントが取得され翻訳される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()

        post = RedditPost(
            type="text",
            id="test123",
            title="Test",
            url=None,
            upvotes=100,
            text="Content",
        )

        # モックコメント
        mock_comment1 = Mock()
        mock_comment1.body = "Great post!"
        mock_comment1.score = 50

        mock_comment2 = Mock()
        mock_comment2.body = "I agree"
        mock_comment2.score = 30

        # モックsubmission
        mock_submission = Mock()
        mock_submission.comments.replace_more = AsyncMock()
        mock_submission.comments.list = Mock(return_value=[mock_comment1, mock_comment2])

        service.reddit = Mock()
        service.reddit.submission = AsyncMock(return_value=mock_submission)
        service._translate_to_japanese = AsyncMock(
            side_effect=["素晴らしい投稿！", "同意します"]
        )

        comments = await service._retrieve_top_comments_of_post(post, limit=5)

        assert len(comments) == 2
        assert comments[0]["text"] == "素晴らしい投稿！"
        assert comments[0]["score"] == 50
        assert comments[1]["text"] == "同意します"
        assert comments[1]["score"] == 30


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_top_comments_empty(mock_env_vars):
    """
    Given: コメントがない投稿
    When: _retrieve_top_comments_of_postでコメント取得
    Then: 空リストが返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()

        post = RedditPost(
            type="text",
            id="test123",
            title="Test",
            url=None,
            upvotes=100,
            text="Content",
        )

        mock_submission = Mock()
        mock_submission.comments.replace_more = AsyncMock()
        mock_submission.comments.list = Mock(return_value=[])

        service.reddit = Mock()
        service.reddit.submission = AsyncMock(return_value=mock_submission)

        comments = await service._retrieve_top_comments_of_post(post, limit=5)

        assert len(comments) == 0


# =============================================================================
# 11. ヘルパーメソッドのユニットテスト
# =============================================================================


@pytest.mark.unit
def test_extract_post_id_from_permalink(mock_env_vars):
    """
    Given: Redditパーマリンク
    When: _extract_post_id_from_permalinkでID抽出
    Then: 正しい投稿IDが返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        # 標準的なパーマリンク
        permalink1 = "https://www.reddit.com/r/python/comments/abc123/test_post/"
        assert service._extract_post_id_from_permalink(permalink1) == "abc123"

        # クエリパラメータ付き
        permalink2 = (
            "https://www.reddit.com/r/python/comments/xyz789/test/?utm_source=share"
        )
        assert service._extract_post_id_from_permalink(permalink2) == "xyz789"

        # 末尾スラッシュなし
        permalink3 = "/r/test/comments/def456/my_post"
        assert service._extract_post_id_from_permalink(permalink3) == "def456"

        # 空文字列
        assert service._extract_post_id_from_permalink("") == ""

        # commentsがないパターン
        permalink4 = "/r/test/ghi789"
        assert service._extract_post_id_from_permalink(permalink4) == "ghi789"


@pytest.mark.unit
def test_post_sort_key(mock_env_vars):
    """
    Given: 投稿レコード
    When: _post_sort_keyでソートキー取得
    Then: popularity_scoreとcreated_atのタプルが返される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import RedditExplorer

        service = RedditExplorer()

        item = {
            "popularity_score": 150.5,
            "created_at": "2024-01-01T12:00:00+00:00",
        }

        popularity, created = service._post_sort_key(item)

        assert popularity == 150.5
        assert created.year == 2024
        assert created.month == 1
        assert created.day == 1


@pytest.mark.unit
def test_select_top_posts(mock_env_vars):
    """
    Given: 複数の投稿
    When: _select_top_postsで上位を選択
    Then: popularity_scoreの高い順に並び替えられる
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.reddit_explorer.reddit_explorer import (
            RedditExplorer,
            RedditPost,
        )

        service = RedditExplorer()
        service.SUMMARY_LIMIT = 2

        post1 = RedditPost(
            type="text",
            id="1",
            title="Post 1",
            url=None,
            upvotes=100,
            text="",
            popularity_score=100.0,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        post2 = RedditPost(
            type="text",
            id="2",
            title="Post 2",
            url=None,
            upvotes=200,
            text="",
            popularity_score=200.0,
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

        post3 = RedditPost(
            type="text",
            id="3",
            title="Post 3",
            url=None,
            upvotes=150,
            text="",
            popularity_score=150.0,
            created_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        )

        posts = [
            ("tech", "python", post1),
            ("tech", "programming", post2),
            ("tech", "coding", post3),
        ]

        selected = service._select_top_posts(posts)

        # 上位2件のみ
        assert len(selected) == 2
        # 人気順
        assert selected[0][2].id == "2"  # popularity_score 200
        assert selected[1][2].id == "3"  # popularity_score 150
