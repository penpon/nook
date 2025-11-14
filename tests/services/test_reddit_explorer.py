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

# 共通インポート (各テスト内での繰り返しを削減)
from nook.common.dedup import DedupTracker
from nook.services.reddit_explorer.reddit_explorer import RedditExplorer, RedditPost

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================

@pytest.mark.unit
def test_init_with_default_storage_dir(reddit_explorer_service):
    """
    Given: デフォルトのstorage_dir
    When: RedditExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    assert reddit_explorer_service.service_name == "reddit_explorer"

# =============================================================================
# 2. OAuth認証のユニットテスト
# =============================================================================

@pytest.mark.unit
def test_init_with_valid_credentials():
    """
    Given: 有効なReddit APIクレデンシャル
    When: RedditExplorerを初期化
    Then: client_id, client_secret, user_agentが正しく設定される
    """
    with patch("nook.common.logging.setup_logger"):
        reddit_explorer_service = RedditExplorer(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )

        assert reddit_explorer_service.client_id == "test-id"
        assert reddit_explorer_service.client_secret == "test-secret"
        assert reddit_explorer_service.user_agent == "test-agent"

@pytest.mark.unit
def test_init_with_env_credentials(reddit_explorer_service):
    """
    Given: 環境変数でReddit APIクレデンシャルを設定
    When: RedditExplorerを初期化（引数なし）
    Then: 環境変数から認証情報が読み込まれる
    """
    assert reddit_explorer_service.client_id == "test-client-id"
    assert reddit_explorer_service.client_secret == "test-client-secret"
    assert reddit_explorer_service.user_agent == "test-user-agent"

@pytest.mark.unit
def test_init_missing_credentials(reddit_explorer_service, monkeypatch):
    """
    Given: Reddit APIクレデンシャルが不足
    When: RedditExplorerを初期化
    Then: ValueErrorが発生
    """
    # 環境変数のReddit関連をクリア
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

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

    with pytest.raises(ValueError, match="Reddit API credentials"):
        RedditExplorer()

# =============================================================================
# 3. 投稿タイプ判定のユニットテスト（7種類）- パラメタライズド
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "post_type,expected_type",
    [
        ("image", "image"),
        ("gallery", "gallery"),
        ("video", "video"),
        ("poll", "poll"),
        ("crosspost", "crosspost"),
        ("text", "text"),
        ("link", "link"),
    ],
    ids=["image", "gallery", "video", "poll", "crosspost", "text", "link"],
)
async def test_post_type_detection(
    reddit_explorer_service,
    mock_reddit_submission,
    test_dates,
    async_generator_helper,
    post_type,
    expected_type,
):
    """
    Given: 各種投稿タイプ（image/gallery/video/poll/crosspost/text/link）
    When: _retrieve_hot_postsで投稿を処理
    Then: 正しい投稿タイプが判定される
    """
    # フィクスチャファクトリーで投稿タイプに応じたモック作成
    mock_sub = mock_reddit_submission(
        post_type=post_type,
        title=f"{post_type.capitalize()} Post",
        post_id=f"{post_type}123",
        created_utc=test_dates["reddit_post_utc_timestamp"],
    )

    mock_subreddit = Mock()
    mock_subreddit.hot = Mock(return_value=async_generator_helper([mock_sub]))

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
    reddit_explorer_service._translate_to_japanese = AsyncMock(return_value="")

    dedup_tracker = DedupTracker()
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "test",
        limit=10,
        dedup_tracker=dedup_tracker,
        target_dates=[test_dates["reddit_post_date"]],
    )

    assert len(posts) == 1
    assert posts[0].type == expected_type

# =============================================================================
# 4. UTCタイムスタンプ変換のユニットテスト
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_utc_to_jst_conversion(
    reddit_explorer_service, mock_reddit_submission, test_dates, async_generator_helper
):
    """
    Given: UTC タイムスタンプの投稿
    When: _retrieve_hot_postsで投稿を処理
    Then: created_atがUTCタイムゾーンで正しく変換される
    """
    utc_timestamp = test_dates["utc_test_timestamp"]
    mock_sub = mock_reddit_submission(
        post_type="text",
        title="UTC Test",
        post_id="utc123",
        created_utc=utc_timestamp,
    )

    mock_subreddit = Mock()
    mock_subreddit.hot = Mock(return_value=async_generator_helper([mock_sub]))

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
    reddit_explorer_service._translate_to_japanese = AsyncMock(return_value="テスト内容")

    dedup_tracker = DedupTracker()
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "test",
        limit=10,
        dedup_tracker=dedup_tracker,
        target_dates=[test_dates["today"]],
    )

    assert len(posts) == 1
    assert posts[0].created_at is not None
    assert posts[0].created_at.tzinfo == timezone.utc
    expected_dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    assert posts[0].created_at == expected_dt

# =============================================================================
# 5. GPT要約のユニットテスト
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_success(reddit_explorer_service):
    """
    Given: 有効なReddit投稿
    When: _summarize_reddit_postで要約を生成
    Then: GPTクライアントが呼ばれ、要約が設定される
    """
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

    reddit_explorer_service.gpt_client = Mock()
    reddit_explorer_service.gpt_client.generate_content = Mock(
        return_value="これは要約です。"
    )

    await reddit_explorer_service._summarize_reddit_post(post)

    assert reddit_explorer_service.gpt_client.generate_content.called
    assert post.summary == "これは要約です。"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_with_url(reddit_explorer_service):
    """
    Given: URLを含むReddit投稿
    When: _summarize_reddit_postで要約を生成
    Then: プロンプトにURLが含まれる
    """
    post = RedditPost(
        type="link",
        id="test123",
        title="Link Post",
        url="https://example.com/article",
        upvotes=200,
        text="",
        comments=[],
    )

    reddit_explorer_service.gpt_client = Mock()
    reddit_explorer_service.gpt_client.generate_content = Mock(return_value="リンク要約")

    await reddit_explorer_service._summarize_reddit_post(post)

    call_kwargs = reddit_explorer_service.gpt_client.generate_content.call_args[1]
    assert "https://example.com/article" in call_kwargs["prompt"]
    assert post.summary == "リンク要約"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_reddit_post_error_handling(reddit_explorer_service):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_reddit_postで要約を生成
    Then: エラーメッセージが要約に設定される
    """
    post = RedditPost(
        type="text",
        id="test123",
        title="Error Test",
        url=None,
        upvotes=50,
        text="Content",
        comments=[],
    )

    reddit_explorer_service.gpt_client = Mock()
    reddit_explorer_service.gpt_client.generate_content = Mock(
        side_effect=Exception("API Error")
    )

    await reddit_explorer_service._summarize_reddit_post(post)

    # エラーメッセージが要約に含まれることを確認
    assert "エラーが発生しました" in post.summary
    assert "API Error" in post.summary

# =============================================================================
# 6. 翻訳機能のユニットテスト
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_success(reddit_explorer_service):
    """
    Given: 英語テキスト
    When: _translate_to_japaneseで翻訳
    Then: 日本語に翻訳される
    """
    reddit_explorer_service.gpt_client = Mock()
    reddit_explorer_service.gpt_client.generate_content = Mock(return_value="これは翻訳されたテキストです。")

    result = await reddit_explorer_service._translate_to_japanese("This is a test text.")

    assert result == "これは翻訳されたテキストです。"
    assert reddit_explorer_service.gpt_client.generate_content.called

@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_empty_text(reddit_explorer_service):
    """
    Given: 空文字列
    When: _translate_to_japaneseで翻訳
    Then: 空文字列が返される（GPT呼び出しなし）
    """
    reddit_explorer_service.gpt_client = Mock()

    result = await reddit_explorer_service._translate_to_japanese("")

    assert result == ""
    assert not reddit_explorer_service.gpt_client.generate_content.called

@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_to_japanese_error_handling(reddit_explorer_service):
    """
    Given: GPT APIがエラーを返す
    When: _translate_to_japaneseで翻訳
    Then: 原文がそのまま返される
    """
    reddit_explorer_service.gpt_client = Mock()
    reddit_explorer_service.gpt_client.generate_content = Mock(
        side_effect=Exception("Translation Error")
    )

    original_text = "Original English text"
    result = await reddit_explorer_service._translate_to_japanese(original_text)

    assert result == original_text  # 原文が返される

# =============================================================================
# 7. エラーケースのユニットテスト
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_subreddit_not_found(reddit_explorer_service):
    """
    Given: 存在しないサブレディット
    When: _retrieve_hot_postsで取得
    Then: 例外が発生する
    """
    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(
        side_effect=Exception("Subreddit not found")
    )

    dedup_tracker = DedupTracker()

    with pytest.raises(Exception, match="Subreddit not found"):
        await reddit_explorer_service._retrieve_hot_posts(
            "nonexistent",
            limit=10,
            dedup_tracker=dedup_tracker,
            target_dates=[date(2023, 11, 15)],
        )

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_empty_results(reddit_explorer_service, async_generator_helper):
    """
    Given: 投稿が0件のサブレディット
    When: _retrieve_hot_postsで取得
    Then: 空リストが返される
    """
    mock_subreddit = Mock()
    mock_subreddit.hot = Mock(return_value=async_generator_helper([]))

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)

    dedup_tracker = DedupTracker()
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "empty", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
    )

    assert len(posts) == 0
    assert total == 0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_skip_stickied(reddit_explorer_service, async_generator_helper):
    """
    Given: スティッキー投稿を含むサブレディット
    When: _retrieve_hot_postsで取得
    Then: スティッキー投稿はスキップされる
    """
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
        return_value=async_generator_helper([stickied_submission, normal_submission])
    )

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
    reddit_explorer_service._translate_to_japanese = AsyncMock(return_value="内容")

    dedup_tracker = DedupTracker()
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
    )

    # スティッキー投稿はスキップされ、カウントもされない
    assert total == 1  # 通常投稿のみカウント
    assert len(posts) == 1
    assert posts[0].title == "Normal Post"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_duplicate_titles(reddit_explorer_service, async_generator_helper):
    """
    Given: 重複するタイトルの投稿
    When: _retrieve_hot_postsで取得
    Then: 重複投稿はスキップされる
    """
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
    mock_subreddit.hot = Mock(return_value=async_generator_helper([submission1, submission2]))

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
    reddit_explorer_service._translate_to_japanese = AsyncMock(
        side_effect=["最初の投稿", "2番目の投稿"]
    )

    dedup_tracker = DedupTracker()
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "test", limit=10, dedup_tracker=dedup_tracker, target_dates=[date(2023, 11, 15)]
    )

    # 2件見つかったが、1件のみ返される（重複除外）
    assert total == 2
    assert len(posts) == 1
    assert posts[0].title == "Duplicate Title"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_top_comments_success(reddit_explorer_service):
    """
    Given: コメントを持つ投稿
    When: _retrieve_top_comments_of_postでコメント取得
    Then: トップコメントが取得され翻訳される
    """
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

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.submission = AsyncMock(return_value=mock_submission)
    reddit_explorer_service._translate_to_japanese = AsyncMock(
        side_effect=["素晴らしい投稿！", "同意します"]
    )

    comments = await reddit_explorer_service._retrieve_top_comments_of_post(post, limit=5)

    assert len(comments) == 2
    assert comments[0]["text"] == "素晴らしい投稿！"
    assert comments[0]["score"] == 50
    assert comments[1]["text"] == "同意します"
    assert comments[1]["score"] == 30

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_top_comments_empty(reddit_explorer_service):
    """
    Given: コメントがない投稿
    When: _retrieve_top_comments_of_postでコメント取得
    Then: 空リストが返される
    """
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

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.submission = AsyncMock(return_value=mock_submission)

    comments = await reddit_explorer_service._retrieve_top_comments_of_post(post, limit=5)

    assert len(comments) == 0

# =============================================================================
# 8. ヘルパーメソッドのユニットテスト
# =============================================================================

@pytest.mark.unit
def test_extract_post_id_from_permalink(reddit_explorer_service):
    """
    Given: Redditパーマリンク
    When: _extract_post_id_from_permalinkでID抽出
    Then: 正しい投稿IDが返される
    """
    # 標準的なパーマリンク
    permalink1 = "https://www.reddit.com/r/python/comments/abc123/test_post/"
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink1) == "abc123"

    # クエリパラメータ付き
    permalink2 = (
        "https://www.reddit.com/r/python/comments/xyz789/test/?utm_source=share"
    )
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink2) == "xyz789"

    # 末尾スラッシュなし
    permalink3 = "/r/test/comments/def456/my_post"
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink3) == "def456"

    # 空文字列
    assert reddit_explorer_service._extract_post_id_from_permalink("") == ""

    # commentsがないパターン
    permalink4 = "/r/test/ghi789"
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink4) == "ghi789"

@pytest.mark.unit
def test_post_sort_key(reddit_explorer_service):
    """
    Given: 投稿レコード
    When: _post_sort_keyでソートキー取得
    Then: popularity_scoreとcreated_atのタプルが返される
    """
    item = {
        "popularity_score": 150.5,
        "created_at": "2024-01-01T12:00:00+00:00",
    }

    popularity, created = reddit_explorer_service._post_sort_key(item)

    assert popularity == 150.5
    assert created.year == 2024
    assert created.month == 1
    assert created.day == 1

@pytest.mark.unit
def test_select_top_posts(reddit_explorer_service):
    """
    Given: 複数の投稿
    When: _select_top_postsで上位を選択
    Then: popularity_scoreの高い順に並び替えられる
    """
    reddit_explorer_service.SUMMARY_LIMIT = 2
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

    selected = reddit_explorer_service._select_top_posts(posts)

    # 上位2件のみ
    assert len(selected) == 2
    # 人気順
    assert selected[0][2].id == "2"  # popularity_score 200
    assert selected[1][2].id == "3"  # popularity_score 150

# =============================================================================
# 9. シリアライズ・ストレージのユニットテスト
# =============================================================================

@pytest.mark.unit
def test_serialize_posts(reddit_explorer_service):
    """
    Given: RedditPost のリスト
    When: _serialize_postsでシリアライズ
    Then: 辞書のリストに変換される
    """
    post1 = RedditPost(
        type="text",
        id="post1",
        title="Test Post 1",
        url=None,
        upvotes=100,
        text="Content 1",
        permalink="/r/test/comments/post1",
        thumbnail="self",
        popularity_score=100.0,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    post1.summary = "Summary 1"
    post1.comments = [{"text": "Comment 1", "score": 10}]

    posts = [("tech", "python", post1)]
    records = reddit_explorer_service._serialize_posts(posts)

    assert len(records) == 1
    assert records[0]["id"] == "post1"
    assert records[0]["category"] == "tech"
    assert records[0]["subreddit"] == "python"
    assert records[0]["title"] == "Test Post 1"
    assert records[0]["url"] is None
    assert records[0]["upvotes"] == 100
    assert records[0]["summary"] == "Summary 1"
    assert records[0]["type"] == "text"
    assert "created_at" in records[0]
    assert "published_at" in records[0]

@pytest.mark.unit
def test_serialize_posts_without_created_at(reddit_explorer_service):
    """
    Given: created_atがないRedditPost
    When: _serialize_postsでシリアライズ
    Then: 現在時刻が使用される
    """
    post = RedditPost(
        type="text",
        id="post1",
        title="Test Post",
        url=None,
        upvotes=100,
        text="Content",
        created_at=None,  # created_atなし
    )

    posts = [("tech", "python", post)]
    records = reddit_explorer_service._serialize_posts(posts)

    assert len(records) == 1
    assert "created_at" in records[0]
    assert "published_at" in records[0]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_empty_posts(reddit_explorer_service):
    """
    Given: 空の投稿リスト
    When: _store_summariesで保存
    Then: 空リストが返される
    """
    result = await reddit_explorer_service._store_summaries([], [date(2024, 1, 1)])

    assert result == []

@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_posts(reddit_explorer_service):
    """
    Given: 投稿リスト
    When: _store_summariesで保存
    Then: ファイルパスのリストが返される
    """
    post = RedditPost(
        type="text",
        id="test123",
        title="Test Post",
        url=None,
        upvotes=100,
        text="Content",
        permalink="/r/test/comments/test123",
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    post.summary = "Summary"

    posts = [("tech", "python", post)]

    with patch(
        "nook.services.reddit_explorer.reddit_explorer.store_daily_snapshots"
    ) as mock_store:
        mock_store.return_value = [
            ("/data/2024-01-01.json", "/data/2024-01-01.md")
        ]

        result = await reddit_explorer_service._store_summaries(posts, [date(2024, 1, 1)])

        assert len(result) == 1
        assert result[0][0] == "/data/2024-01-01.json"
        assert result[0][1] == "/data/2024-01-01.md"
    assert mock_store.called

# =============================================================================
# 10. Markdownレンダリングのユニットテスト
# =============================================================================

@pytest.mark.unit
def test_render_markdown(reddit_explorer_service):
    """
    Given: 投稿レコードのリスト
    When: _render_markdownでMarkdown生成
    Then: 正しいフォーマットのMarkdownが返される
    """
    records = [
        {
            "id": "test123",
            "subreddit": "python",
            "title": "Test Post",
            "permalink": "/r/python/comments/test123",
            "url": "https://example.com",
            "text": "This is a test post content",
            "upvotes": 100,
            "summary": "This is a summary",
        }
    ]

    today = datetime(2024, 1, 1)
    markdown = reddit_explorer_service._render_markdown(records, today)

    assert "# Reddit 人気投稿 (2024-01-01)" in markdown
    assert "## r/python" in markdown
    assert "### [Test Post](/r/python/comments/test123)" in markdown
    assert "リンク: https://example.com" in markdown
    assert "本文: This is a test post content" in markdown
    assert "アップボート数: 100" in markdown
    assert "**要約**:\nThis is a summary" in markdown
    assert "---" in markdown

@pytest.mark.unit
def test_render_markdown_long_text(reddit_explorer_service):
    """
    Given: 長い本文を持つ投稿レコード
    When: _render_markdownでMarkdown生成
    Then: 本文が200文字で切り詰められる
    """
    long_text = "a" * 300  # 300文字のテキスト
    records = [
        {
            "id": "test123",
            "subreddit": "python",
            "title": "Long Post",
            "permalink": "/r/python/comments/test123",
            "url": None,
            "text": long_text,
            "upvotes": 50,
            "summary": "Summary",
        }
    ]

    today = datetime(2024, 1, 1)
    markdown = reddit_explorer_service._render_markdown(records, today)

    assert "本文: " + "a" * 200 + "..." in markdown

@pytest.mark.unit
def test_render_markdown_multiple_subreddits(reddit_explorer_service):
    """
    Given: 複数のサブレディットの投稿レコード
    When: _render_markdownでMarkdown生成
    Then: サブレディットごとにグループ化される
    """
    records = [
        {
            "id": "test1",
            "subreddit": "python",
            "title": "Python Post",
            "permalink": "/r/python/comments/test1",
            "upvotes": 100,
            "summary": "Python summary",
        },
        {
            "id": "test2",
            "subreddit": "javascript",
            "title": "JS Post",
            "permalink": "/r/javascript/comments/test2",
            "upvotes": 50,
            "summary": "JS summary",
        },
    ]

    today = datetime(2024, 1, 1)
    markdown = reddit_explorer_service._render_markdown(records, today)

    assert "## r/python" in markdown
    assert "## r/javascript" in markdown
    assert "### [Python Post](/r/python/comments/test1)" in markdown
    assert "### [JS Post](/r/javascript/comments/test2)" in markdown

# =============================================================================
# 11. Markdownパースのユニットテスト
# =============================================================================

@pytest.mark.unit
def test_parse_markdown(reddit_explorer_service):
    """
    Given: Markdown形式の文字列
    When: _parse_markdownでパース
    Then: 投稿レコードのリストに変換される
    """
    markdown = """# Reddit 人気投稿 (2024-01-01)

## r/python

### [Test Post](/r/python/comments/abc123/test_post)

リンク: https://example.com

本文: This is a test post

アップボート数: 100

**要約**:
This is a summary

---

"""

    records = reddit_explorer_service._parse_markdown(markdown)

    assert len(records) == 1
    assert records[0]["id"] == "abc123"
    assert records[0]["subreddit"] == "python"
    assert records[0]["title"] == "Test Post"
    assert records[0]["url"] == "https://example.com"
    assert records[0]["text"] == "This is a test post"
    assert records[0]["upvotes"] == 100
    assert records[0]["summary"] == "This is a summary"
    assert records[0]["permalink"] == "/r/python/comments/abc123/test_post"

@pytest.mark.unit
def test_parse_markdown_without_optional_fields(reddit_explorer_service):
    """
    Given: オプショナルフィールドなしのMarkdown
    When: _parse_markdownでパース
    Then: 正しくパースされる
    """
    markdown = """# Reddit 人気投稿 (2024-01-01)

## r/test

### [Simple Post](/r/test/comments/xyz789)

アップボート数: 50

**要約**:
Simple summary

---

"""

    records = reddit_explorer_service._parse_markdown(markdown)

    assert len(records) == 1
    assert records[0]["id"] == "xyz789"
    assert records[0]["title"] == "Simple Post"
    assert records[0]["url"] is None
    assert records[0]["text"] == ""
    assert records[0]["upvotes"] == 50
    assert records[0]["summary"] == "Simple summary"

@pytest.mark.unit
def test_parse_markdown_multiple_posts(reddit_explorer_service):
    """
    Given: 複数投稿を含むMarkdown
    When: _parse_markdownでパース
    Then: 全投稿が正しくパースされる
    """
    markdown = """# Reddit 人気投稿 (2024-01-01)

## r/python

### [Post 1](/r/python/comments/abc123)

アップボート数: 100

**要約**:
Summary 1

---

### [Post 2](/r/python/comments/def456)

アップボート数: 50

**要約**:
Summary 2

---

## r/javascript

### [Post 3](/r/javascript/comments/ghi789)

アップボート数: 75

**要約**:
Summary 3

---

"""

    records = reddit_explorer_service._parse_markdown(markdown)

    assert len(records) == 3
    assert records[0]["subreddit"] == "python"
    assert records[0]["title"] == "Post 1"
    assert records[1]["subreddit"] == "python"
    assert records[1]["title"] == "Post 2"
    assert records[2]["subreddit"] == "javascript"
    assert records[2]["title"] == "Post 3"

# =============================================================================
# 12. _load_existing_postsのユニットテスト
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_posts_from_json_list(reddit_explorer_service):
    """
    Given: リスト形式のJSON
    When: _load_existing_postsで読み込み
    Then: リストが返される
    """
    json_data = [
        {"id": "test1", "title": "Post 1"},
        {"id": "test2", "title": "Post 2"},
    ]

    with patch.object(reddit_explorer_service, "load_json", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = json_data

        result = await reddit_explorer_service._load_existing_posts(date(2024, 1, 1))

        assert len(result) == 2
        assert result[0]["id"] == "test1"
        assert result[1]["id"] == "test2"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_posts_from_json_dict(reddit_explorer_service):
    """
    Given: 辞書形式のJSON（サブレディット別）
    When: _load_existing_postsで読み込み
    Then: フラット化されたリストが返される
    """
    json_data = {
        "python": [{"id": "test1", "title": "Python Post"}],
        "javascript": [{"id": "test2", "title": "JS Post"}],
    }

    with patch.object(reddit_explorer_service, "load_json", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = json_data

        result = await reddit_explorer_service._load_existing_posts(date(2024, 1, 1))

        assert len(result) == 2
        assert result[0]["subreddit"] == "python"
        assert result[0]["id"] == "test1"
        assert result[1]["subreddit"] == "javascript"
        assert result[1]["id"] == "test2"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_posts_from_markdown(reddit_explorer_service):
    """
    Given: JSONがなくMarkdownのみ存在
    When: _load_existing_postsで読み込み
    Then: Markdownからパースされたデータが返される
    """
    markdown = """# Reddit 人気投稿 (2024-01-01)

## r/python

### [Test Post](/r/python/comments/test123)

アップボート数: 100

**要約**:
Summary

---

"""

    with patch.object(
            reddit_explorer_service, "load_json", new_callable=AsyncMock
        ) as mock_load_json, patch.object(
            reddit_explorer_service.storage, "load", new_callable=AsyncMock
        ) as mock_load_md:
        mock_load_json.return_value = None
        mock_load_md.return_value = markdown

        result = await reddit_explorer_service._load_existing_posts(date(2024, 1, 1))

        assert len(result) == 1
        assert result[0]["id"] == "test123"
        assert result[0]["subreddit"] == "python"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_posts_no_data(reddit_explorer_service):
    """
    Given: JSONもMarkdownも存在しない
    When: _load_existing_postsで読み込み
    Then: 空リストが返される
    """
    with patch.object(
        reddit_explorer_service, "load_json", new_callable=AsyncMock
    ) as mock_load_json, patch.object(
        reddit_explorer_service.storage, "load", new_callable=AsyncMock
    ) as mock_load_md:
        mock_load_json.return_value = None
        mock_load_md.return_value = None

        result = await reddit_explorer_service._load_existing_posts(date(2024, 1, 1))

        assert len(result) == 0

# =============================================================================
# 13. エッジケーステスト
# =============================================================================

@pytest.mark.unit
def test_post_sort_key_edge_cases(reddit_explorer_service):
    """
    Given: created_atがない、またはpopularity_scoreがない投稿
    When: _post_sort_keyでソートキー取得
    Then: デフォルト値が使用される
    """
    # popularity_scoreなし
    item1 = {"created_at": "2024-01-01T12:00:00+00:00"}
    popularity1, created1 = reddit_explorer_service._post_sort_key(item1)
    assert popularity1 == 0.0

    # created_atなし
    item2 = {"popularity_score": 100.0}
    popularity2, created2 = reddit_explorer_service._post_sort_key(item2)
    assert popularity2 == 100.0
    assert created2.year == 1  # datetime.min

    # 両方なし
    item3 = {}
    popularity3, created3 = reddit_explorer_service._post_sort_key(item3)
    assert popularity3 == 0.0
    assert created3.year == 1

    # Noneの値
    item4 = {"popularity_score": None, "created_at": None}
    popularity4, created4 = reddit_explorer_service._post_sort_key(item4)
    assert popularity4 == 0.0
    assert created4.year == 1

@pytest.mark.unit
def test_extract_post_id_edge_cases(reddit_explorer_service):
    """
    Given: 様々な形式のパーマリンク
    When: _extract_post_id_from_permalinkでID抽出
    Then: 正しくIDが抽出される
    """
    # commentsキーワードなし
    permalink1 = "/r/test/post123"
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink1) == "post123"

    # 複数のスラッシュ
    permalink2 = "/r/test/comments/abc123/title/extra/parts"
    assert reddit_explorer_service._extract_post_id_from_permalink(permalink2) == "abc123"

    # None
    assert reddit_explorer_service._extract_post_id_from_permalink(None) == ""

@pytest.mark.unit
def test_select_top_posts_fewer_than_limit(reddit_explorer_service):
    """
    Given: SUMMARY_LIMIT以下の投稿
    When: _select_top_postsで選択
    Then: 全投稿が返される
    """
    reddit_explorer_service.SUMMARY_LIMIT = 10
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

    posts = [("tech", "python", post1)]

    selected = reddit_explorer_service._select_top_posts(posts)

    # 全投稿が返される
    assert len(selected) == 1

@pytest.mark.unit
def test_run_method(reddit_explorer_service):
    """
    Given: RedditExplorer インスタンス
    When: runメソッドを呼び出す
    Then: collectメソッドが実行される
    """
    with patch.object(reddit_explorer_service, "collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = []

        reddit_explorer_service.run(limit=10)

        # collectが呼ばれたことを確認
        assert mock_collect.called

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_hot_posts_date_filter(reddit_explorer_service, async_generator_helper):
    """
    Given: 対象日付外の投稿
    When: _retrieve_hot_postsで取得
    Then: 対象日付外の投稿はスキップされる (line 392)
    """
    # 対象日付: 2024-01-01
    # 投稿日時: 2023-01-01 (対象外)
    mock_submission = Mock()
    mock_submission.stickied = False
    mock_submission.is_video = False
    mock_submission.is_gallery = False
    mock_submission.poll_data = None
    mock_submission.crosspost_parent = None
    mock_submission.is_self = True
    mock_submission.url = "https://reddit.com/test"
    mock_submission.title = "Old Post"
    mock_submission.selftext = "Content"
    mock_submission.score = 100
    mock_submission.id = "old123"
    mock_submission.permalink = "/r/test/comments/old123"
    mock_submission.thumbnail = "self"
    mock_submission.created_utc = 1672531200  # 2023-01-01 00:00:00 UTC

    mock_subreddit = Mock()
    mock_subreddit.hot = Mock(return_value=async_generator_helper([mock_submission]))

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.subreddit = AsyncMock(return_value=mock_subreddit)
    reddit_explorer_service._translate_to_japanese = AsyncMock(return_value="内容")

    dedup_tracker = DedupTracker()
    # 対象日付は2024-01-01だが、投稿は2023-01-01なのでフィルタされる
    posts, total = await reddit_explorer_service._retrieve_hot_posts(
        "test",
        limit=10,
        dedup_tracker=dedup_tracker,
        target_dates=[date(2024, 1, 1)],
    )

    # 対象日付外の投稿はスキップされる
    assert len(posts) == 0
    assert total == 1  # カウントはされる

@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_top_comments_without_body(reddit_explorer_service):
    """
    Given: body属性がないコメントオブジェクト
    When: _retrieve_top_comments_of_postでコメント取得
    Then: body属性がないコメントはスキップされる (line 454)
    """
    post = RedditPost(
        type="text",
        id="test123",
        title="Test",
        url=None,
        upvotes=100,
        text="Content",
    )

    # body属性があるコメント
    mock_comment_with_body = Mock()
    mock_comment_with_body.body = "Valid comment"
    mock_comment_with_body.score = 50

    # body属性がないコメント（Moreオブジェクトなど）
    mock_comment_without_body = Mock(spec=[])  # bodyを持たない

    mock_submission = Mock()
    mock_submission.comments.replace_more = AsyncMock()
    mock_submission.comments.list = Mock(
        return_value=[mock_comment_with_body, mock_comment_without_body]
    )

    reddit_explorer_service.reddit = Mock()
    reddit_explorer_service.reddit.submission = AsyncMock(return_value=mock_submission)
    reddit_explorer_service._translate_to_japanese = AsyncMock(return_value="有効なコメント")

    comments = await reddit_explorer_service._retrieve_top_comments_of_post(post, limit=5)

    # body属性があるコメントのみ返される
    assert len(comments) == 1
    assert comments[0]["text"] == "有効なコメント"

@pytest.mark.unit
def test_post_sort_key_invalid_date_format(reddit_explorer_service):
    """
    Given: 不正な形式のcreated_at
    When: _post_sort_keyでソートキー取得
    Then: ValueErrorが発生し、datetime.minが使用される (lines 588-589)
    """
    # 不正な日付フォーマット
    item = {"popularity_score": 100.0, "created_at": "invalid-date-format"}

    popularity, created = reddit_explorer_service._post_sort_key(item)

    assert popularity == 100.0
    # 不正な日付はdatetime.minになる
    assert created.year == 1
    assert created.month == 1

@pytest.mark.unit
def test_select_top_posts_empty_list(reddit_explorer_service):
    """
    Given: 空の投稿リスト
    When: _select_top_postsで選択
    Then: 空リストが返される (line 689)
    """
    # 空リスト
    posts = []

    selected = reddit_explorer_service._select_top_posts(posts)

    assert len(selected) == 0
    assert selected == []

@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_titles_error(reddit_explorer_service):
    """
    Given: storage.load_markdownがエラーを発生させる
    When: _load_existing_titlesで既存タイトル読み込み
    Then: エラーをキャッチして空のDedupTrackerを返す (lines 707-710)
    """
    # storage.load_markdownがエラーを発生
    with patch.object(
        reddit_explorer_service.storage, "load_markdown", side_effect=Exception("Load error")
    ):
        tracker = await reddit_explorer_service._load_existing_titles()

        # エラーが発生しても空のトラッカーが返される
        assert tracker is not None
        # 空のトラッカーなので重複チェックはFalseを返す
        is_dup, _ = tracker.is_duplicate("any title")
        assert not is_dup
