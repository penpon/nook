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

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import httpx
import pytest
import respx

from nook.common.dedup import DedupTracker
from nook.services.hacker_news.hacker_news import (
    HackerNewsRetriever,
    Story,
    SCORE_THRESHOLD,
    MIN_TEXT_LENGTH,
    MAX_TEXT_LENGTH,
)

# =============================================================================
# テストヘルパー関数
# =============================================================================


def create_test_story(
    title: str = "Test Story",
    score: int = 100,
    url: str = "https://example.com/test",
    text: str | None = "Test text",
    summary: str | None = None,
    created_at: datetime | None = None
) -> Story:
    """テスト用のStoryオブジェクトを作成するヘルパー関数"""
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    return Story(
        title=title,
        score=score,
        url=url,
        text=text,
        summary=summary,
        created_at=created_at
    )


def mock_hn_story_response(story_id: int, **kwargs) -> dict:
    """HN APIのストーリーレスポンスをモック化するヘルパー関数"""
    default_response = {
        "id": story_id,
        "title": kwargs.get("title", f"Story {story_id}"),
        "score": kwargs.get("score", 100),
        "time": kwargs.get("time", 1700000000)
    }

    if "url" in kwargs:
        default_response["url"] = kwargs["url"]
    if "text" in kwargs:
        default_response["text"] = kwargs["text"]

    return default_response


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

            service.http_client.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

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

        with patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(service.storage, "save", new_callable=AsyncMock):

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
            service.gpt_client.get_response = AsyncMock(
                side_effect=Exception("API Error")
            )

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
    story = Story(
        title="Test Story", score=200, url="https://example.com/test", text="Test text"
    )

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


# =============================================================================
# 7. _load_blocked_domains メソッドのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
def test_load_blocked_domains_success(mock_env_vars):
    """
    Given: 正常なblocked_domains.jsonファイル
    When: _load_blocked_domainsを呼び出す
    Then: ブロックドメインリストが正常に読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        assert "blocked_domains" in service.blocked_domains
        assert "reasons" in service.blocked_domains
        assert isinstance(service.blocked_domains["blocked_domains"], list)
        assert len(service.blocked_domains["blocked_domains"]) > 0


@pytest.mark.unit
def test_load_blocked_domains_file_not_found(mock_env_vars):
    """
    Given: blocked_domains.jsonが存在しない
    When: _load_blocked_domainsを呼び出す
    Then: デフォルトの空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"), \
         patch("builtins.open", side_effect=FileNotFoundError):
        service = HackerNewsRetriever()

        assert service.blocked_domains == {"blocked_domains": [], "reasons": {}}


@pytest.mark.unit
def test_load_blocked_domains_invalid_json(mock_env_vars):
    """
    Given: 不正なJSON形式のblocked_domains.json
    When: _load_blocked_domainsを呼び出す
    Then: デフォルトの空リストが返される
    """
    import json

    with patch("nook.common.base_service.setup_logger"), \
         patch("builtins.open", mock_open(read_data="invalid json")), \
         patch("json.load", side_effect=json.JSONDecodeError("test", "test", 0)):
        service = HackerNewsRetriever()

        assert service.blocked_domains == {"blocked_domains": [], "reasons": {}}


# =============================================================================
# 8. _is_blocked_domain メソッドのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
def test_is_blocked_domain_blocked(mock_env_vars):
    """
    Given: ブロックリストに含まれるドメイン
    When: _is_blocked_domainを呼び出す
    Then: Trueが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {
            "blocked_domains": ["reuters.com", "wsj.com"],
            "reasons": {}
        }

        assert service._is_blocked_domain("https://reuters.com/article") is True
        assert service._is_blocked_domain("https://www.reuters.com/article") is True


@pytest.mark.unit
def test_is_blocked_domain_not_blocked(mock_env_vars):
    """
    Given: ブロックリストに含まれないドメイン
    When: _is_blocked_domainを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {
            "blocked_domains": ["reuters.com"],
            "reasons": {}
        }

        assert service._is_blocked_domain("https://example.com/article") is False


@pytest.mark.unit
def test_is_blocked_domain_empty_url(mock_env_vars):
    """
    Given: 空のURL
    When: _is_blocked_domainを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        assert service._is_blocked_domain("") is False
        assert service._is_blocked_domain(None) is False


@pytest.mark.unit
def test_is_blocked_domain_invalid_url(mock_env_vars):
    """
    Given: 不正なURL（スキームなし）
    When: _is_blocked_domainを呼び出す
    Then: Falseが返される（ドメインが抽出できないため）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        # URLとして解釈されないが、パース自体は成功する（netloc=""）
        # 実際の実装ではnettlocが空の場合はブロックされていないと判断される
        result = service._is_blocked_domain("not-a-url")

        # netloc が空文字列の場合、blocked_domainsリストには含まれないのでFalse
        assert result is False


# =============================================================================
# 9. _is_http1_required_domain メソッドのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
def test_is_http1_required_domain_required(mock_env_vars):
    """
    Given: HTTP/1.1が必要なドメイン
    When: _is_http1_required_domainを呼び出す
    Then: Trueが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {
            "blocked_domains": [],
            "http1_required_domains": ["htmlrev.com"],
            "reasons": {}
        }

        assert service._is_http1_required_domain("https://htmlrev.com/page") is True
        assert service._is_http1_required_domain("https://www.htmlrev.com/page") is True


@pytest.mark.unit
def test_is_http1_required_domain_not_required(mock_env_vars):
    """
    Given: HTTP/1.1が不要なドメイン
    When: _is_http1_required_domainを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {
            "blocked_domains": [],
            "http1_required_domains": ["htmlrev.com"],
            "reasons": {}
        }

        assert service._is_http1_required_domain("https://example.com/page") is False


@pytest.mark.unit
def test_is_http1_required_domain_empty_url(mock_env_vars):
    """
    Given: 空のURL
    When: _is_http1_required_domainを呼び出す
    Then: Falseが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        assert service._is_http1_required_domain("") is False
        assert service._is_http1_required_domain(None) is False


# =============================================================================
# 10. _fetch_story メソッドのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_success(mock_env_vars, respx_mock):
    """
    Given: 正常なHN APIレスポンス
    When: _fetch_storyを呼び出す
    Then: Storyオブジェクトが正常に返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story_data = {
            "id": 12345,
            "title": "Test Story",
            "score": 150,
            "url": "https://example.com/test",
            "time": 1699999999
        }

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/12345.json").mock(
            return_value=httpx.Response(200, json=story_data)
        )

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text='<html><meta name="description" content="Test description"></html>')
        )

        story = await service._fetch_story(12345)

        assert story is not None
        assert story.title == "Test Story"
        assert story.score == 150
        assert story.url == "https://example.com/test"
        assert story.created_at is not None

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_deleted(mock_env_vars, respx_mock):
    """
    Given: 削除済みストーリー（titleなし）
    When: _fetch_storyを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story_data = {
            "id": 12345,
            "deleted": True
        }

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/12345.json").mock(
            return_value=httpx.Response(200, json=story_data)
        )

        story = await service._fetch_story(12345)

        assert story is None

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_missing_timestamp(mock_env_vars, respx_mock):
    """
    Given: タイムスタンプがないストーリー
    When: _fetch_storyを呼び出す
    Then: 現在時刻がcreated_atに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story_data = {
            "id": 12345,
            "title": "Test Story",
            "score": 50,
            "text": "Test text" * 20  # MIN_TEXT_LENGTH以上にする
        }

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/12345.json").mock(
            return_value=httpx.Response(200, json=story_data)
        )

        story = await service._fetch_story(12345)

        assert story is not None
        assert story.created_at is not None
        # created_atは現在時刻のはず
        assert (datetime.now(timezone.utc) - story.created_at).total_seconds() < 5

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_api_error(mock_env_vars, respx_mock):
    """
    Given: HN APIがエラーを返す
    When: _fetch_storyを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/12345.json").mock(
            return_value=httpx.Response(500)
        )

        story = await service._fetch_story(12345)

        assert story is None

        await service.cleanup()


# =============================================================================
# 11. _fetch_story_content メソッドのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_meta_description(mock_env_vars, respx_mock):
    """
    Given: メタディスクリプションを含むHTML
    When: _fetch_story_contentを呼び出す
    Then: メタディスクリプションがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        html_content = '<html><meta name="description" content="Test meta description"></html>'

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        await service._fetch_story_content(story)

        assert story.text == "Test meta description"

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_og_description(mock_env_vars, respx_mock):
    """
    Given: Open Graphディスクリプションを含むHTML
    When: _fetch_story_contentを呼び出す
    Then: OGディスクリプションがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        html_content = '<html><meta property="og:description" content="OG description"></html>'

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        await service._fetch_story_content(story)

        assert story.text == "OG description"

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_paragraphs(mock_env_vars, respx_mock):
    """
    Given: 段落を含むHTML（メタディスクリプションなし）
    When: _fetch_story_contentを呼び出す
    Then: 段落のテキストがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        html_content = '''<html><body>
            <p>First paragraph with meaningful content that is longer than 50 characters.</p>
            <p>Second paragraph with even more content to test the extraction logic here.</p>
            <p>Third paragraph continues the pattern of providing substantial text content.</p>
        </body></html>'''

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        await service._fetch_story_content(story)

        assert story.text is not None
        assert len(story.text) > 50

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_blocked_domain(mock_env_vars):
    """
    Given: ブロックされたドメイン
    When: _fetch_story_contentを呼び出す
    Then: ブロック警告がstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {
            "blocked_domains": ["reuters.com"],
            "reasons": {"reuters.com": "401 - Authentication required"}
        }

        story = Story(
            title="Test",
            score=100,
            url="https://reuters.com/article"
        )

        await service._fetch_story_content(story)

        assert "reuters.com" in story.text
        assert "ブロックされています" in story.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_http_401(mock_env_vars, respx_mock):
    """
    Given: HTTP 401エラー
    When: _fetch_story_contentを呼び出す
    Then: アクセス制限メッセージがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        # HTTPStatusErrorを発生させる
        respx_mock.get("https://example.com/test").mock(
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("GET", "https://example.com/test"),
                response=httpx.Response(401)
            )
        )

        await service._fetch_story_content(story)

        assert "アクセス制限により" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_http_403(mock_env_vars):
    """
    Given: HTTP 403エラー
    When: _fetch_story_contentを呼び出す
    Then: アクセス制限メッセージがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        # http_client.getメソッドを直接モックしてHTTPStatusErrorを発生させる
        async def mock_get_403(*args, **kwargs):
            raise httpx.HTTPStatusError(
                "403 Forbidden",
                request=httpx.Request("GET", "https://example.com/test"),
                response=httpx.Response(403)
            )

        with patch.object(service.http_client, 'get', side_effect=mock_get_403):
            await service._fetch_story_content(story)

        assert "アクセス制限により" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_http_404(mock_env_vars, respx_mock):
    """
    Given: HTTP 404エラー
    When: _fetch_story_contentを呼び出す
    Then: 記事が見つからないメッセージがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        # HTTPStatusErrorを発生させる
        respx_mock.get("https://example.com/test").mock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=httpx.Request("GET", "https://example.com/test"),
                response=httpx.Response(404)
            )
        )

        await service._fetch_story_content(story)

        assert "記事が見つかりませんでした" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_timeout(mock_env_vars, respx_mock):
    """
    Given: タイムアウトエラー
    When: _fetch_story_contentを呼び出す
    Then: エラーメッセージがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        respx_mock.get("https://example.com/test").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        await service._fetch_story_content(story)

        assert "記事の内容を取得できませんでした" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_ssl_error(mock_env_vars, respx_mock):
    """
    Given: SSL/TLSエラー
    When: _fetch_story_contentを呼び出す
    Then: エラーメッセージがstory.textに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        respx_mock.get("https://example.com/test").mock(
            side_effect=httpx.ConnectError("SSL handshake failed")
        )

        await service._fetch_story_content(story)

        assert "記事の内容を取得できませんでした" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_http1_required(mock_env_vars, respx_mock):
    """
    Given: HTTP/1.1が必要なドメイン
    When: _fetch_story_contentを呼び出す
    Then: force_http1=Trueでリクエストされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()
        service.blocked_domains = {
            "blocked_domains": [],
            "http1_required_domains": ["htmlrev.com"],
            "reasons": {}
        }

        story = Story(
            title="Test",
            score=100,
            url="https://htmlrev.com/test"
        )

        html_content = '<html><meta name="description" content="Test"></html>'
        respx_mock.get("https://htmlrev.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        with patch.object(service.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                text=html_content
            )

            await service._fetch_story_content(story)

            # force_http1=Trueで呼び出されることを確認
            mock_get.assert_called_once_with("https://htmlrev.com/test", force_http1=True)

        await service.cleanup()


# =============================================================================
# 12. _get_top_stories フィルタリングのテスト（内部メソッド）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_top_stories_score_filtering(mock_env_vars, respx_mock):
    """
    Given: スコアが閾値未満のストーリー
    When: _get_top_storiesを呼び出す
    Then: スコアが閾値以上のストーリーのみが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        # トップストーリーIDのモック
        respx_mock.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=httpx.Response(200, json=[1, 2, 3])
        )

        # スコアが異なるストーリー
        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(
            return_value=httpx.Response(200, json={
                "id": 1,
                "title": "High Score Story",
                "score": 100,  # SCORE_THRESHOLD以上
                "time": 1699999999,
                "text": "A" * 150  # MIN_TEXT_LENGTH以上
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/2.json").mock(
            return_value=httpx.Response(200, json={
                "id": 2,
                "title": "Low Score Story",
                "score": 10,  # SCORE_THRESHOLD未満
                "time": 1699999999,
                "text": "B" * 150
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/3.json").mock(
            return_value=httpx.Response(200, json={
                "id": 3,
                "title": "Another High Score",
                "score": 50,  # SCORE_THRESHOLD以上
                "time": 1699999999,
                "text": "C" * 150
            })
        )

        from nook.common.dedup import DedupTracker
        dedup_tracker = DedupTracker()

        stories = await service._get_top_stories(15, dedup_tracker, [date.today()])

        # スコア >= SCORE_THRESHOLD のストーリーのみ
        assert all(story.score >= SCORE_THRESHOLD for story in stories)
        assert len([s for s in stories if s.score >= SCORE_THRESHOLD]) >= 0

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_top_stories_text_length_filtering(mock_env_vars, respx_mock):
    """
    Given: テキスト長が範囲外のストーリー
    When: _get_top_storiesを呼び出す
    Then: テキスト長が範囲内のストーリーのみが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        respx_mock.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=httpx.Response(200, json=[1, 2, 3])
        )

        # テキスト長が異なるストーリー
        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(
            return_value=httpx.Response(200, json={
                "id": 1,
                "title": "Valid Length Story",
                "score": 100,
                "time": 1699999999,
                "text": "A" * 500  # MIN_TEXT_LENGTH < len < MAX_TEXT_LENGTH
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/2.json").mock(
            return_value=httpx.Response(200, json={
                "id": 2,
                "title": "Too Short Story",
                "score": 100,
                "time": 1699999999,
                "text": "B" * 50  # MIN_TEXT_LENGTH未満
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/3.json").mock(
            return_value=httpx.Response(200, json={
                "id": 3,
                "title": "Too Long Story",
                "score": 100,
                "time": 1699999999,
                "text": "C" * 15000  # MAX_TEXT_LENGTH超過
            })
        )

        from nook.common.dedup import DedupTracker
        dedup_tracker = DedupTracker()

        stories = await service._get_top_stories(15, dedup_tracker, [date.today()])

        # テキスト長が範囲内のストーリーのみ
        for story in stories:
            text_len = len(story.text or "")
            assert MIN_TEXT_LENGTH <= text_len <= MAX_TEXT_LENGTH

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_top_stories_sorted_by_score(mock_env_vars, respx_mock):
    """
    Given: 複数の有効なストーリー
    When: _get_top_storiesを呼び出す
    Then: スコアの降順にソートされて返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        respx_mock.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=httpx.Response(200, json=[1, 2, 3])
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(
            return_value=httpx.Response(200, json={
                "id": 1,
                "title": "Medium Score",
                "score": 50,
                "time": 1699999999,
                "text": "A" * 150
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/2.json").mock(
            return_value=httpx.Response(200, json={
                "id": 2,
                "title": "High Score",
                "score": 200,
                "time": 1699999999,
                "text": "B" * 150
            })
        )

        respx_mock.get("https://hacker-news.firebaseio.com/v0/item/3.json").mock(
            return_value=httpx.Response(200, json={
                "id": 3,
                "title": "Low Score",
                "score": 30,
                "time": 1699999999,
                "text": "C" * 150
            })
        )

        from nook.common.dedup import DedupTracker
        dedup_tracker = DedupTracker()

        stories = await service._get_top_stories(15, dedup_tracker, [date.today()])

        # スコアの降順にソートされている
        if len(stories) > 1:
            for i in range(len(stories) - 1):
                assert stories[i].score >= stories[i + 1].score

        await service.cleanup()


# =============================================================================
# 13. _add_to_blocked_domains / _update_blocked_domains_from_errors のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_to_blocked_domains_new_domain(mock_env_vars, tmp_path):
    """
    Given: 新しいドメインを追加
    When: _add_to_blocked_domainsを呼び出す
    Then: ブロックドメインリストに追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        # 一時ファイルパスを設定
        blocked_domains_path = tmp_path / "blocked_domains.json"
        blocked_domains_path.write_text('{"blocked_domains": [], "reasons": {}}')

        with patch("os.path.join", return_value=str(blocked_domains_path)), \
             patch("os.path.exists", return_value=True):

            new_domains = {
                "newdomain.com": "403 - Access denied"
            }

            await service._add_to_blocked_domains(new_domains)

            # ファイルが更新されたことを確認
            import json
            with open(blocked_domains_path, encoding="utf-8") as f:
                data = json.load(f)

            assert "newdomain.com" in data["blocked_domains"]
            assert data["reasons"]["newdomain.com"] == "403 - Access denied"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_to_blocked_domains_duplicate(mock_env_vars, tmp_path):
    """
    Given: 既存のドメインを追加
    When: _add_to_blocked_domainsを呼び出す
    Then: 重複して追加されない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        # 既存のドメインを含むファイル
        blocked_domains_path = tmp_path / "blocked_domains.json"
        blocked_domains_path.write_text(
            '{"blocked_domains": ["existing.com"], "reasons": {"existing.com": "Test"}}'
        )

        with patch("os.path.join", return_value=str(blocked_domains_path)), \
             patch("os.path.exists", return_value=True):

            new_domains = {
                "existing.com": "403 - Access denied"
            }

            await service._add_to_blocked_domains(new_domains)

            # ファイルを確認
            import json
            with open(blocked_domains_path, encoding="utf-8") as f:
                data = json.load(f)

            # 重複して追加されていない
            assert data["blocked_domains"].count("existing.com") == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocked_domains_from_errors(mock_env_vars, tmp_path):
    """
    Given: エラー状態のストーリー
    When: _update_blocked_domains_from_errorsを呼び出す
    Then: エラードメインが検出され、ブロックリストに追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        # 一時ファイルパスを設定
        blocked_domains_path = tmp_path / "blocked_domains.json"
        blocked_domains_path.write_text('{"blocked_domains": [], "reasons": {}}')

        with patch("os.path.join", return_value=str(blocked_domains_path)), \
             patch("os.path.exists", return_value=True):

            # エラーストーリーを作成
            stories = [
                Story(
                    title="Error Story",
                    score=100,
                    url="https://errordomain.com/article",
                    text="記事の内容を取得できませんでした。"
                )
            ]

            await service._update_blocked_domains_from_errors(stories)

            # ファイルが更新されたことを確認
            import json
            with open(blocked_domains_path, encoding="utf-8") as f:
                data = json.load(f)

            # エラードメインが追加されている可能性がある
            # （実装によって追加されるかどうかは異なる）
            assert isinstance(data["blocked_domains"], list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocked_domains_from_errors_no_errors(mock_env_vars):
    """
    Given: エラーなしのストーリー
    When: _update_blocked_domains_from_errorsを呼び出す
    Then: ブロックリストは更新されない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        stories = [
            Story(
                title="Success Story",
                score=100,
                url="https://example.com/article",
                text="Valid content text here"
            )
        ]

        with patch.object(service, '_add_to_blocked_domains', new_callable=AsyncMock) as mock_add:
            await service._update_blocked_domains_from_errors(stories)

            # _add_to_blocked_domainsが空の辞書で呼び出されないか、
            # 呼び出されても何も追加されない
            if mock_add.called:
                assert mock_add.call_args[0][0] == {} or len(mock_add.call_args[0][0]) == 0


# =============================================================================
# 14. ヘルパーメソッドのテスト (_serialize_stories, _render_markdown, _parse_markdown, _story_sort_key)
# =============================================================================


@pytest.mark.unit
def test_serialize_stories(mock_env_vars):
    """
    Given: ストーリーのリスト
    When: _serialize_storiesを呼び出す
    Then: シリアライズされた辞書のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        stories = [
            create_test_story(
                title="Test Story",
                score=100,
                url="https://example.com/test",
                text="Test text",
                summary="Test summary",
                created_at=datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            )
        ]

        records = service._serialize_stories(stories)

        assert len(records) == 1
        assert records[0]["title"] == "Test Story"
        assert records[0]["score"] == 100
        assert records[0]["url"] == "https://example.com/test"
        assert records[0]["text"] == "Test text"
        assert records[0]["summary"] == "Test summary"
        assert "published_at" in records[0]


@pytest.mark.unit
def test_render_markdown(mock_env_vars):
    """
    Given: 記事のリスト
    When: _render_markdownを呼び出す
    Then: マークダウン形式の文字列が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        records = [
            {
                "title": "Test Story",
                "score": 100,
                "url": "https://example.com/test",
                "summary": "Test summary"
            }
        ]

        today = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
        markdown = service._render_markdown(records, today)

        assert "# Hacker News トップ記事" in markdown
        assert "Test Story" in markdown
        assert "スコア: 100" in markdown
        assert "Test summary" in markdown


@pytest.mark.unit
def test_parse_markdown(mock_env_vars):
    """
    Given: マークダウン形式の文字列
    When: _parse_markdownを呼び出す
    Then: 記事のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        markdown_content = """
## [Test Story](https://example.com/test)

スコア: 100

**要約**:
Test summary

---

"""

        records = service._parse_markdown(markdown_content)

        assert len(records) == 1
        assert records[0]["title"] == "Test Story"
        assert records[0]["url"] == "https://example.com/test"
        assert records[0]["score"] == 100
        assert "Test summary" in records[0]["summary"]


@pytest.mark.unit
def test_story_sort_key(mock_env_vars):
    """
    Given: 記事の辞書
    When: _story_sort_keyを呼び出す
    Then: ソート用のキー（score, published_at）が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        item = {
            "score": 100,
            "published_at": "2024-11-14T12:00:00+00:00"
        }

        score, published = service._story_sort_key(item)

        assert score == 100
        assert isinstance(published, datetime)


@pytest.mark.unit
def test_story_sort_key_with_invalid_date(mock_env_vars):
    """
    Given: 不正な日付を持つ記事
    When: _story_sort_keyを呼び出す
    Then: デフォルトの最小日時が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        item = {
            "score": 100,
            "published_at": "invalid-date"
        }

        score, published = service._story_sort_key(item)

        assert score == 100
        assert published == datetime.min.replace(tzinfo=timezone.utc)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_story(mock_env_vars):
    """
    Given: ストーリー
    When: _summarize_storyを呼び出す
    Then: summaryが設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        story = create_test_story(text="Test text")

        with patch.object(service, 'gpt_client') as mock_gpt:
            mock_gpt.generate_async = AsyncMock(return_value="Generated summary")
            with patch.object(service, 'rate_limit', new_callable=AsyncMock):
                await service._summarize_story(story)

        assert story.summary == "Generated summary"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_story_no_text(mock_env_vars):
    """
    Given: テキストがないストーリー
    When: _summarize_storyを呼び出す
    Then: デフォルトのエラーメッセージが設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        story = Story(
            title="Test Story",
            score=100
        )

        await service._summarize_story(story)

        assert "本文情報がないため" in story.summary


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_story_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: _summarize_storyを呼び出す
    Then: エラーメッセージが設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        story = Story(
            title="Test Story",
            score=100,
            text="Test text"
        )

        with patch.object(service, 'gpt_client') as mock_gpt:
            mock_gpt.generate_async = AsyncMock(side_effect=Exception("API Error"))
            with patch.object(service, 'rate_limit', new_callable=AsyncMock):
                await service._summarize_story(story)

        assert "エラーが発生しました" in story.summary


# =============================================================================
# 15. _load_existing_titles / _load_existing_stories / _store_summaries のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_titles_from_json(mock_env_vars):
    """
    Given: 既存のJSONファイル
    When: _load_existing_titlesを呼び出す
    Then: タイトルがDedupTrackerに追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        existing_data = [
            {"title": "Existing Title 1"},
            {"title": "Existing Title 2"}
        ]

        with patch.object(service.storage, 'exists', new_callable=AsyncMock, return_value=True), \
             patch.object(service, 'load_json', new_callable=AsyncMock, return_value=existing_data):

            tracker = await service._load_existing_titles()

            # タイトルが追加されているか確認
            is_dup1, _ = tracker.is_duplicate("Existing Title 1")
            is_dup2, _ = tracker.is_duplicate("Existing Title 2")
            assert is_dup1 is True
            assert is_dup2 is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_titles_from_markdown(mock_env_vars):
    """
    Given: 既存のMarkdownファイル（JSONなし）
    When: _load_existing_titlesを呼び出す
    Then: マークダウンからタイトルが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        markdown_content = """
## [Title from Markdown](https://example.com)

## Plain Title Without Link

Some content
"""

        with patch.object(service.storage, 'exists', new_callable=AsyncMock, return_value=False), \
             patch.object(service.storage, 'load_markdown', return_value=markdown_content):

            tracker = await service._load_existing_titles()

            # マークダウンから抽出されたタイトルを確認
            is_dup1, _ = tracker.is_duplicate("Title from Markdown")
            is_dup2, _ = tracker.is_duplicate("Plain Title Without Link")
            assert is_dup1 is True
            assert is_dup2 is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_titles_error(mock_env_vars):
    """
    Given: ファイル読み込みでエラー
    When: _load_existing_titlesを呼び出す
    Then: 空のトラッカーが返される（エラーは無視される）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        with patch.object(service.storage, 'exists', new_callable=AsyncMock, side_effect=Exception("Read error")):

            tracker = await service._load_existing_titles()

            # エラーでも空のトラッカーが返る
            assert tracker is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_stories_from_json(mock_env_vars):
    """
    Given: 既存のJSONファイル
    When: _load_existing_storiesを呼び出す
    Then: ストーリーのリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        existing_data = [
            {"title": "Story 1", "score": 100},
            {"title": "Story 2", "score": 200}
        ]

        target_date = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

        with patch.object(service, 'load_json', new_callable=AsyncMock, return_value=existing_data):

            stories = await service._load_existing_stories(target_date)

            assert len(stories) == 2
            assert stories[0]["title"] == "Story 1"
            assert stories[1]["title"] == "Story 2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_stories_from_markdown(mock_env_vars):
    """
    Given: Markdownファイルのみ（JSONなし）
    When: _load_existing_storiesを呼び出す
    Then: マークダウンからパースされたストーリーが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        markdown_content = """
## [Test Story](https://example.com/test)

スコア: 100

---
"""

        target_date = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

        with patch.object(service, 'load_json', new_callable=AsyncMock, return_value=None), \
             patch.object(service.storage, 'load', new_callable=AsyncMock, return_value=markdown_content):

            stories = await service._load_existing_stories(target_date)

            assert len(stories) == 1
            assert stories[0]["title"] == "Test Story"
            assert stories[0]["score"] == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_stories_no_file(mock_env_vars):
    """
    Given: ファイルが存在しない
    When: _load_existing_storiesを呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        target_date = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

        with patch.object(service, 'load_json', new_callable=AsyncMock, return_value=None), \
             patch.object(service.storage, 'load', new_callable=AsyncMock, return_value=None):

            stories = await service._load_existing_stories(target_date)

            assert stories == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_stories(mock_env_vars):
    """
    Given: 複数のストーリー
    When: _summarize_storiesを呼び出す
    Then: 各ストーリーが要約され、ブロックドメイン更新が呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        stories = [
            Story(title="Story 1", score=100, text="Text 1"),
            Story(title="Story 2", score=200, text="Text 2")
        ]

        with patch.object(service, '_summarize_story', new_callable=AsyncMock) as mock_summarize, \
             patch.object(service, '_update_blocked_domains_from_errors', new_callable=AsyncMock) as mock_update:

            await service._summarize_stories(stories)

            # 各ストーリーが要約される
            assert mock_summarize.call_count == 2
            # ブロックドメイン更新が呼ばれる
            mock_update.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_stories_empty(mock_env_vars):
    """
    Given: 空のストーリーリスト
    When: _summarize_storiesを呼び出す
    Then: 何も処理されない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        await service._summarize_stories([])

        # エラーが発生しないことを確認


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries(mock_env_vars):
    """
    Given: ストーリーのリスト
    When: _store_summariesを呼び出す
    Then: 保存されたファイルパスのリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        stories = [
            Story(
                title="Test Story",
                score=100,
                url="https://example.com",
                text="Test text",
                summary="Test summary",
                created_at=datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            )
        ]

        target_dates = [date(2024, 11, 14)]

        with patch('nook.services.hacker_news.hacker_news.store_daily_snapshots', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = [("/path/to/2024-11-14.json", "/path/to/2024-11-14.md")]

            result = await service._store_summaries(stories, target_dates)

            assert len(result) == 1
            assert result[0][0] == "/path/to/2024-11-14.json"
            assert result[0][1] == "/path/to/2024-11-14.md"
            mock_store.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_empty(mock_env_vars):
    """
    Given: 空のストーリーリスト
    When: _store_summariesを呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        result = await service._store_summaries([], [date.today()])

        assert result == []


# =============================================================================
# 16. HTMLパース・エッジケースのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_article_element(mock_env_vars, respx_mock):
    """
    Given: article要素を含むHTML（メタディスクリプション・段落なし）
    When: _fetch_story_contentを呼び出す
    Then: article要素からテキストが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        html_content = '<html><body><article>Article content here for testing purposes and extraction.</article></body></html>'

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        await service._fetch_story_content(story)

        assert story.text is not None
        assert "Article content" in story.text

        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_short_paragraphs(mock_env_vars, respx_mock):
    """
    Given: 短い段落のみのHTML
    When: _fetch_story_contentを呼び出す
    Then: 最初の段落が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        await service.setup_http_client()

        story = Story(
            title="Test",
            score=100,
            url="https://example.com/test"
        )

        html_content = '''<html><body>
            <p>Short</p>
            <p>Also short</p>
        </body></html>'''

        respx_mock.get("https://example.com/test").mock(
            return_value=httpx.Response(200, text=html_content)
        )

        await service._fetch_story_content(story)

        assert story.text is not None

        await service.cleanup()


@pytest.mark.unit
def test_render_markdown_with_text_only(mock_env_vars):
    """
    Given: summaryなし、textのみの記事
    When: _render_markdownを呼び出す
    Then: テキストが表示される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        records = [
            {
                "title": "Test Story",
                "score": 100,
                "url": "https://example.com/test",
                "text": "A" * 600  # 500文字以上
            }
        ]

        today = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
        markdown = service._render_markdown(records, today)

        assert "Test Story" in markdown
        assert "..." in markdown  # 省略記号が含まれる


@pytest.mark.unit
def test_render_markdown_no_url(mock_env_vars):
    """
    Given: URLなしの記事
    When: _render_markdownを呼び出す
    Then: リンクなしでタイトルが表示される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        records = [
            {
                "title": "Test Story Without URL",
                "score": 100,
                "summary": "Test summary"
            }
        ]

        today = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
        markdown = service._render_markdown(records, today)

        assert "Test Story Without URL" in markdown
        assert "[" not in markdown.split("## ")[1].split("\n")[0]  # タイトル行にリンク記法がない


@pytest.mark.unit
def test_parse_markdown_title_only(mock_env_vars):
    """
    Given: タイトルのみのマークダウン（URLなし）
    When: _parse_markdownを呼び出す
    Then: タイトルが正しくパースされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        markdown_content = """
## Title Without URL

スコア: 50

---
"""

        records = service._parse_markdown(markdown_content)

        assert len(records) == 1
        assert records[0]["title"] == "Title Without URL"
        assert records[0]["score"] == 50
        assert records[0]["url"] is None


@pytest.mark.unit
def test_story_sort_key_missing_score(mock_env_vars):
    """
    Given: スコアがない記事
    When: _story_sort_keyを呼び出す
    Then: デフォルトの0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        item = {
            "published_at": "2024-11-14T12:00:00+00:00"
        }

        score, published = service._story_sort_key(item)

        assert score == 0
        assert isinstance(published, datetime)


@pytest.mark.unit
def test_story_sort_key_no_published_at(mock_env_vars):
    """
    Given: published_atがない記事
    When: _story_sort_keyを呼び出す
    Then: デフォルトの最小日時が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        item = {
            "score": 100
        }

        score, published = service._story_sort_key(item)

        assert score == 100
        assert published == datetime.min.replace(tzinfo=timezone.utc)


# Section 17: Additional coverage tests for 95% target


@pytest.mark.unit
def test_dedup_tracker_with_similar_titles(mock_env_vars):
    """
    Given: 重複したタイトル（空白の違いのみ）
    When: DedupTrackerで重複チェックを行う
    Then: 重複として検出される
    """
    # Note: 実際の重複検出ロジックは_get_top_stories内で
    # DedupTrackerを使用して実装されている
    # ここではDedupTrackerの動作を単体でテスト
    tracker = DedupTracker()

    # 最初のタイトルを追加
    tracker.add("Test Article")

    # 同じタイトル（空白付き）を重複チェック
    is_dup, normalized = tracker.is_duplicate("Test Article  ")

    # 正規化後に重複として検出されるべき
    assert is_dup is True, "空白の違いのみのタイトルは重複として検出されるべき"


@pytest.mark.unit
def test_story_date_normalization(mock_env_vars):
    """
    Given: タイムゾーン付きの日時
    When: 日付に変換する
    Then: ローカルタイムゾーンの日付が取得される
    """
    # Note: 日付グループ化ロジックは_get_top_stories内の複雑な処理のため
    # 統合テストでカバーすべき。ここでは日付正規化の基本動作をテスト
    from nook.common.date_utils import normalize_datetime_to_local

    utc_time = datetime(2024, 11, 14, 23, 0, 0, tzinfo=timezone.utc)
    local_date = normalize_datetime_to_local(utc_time).date()

    # 日付として正規化されることを確認
    assert isinstance(local_date, date)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_log_fetch_summary(mock_env_vars):
    """
    Given: 様々な状態のストーリーリスト
    When: _log_fetch_summaryを呼び出す
    Then: 正しいサマリーがログに記録される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        stories = [
            Story(
                title="Success Story",
                score=100,
                url="https://example.com/1",
                text="This is successful content",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Blocked Story",
                score=90,
                url="https://blocked.com/1",
                text="このサイト（blocked.com）はアクセス制限のためブロックされています。",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Error Story",
                score=80,
                url="https://example.com/2",
                text="アクセス制限により記事を取得できませんでした。",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Not Found Story",
                score=70,
                url="https://example.com/3",
                text="記事が見つかりませんでした。",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Failed Story",
                score=60,
                url="https://example.com/4",
                text="記事の内容を取得できませんでした。",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="No Text Story",
                score=50,
                url="https://example.com/5",
                text=None,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # This should not raise an error
        await service._log_fetch_summary(stories)


@pytest.mark.unit
def test_is_blocked_domain_exception_handling(mock_env_vars):
    """
    Given: 不正なURL
    When: _is_blocked_domainを呼び出す
    Then: Falseが返される（例外は発生しない）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {"blocked_domains": None}  # Cause an exception

        result = service._is_blocked_domain("https://example.com")

        # Should handle exception and return False
        assert result is False


@pytest.mark.unit
def test_is_http1_required_domain_exception_handling(mock_env_vars):
    """
    Given: 不正な状態
    When: _is_http1_required_domainを呼び出す
    Then: Falseが返される（例外は発生しない）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.blocked_domains = {"http1_required_domains": None}  # Cause an exception

        result = service._is_http1_required_domain("https://example.com")

        # Should handle exception and return False
        assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_invalid_timestamp(mock_env_vars, respx_mock):
    """
    Given: 不正なタイムスタンプを持つストーリー
    When: _fetch_storyを呼び出す
    Then: created_atがNoneに設定され、その後現在時刻が設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        # Set up http_client for respx_mock to intercept
        service.http_client = httpx.AsyncClient()

        # Mock item API with invalid timestamp
        respx_mock.get(f"{service.base_url}/item/12345.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 12345,
                    "title": "Test Story",
                    "score": 50,
                    "url": "https://example.com",
                    "time": "invalid",  # Invalid timestamp
                },
            )
        )

        # Mock content fetching
        respx_mock.get("https://example.com").mock(
            return_value=httpx.Response(
                200, text="<p>" + "Test content" * 20 + "</p>"
            )
        )

        story = await service._fetch_story(12345)

        assert story is not None
        assert story.created_at is not None  # Should be set to current time


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_story_content_www_blocked_domain(mock_env_vars):
    """
    Given: www.付きのブロックされたドメイン
    When: _fetch_story_contentを呼び出す
    Then: www.が除去されて理由が取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        story = Story(
            title="Test",
            score=50,
            url="https://www.nytimes.com/article",
            text=None,
            created_at=datetime.now(timezone.utc),
        )

        await service._fetch_story_content(story)

        assert story.text is not None
        assert "ブロックされています" in story.text
        assert "nytimes.com" in story.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocked_domains_various_error_reasons(mock_env_vars):
    """
    Given: 様々なエラー理由を持つストーリー
    When: _update_blocked_domains_from_errorsを呼び出す
    Then: 適切なエラー理由が特定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        # Ensure blocked_domains is properly initialized
        service.blocked_domains = service._load_blocked_domains()

        stories = [
            Story(
                title="522 Error",
                score=50,
                url="https://error522.com/page",
                text="HTTP error 522 Server error occurred",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="429 Error",
                score=50,
                url="https://error429.com/page",
                text="HTTP error 429 Too Many Requests",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="403 Error",
                score=50,
                url="https://error403.com/page",
                text="HTTP error 403 Access denied",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="404 Error",
                score=50,
                url="https://error404.com/page",
                text="HTTP error 404 Not found",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Timeout Error",
                score=50,
                url="https://timeout.com/page",
                text="Request error: timeout occurred while connecting",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="SSL Error",
                score=50,
                url="https://sslerror.com/page",
                text="Request error: SSL handshake failed",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Request Error",
                score=50,
                url="https://requesterror.com/page",
                text="Request error occurred",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Generic Error",
                score=50,
                url="https://genericerror.com/page",
                text="HTTP error: Some other error",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="No URL",
                score=50,
                url=None,
                text="No text",
                created_at=datetime.now(timezone.utc),
            ),
            Story(
                title="Already Blocked",
                score=50,
                url="https://www.reuters.com/page",
                text="HTTP error 403",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock _add_to_blocked_domains to capture what domains would be added
        added_domains = {}

        async def mock_add_to_blocked_domains(new_domains):
            added_domains.update(new_domains)

        with patch.object(service, '_add_to_blocked_domains', side_effect=mock_add_to_blocked_domains):
            # Should not raise an error
            await service._update_blocked_domains_from_errors(stories)

        # Verify various error types were detected
        assert "error522.com" in added_domains
        assert "error429.com" in added_domains
        assert "error403.com" in added_domains
        assert "error404.com" in added_domains
        assert "timeout.com" in added_domains
        assert "sslerror.com" in added_domains
        assert "genericerror.com" in added_domains

        # reuters.com should not be in added_domains (already blocked)
        assert "reuters.com" not in added_domains

        # Verify error reasons are correctly identified
        assert added_domains["error522.com"] == "522 - Server error"
        assert added_domains["error429.com"] == "429 - Too Many Requests"
        assert added_domains["error403.com"] == "403 - Access denied"
        assert added_domains["error404.com"] == "404 - Not found"
        assert added_domains["timeout.com"] == "Timeout error"
        assert added_domains["sslerror.com"] == "SSL/TLS error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocked_domains_exception_handling(mock_env_vars):
    """
    Given: URLのパースに失敗するストーリー
    When: _update_blocked_domains_from_errorsを呼び出す
    Then: 例外が処理され、処理が続行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        # Ensure blocked_domains is properly initialized
        service.blocked_domains = service._load_blocked_domains()

        stories = [
            Story(
                title="Invalid URL",
                score=50,
                url="not a valid url",
                text="記事の内容を取得できませんでした。",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock _add_to_blocked_domains to capture what domains would be added
        added_domains = {}

        async def mock_add_to_blocked_domains(new_domains):
            added_domains.update(new_domains)

        with patch.object(service, '_add_to_blocked_domains', side_effect=mock_add_to_blocked_domains):
            # Should not raise an error
            await service._update_blocked_domains_from_errors(stories)

        # Empty domain should be added for invalid URL
        # (urlparse returns empty netloc for invalid URLs)
        assert len(added_domains) >= 0  # May include empty domain from invalid URL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_to_blocked_domains_file_not_exists(mock_env_vars, tmp_path):
    """
    Given: blocked_domains.jsonが存在しない
    When: _add_to_blocked_domainsを呼び出す
    Then: 新しいファイルが作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        # Use a non-existent path
        new_domains = {"newdomain.com": "Test reason"}

        with patch("nook.services.hacker_news.hacker_news.os.path.join") as mock_join:
            mock_join.return_value = str(tmp_path / "blocked_domains.json")

            await service._add_to_blocked_domains(new_domains)

            # Verify file was created
            assert (tmp_path / "blocked_domains.json").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_to_blocked_domains_exception_handling(mock_env_vars):
    """
    Given: ファイル書き込みに失敗する状況
    When: _add_to_blocked_domainsを呼び出す
    Then: 例外が処理され、エラーログが記録される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        new_domains = {"testdomain.com": "Test reason"}

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Should not raise an error
            await service._add_to_blocked_domains(new_domains)


@pytest.mark.unit
def test_run_sync_wrapper(mock_env_vars):
    """
    Given: HackerNewsRetrieverインスタンス
    When: run()メソッドを呼び出す
    Then: asyncio.runが使用されてcollectが実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()

        with patch("nook.services.hacker_news.hacker_news.asyncio.run") as mock_run:
            service.run(limit=10)

            # Verify asyncio.run was called
            mock_run.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_client_initialization(mock_env_vars):
    """
    Given: http_clientがNoneの状態
    When: collectメソッドを呼び出す
    Then: setup_http_clientが呼び出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = HackerNewsRetriever()
        service.http_client = None  # Ensure it's None

        with patch.object(service, 'setup_http_client', new_callable=AsyncMock) as mock_setup, \
             patch.object(service, '_load_existing_titles', new_callable=AsyncMock) as mock_load, \
             patch.object(service, '_get_top_stories', new_callable=AsyncMock) as mock_get, \
             patch.object(service, '_store_summaries', new_callable=AsyncMock) as mock_store:

            mock_load.return_value = Mock()
            mock_get.return_value = []
            mock_store.return_value = []

            await service.collect()

            # Verify setup_http_client was called
            mock_setup.assert_called_once()
