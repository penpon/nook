"""
nook/services/hacker_news/hacker_news.py の統合テスト

Hacker Newsサービスのエンドツーエンド動作を検証する統合テストスイート。
データ取得→GPT要約→Storage保存の全体フローとエラーハンドリングをテストします。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.hacker_news.hacker_news import (
    SCORE_THRESHOLD,
    HackerNewsRetriever,
    Story,
)

# =============================================================================
# テスト定数
# =============================================================================

TEST_STORY_ID = 40000000
TEST_STORY_SCORE = 150
TEST_STORY_TIMESTAMP = 1700000000  # 2023-11-14 22:13:20 UTC
TEST_STORY_URL = "https://example.com/test-article"
TEST_STORY_TITLE = "Integration Test Story"
TEST_STORY_TEXT = "This is a test article content for integration testing. " * 10


# =============================================================================
# テストヘルパー関数
# =============================================================================


def create_mock_hn_api_response(story_id: int, **kwargs) -> dict:
    """HN API形式のストーリーレスポンスを作成"""
    return {
        "id": story_id,
        "title": kwargs.get("title", f"Story {story_id}"),
        "score": kwargs.get("score", TEST_STORY_SCORE),
        "time": kwargs.get("time", TEST_STORY_TIMESTAMP),
        "url": kwargs.get("url", f"https://example.com/story{story_id}"),
        "type": "story",
    }


def create_mock_http_response(text: str = TEST_STORY_TEXT, status_code: int = 200) -> Mock:
    """HTTPレスポンスのモックオブジェクトを作成"""
    return Mock(
        text=text,
        content=text.encode("utf-8"),
        status_code=status_code,
        headers={"content-type": "text/html; charset=utf-8"},
    )


# =============================================================================
# 統合テスト: フルデータフロー
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_hacker_news_to_storage(tmp_path, mock_env_vars):
    """
    Given: HackerNewsRetrieverサービスインスタンス
    When: collect()メソッドを実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功する
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "hacker_news_data")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    service = HackerNewsRetriever(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のStoryオブジェクトを作成
    test_stories = [
        Story(
            title="Test Story 1 - Integration Test",
            score=200,
            url="https://example.com/story1",
            text="This is test content 1 for integration testing. " * 20,  # 十分な長さのテキスト
            created_at=datetime.now(UTC),
        ),
        Story(
            title="Test Story 2 - Integration Test",
            score=180,
            url="https://example.com/story2",
            text="This is test content 2 for integration testing. " * 20,
            created_at=datetime.now(UTC),
        ),
        Story(
            title="Test Story 3 - Integration Test",
            score=160,
            url="https://example.com/story3",
            text="This is test content 3 for integration testing. " * 20,
            created_at=datetime.now(UTC),
        ),
    ]

    # _get_top_storiesメソッドとGPTクライアントをモック
    with (
        patch.object(service, "_get_top_stories", new_callable=AsyncMock) as mock_get_stories,
        patch.object(service.gpt_client, "generate_async", new_callable=AsyncMock) as mock_gpt,
    ):
        # _get_top_storiesはテストストーリーを返す（要約はまだ生成されていない）
        mock_get_stories.return_value = test_stories

        # GPT要約のモック
        mock_gpt.return_value = "テスト要約: この記事は統合テストの一環として作成されました。"

        # 3. データ収集実行
        result = await service.collect(limit=3)

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

        assert len(saved_data) >= 3, f"期待: 3件以上のストーリー, 実際: {len(saved_data)}件"

        # 最初のストーリーの検証
        first_story = saved_data[0]
        assert "title" in first_story, "titleフィールドが存在しません"
        assert "url" in first_story, "urlフィールドが存在しません"
        assert "text" in first_story, "textフィールドが存在しません"

        # ストーリーのタイトルが正しいことを確認
        story_titles = [s["title"] for s in saved_data]
        assert "Test Story 1 - Integration Test" in story_titles, "テストストーリー1が保存されていません"
        assert "Test Story 2 - Integration Test" in story_titles, "テストストーリー2が保存されていません"
        assert "Test Story 3 - Integration Test" in story_titles, "テストストーリー3が保存されていません"


# =============================================================================
# 統合テスト: ネットワークエラーハンドリング
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_hacker_news(tmp_path, mock_env_vars):
    """
    Given: ネットワークエラーが発生する状況
    When: collect()メソッドを実行
    Then: RetryExceptionが発生する（retry decoratorによる3回のリトライ後）
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "hacker_news_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    service = HackerNewsRetriever(storage_dir=storage_dir)

    # HTTP clientを初期化
    await service.setup_http_client()

    # 2. モック設定: ネットワークエラーをシミュレート
    with patch.object(service.http_client, "get", new_callable=AsyncMock) as mock_http_get:
        # 接続エラーを発生させる
        mock_http_get.side_effect = httpx.ConnectError("Connection failed")

        # 3. エラーハンドリング確認: RetryExceptionが発生することを検証
        from nook.common.exceptions import RetryException

        with pytest.raises(RetryException) as exc_info:
            await service.collect(limit=3)
        # リトライデコレータにより3回リトライ後にRetryExceptionが発生する
        assert "Failed after 3 attempts" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)


# =============================================================================
# 統合テスト: GPT APIエラーハンドリングとフォールバック
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_hacker_news(tmp_path, mock_env_vars):
    """
    Given: GPT APIエラーが発生する状況
    When: collect()メソッドを実行
    Then: フォールバック処理が動作し、要約なしでもデータが保存される（データ保存は必須）
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "hacker_news_gpt_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)
    service = HackerNewsRetriever(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のStoryオブジェクトを作成
    test_stories = [
        Story(
            title="Story without GPT summary 1",
            score=250,
            url="https://example.com/nogpt1",
            text="This is test content without GPT summary. " * 20,
            created_at=datetime.now(UTC),
        ),
        Story(
            title="Story without GPT summary 2",
            score=220,
            url="https://example.com/nogpt2",
            text="Another test content without GPT summary. " * 20,
            created_at=datetime.now(UTC),
        ),
    ]

    with (
        patch.object(service, "_get_top_stories", new_callable=AsyncMock) as mock_get_stories,
        patch.object(service.gpt_client, "generate_async", new_callable=AsyncMock) as mock_gpt,
    ):
        # _get_top_storiesはテストストーリーを返す
        mock_get_stories.return_value = test_stories

        # GPT APIエラーをシミュレート
        mock_gpt.side_effect = Exception("API rate limit exceeded")

        # 3. データ収集実行（GPTエラーがあっても処理は継続）
        result = await service.collect(limit=2)

        # 4. 検証: データは必ず保存されるべき（GPTエラーがあっても）
        assert result is not None, "GPTエラー時でもresultはNoneであってはいけません"
        assert len(result) > 0, "GPTエラーがあってもデータは保存されるべきです"

        saved_json_path, saved_md_path = result[0]
        assert Path(saved_json_path).exists(), f"JSONファイルが保存されていません: {saved_json_path}"

        # 5. 保存内容確認
        import json

        with open(saved_json_path) as f:
            saved_data = json.load(f)

        # データは取得されている
        assert len(saved_data) >= 1, "最低1件のストーリーが保存されるべきです"
        for story in saved_data:
            # 必須フィールドの確認
            assert "title" in story, "titleフィールドが存在しません"
            assert "text" in story, "textフィールドが存在しません"
            assert "url" in story, "urlフィールドが存在しません"

            # summaryフィールドの検証
            assert "summary" in story, "summaryフィールドが存在しません"
            assert story["summary"] is not None, "summaryはNoneであってはいけません"

            # GPTエラー時のフォールバック値を検証
            # 空文字列、またはエラーメッセージ「要約の生成中にエラーが発生しました: {詳細}」のいずれか
            assert (
                isinstance(story["summary"], str)
            ), f"summaryは文字列であるべきです: {type(story['summary'])}"
            # フォールバック動作を確認（空文字列か特定のエラーメッセージで始まる）
            is_valid_fallback = (
                story["summary"] == ""
                or story["summary"].startswith("要約の生成中にエラーが発生しました")
            )
            assert is_valid_fallback, f"予期しないsummary値: {story['summary']}"
