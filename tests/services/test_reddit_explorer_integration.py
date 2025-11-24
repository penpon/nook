"""Reddit Explorer統合テスト

テスト観点:
- データ取得 → GPT要約 → Storage保存の全体フロー
- ネットワークエラーハンドリング
- GPT APIエラーハンドリングとフォールバック

注意: RedditExplorerはasyncprawを直接使用しているため、
完全な統合テストではなく、主要なコンポーネントをモック化した
エンドツーエンドテストとして実装しています。
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.reddit_explorer.reddit_explorer import RedditExplorer, RedditPost

# =============================================================================
# 統合テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_reddit_explorer_to_storage(tmp_path, mock_env_vars):
    """Given: RedditExplorerサービスインスタンスと適切にモックされた外部依存
    When: collect()を実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功する
    """
    # 1. サービス初期化
    mock_logger = Mock()
    with patch("nook.common.base_service.setup_logger", return_value=mock_logger):
        service = RedditExplorer(storage_dir=str(tmp_path))
        service.logger = mock_logger

    # 2. 主要なメソッドをモックして統合テスト実行
    #    _retrieve_hot_posts, _retrieve_top_comments_of_post, _summarize_reddit_postをモック
    #    これにより、asyncprawの複雑な依存を避けつつ、フロー全体をテスト

    # 固定のUTC日時を使用（タイムゾーン不整合を回避）
    test_datetime = datetime(2024, 11, 14, 12, 0, 0, tzinfo=UTC)
    test_date = test_datetime.date()

    mock_post = RedditPost(
        type="text",
        id="test123",
        title="Test Reddit Post",
        url=None,
        upvotes=100,
        text="Test content",
        permalink="https://reddit.com/r/test/comments/test123/",
        created_at=test_datetime,
    )

    with (
        patch.object(service, "setup_http_client", new_callable=AsyncMock),
        patch("asyncpraw.Reddit") as mock_reddit,
        patch.object(
            service,
            "_retrieve_hot_posts",
            new_callable=AsyncMock,
            return_value=([mock_post], 1),
        ) as mock_retrieve,
        patch.object(
            service,
            "_retrieve_top_comments_of_post",
            new_callable=AsyncMock,
            return_value=[{"text": "Test comment", "score": 50}],
        ),
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # asyncprawのコンテキストマネージャをモック
        mock_reddit_instance = AsyncMock()
        mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance
        # GPT要約モック
        mock_gpt.return_value = "テスト要約"

        # 3. データ収集実行（UTC日付を明示的に指定）
        result = await service.collect(limit=10, target_dates=[test_date])

        # 4. 検証: データ取得確認
        assert len(result) > 0, "データが取得できていません"
        json_path, md_path = result[0]

        # 5. 検証: ファイルが作成されたことを確認
        assert Path(json_path).exists(), f"JSONファイルが作成されていません: {json_path}"
        assert Path(md_path).exists(), f"Markdownファイルが作成されていません: {md_path}"

        # 6. 検証: 主要なメソッドが呼ばれたことを確認
        assert mock_retrieve.called, "投稿取得メソッドが呼ばれていません"
        assert mock_gpt.called, "GPT要約が実行されていません"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_reddit_explorer(tmp_path, mock_env_vars):
    """Given: ネットワークエラーが発生する状況
    When: collect()を実行
    Then: 適切なエラーハンドリングがされ、空の結果が返る
    """
    # 1. サービス初期化（ロガーのモックも設定）
    mock_logger = Mock()
    with patch("nook.common.base_service.setup_logger", return_value=mock_logger):
        service = RedditExplorer(storage_dir=str(tmp_path))
        service.logger = mock_logger

    # 2. モック設定（ネットワークエラー）
    with (
        patch.object(service, "setup_http_client", new_callable=AsyncMock),
        patch("asyncpraw.Reddit") as mock_reddit,
        patch.object(
            service,
            "_retrieve_hot_posts",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection failed"),
        ),
    ):
        # asyncprawのコンテキストマネージャをモック
        mock_reddit_instance = AsyncMock()
        mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

        # 3. エラーハンドリング確認
        # ネットワークエラーはキャッチされ、空の結果が返る
        # 固定のUTC日時を使用（再現性のため）
        test_datetime = datetime(2024, 11, 14, 12, 0, 0, tzinfo=UTC)
        test_date = test_datetime.date()
        result = await service.collect(limit=10, target_dates=[test_date])

        # 4. 検証: 空の結果が返ること
        assert result == [], "ネットワークエラー時は空の結果が返るべき"

        # 5. 検証: エラーがログに記録されること
        assert mock_logger.error.called, "エラーがログに記録されるべき"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_reddit_explorer(tmp_path, mock_env_vars):
    """Given: GPT APIエラーが発生する状況
    When: collect()を実行
    Then: フォールバック処理が動作し、要約にエラーメッセージが設定される
    """
    # 1. サービス初期化（ロガーのモックも設定）
    mock_logger = Mock()
    with patch("nook.common.base_service.setup_logger", return_value=mock_logger):
        service = RedditExplorer(storage_dir=str(tmp_path))
        service.logger = mock_logger

    # 2. モック設定
    # 固定のUTC日時を使用（タイムゾーン不整合を回避）
    test_datetime = datetime(2024, 11, 14, 12, 0, 0, tzinfo=UTC)
    test_date = test_datetime.date()

    mock_post = RedditPost(
        type="text",
        id="test123",
        title="Test Reddit Post",
        url=None,
        upvotes=100,
        text="Test content",
        permalink="https://reddit.com/r/test/comments/test123/",
        created_at=test_datetime,
    )

    with (
        patch.object(service, "setup_http_client", new_callable=AsyncMock),
        patch("asyncpraw.Reddit") as mock_reddit,
        patch.object(
            service,
            "_retrieve_hot_posts",
            new_callable=AsyncMock,
            return_value=([mock_post], 1),
        ),
        patch.object(
            service,
            "_retrieve_top_comments_of_post",
            new_callable=AsyncMock,
            return_value=[{"text": "Test comment", "score": 50}],
        ),
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # asyncprawのコンテキストマネージャをモック
        mock_reddit_instance = AsyncMock()
        mock_reddit.return_value.__aenter__.return_value = mock_reddit_instance

        # GPT APIエラーをシミュレート（翻訳と要約の両方）
        mock_gpt.side_effect = Exception("API rate limit exceeded")

        # 3. フォールバック動作確認（UTC日付を明示的に指定）
        result = await service.collect(limit=10, target_dates=[test_date])

        # 4. 検証: 要約失敗でもデータは取得される
        assert len(result) > 0, "GPTエラー時でもデータが取得されるべき"

        # 5. 検証: 保存されたデータを読み込んで確認
        json_path, _ = result[0]

        with open(json_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        # データが存在することを確認
        assert len(saved_data) > 0, "保存されたデータが存在しない"

        # summaryフィールドにエラーメッセージが含まれることを確認
        first_item = saved_data[0]
        assert "summary" in first_item, "summaryフィールドが存在しない"
        # エラーメッセージが入っている
        summary = first_item["summary"]
        assert "エラー" in summary, f"要約エラー時の適切なメッセージが入っていない: {summary}"

        # 6. 検証: エラーがログに記録されること
        assert mock_logger.error.called, "エラーがログに記録されるべき"
