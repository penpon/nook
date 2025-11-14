"""pytest共通設定・フィクスチャ"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
import respx

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# セッションスコープフィクスチャ
# =============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """イベントループポリシー設定"""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# 環境変数・設定フィクスチャ
# =============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """環境変数のモック設定"""
    env_vars = {
        "OPENAI_API_KEY": "test-api-key-12345",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "REDDIT_CLIENT_ID": "test-client-id",
        "REDDIT_CLIENT_SECRET": "test-client-secret",
        "REDDIT_USER_AGENT": "test-user-agent",
        "DATA_DIR": "/tmp/nook_test_data",
        "LOG_LEVEL": "INFO",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def temp_data_dir(tmp_path):
    """テスト用一時データディレクトリ"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


# =============================================================================
# HTTPクライアント・API モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_httpx_client():
    """モックHTTPXクライアント"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.fixture
def respx_mock():
    """respxモックルーター（外部API呼び出しをモック化）"""
    with respx.mock(assert_all_called=False) as router:
        yield router


# =============================================================================
# OpenAI API モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_openai_response():
    """OpenAI APIレスポンスのモックデータ"""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1699999999,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "テスト翻訳・要約結果です。",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


@pytest.fixture
def mock_openai_api(respx_mock, mock_openai_response):
    """OpenAI APIエンドポイントのモック"""
    route = respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response)
    )
    return route


# =============================================================================
# Reddit API モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_reddit_post():
    """Redditポストのサンプルデータ"""
    return {
        "kind": "t3",
        "data": {
            "id": "test123",
            "title": "Test Reddit Post",
            "selftext": "This is a test post content.",
            "author": "test_user",
            "score": 100,
            "num_comments": 25,
            "created_utc": 1699999999,
            "url": "https://reddit.com/r/test/comments/test123",
            "subreddit": "test",
            "permalink": "/r/test/comments/test123",
        },
    }


@pytest.fixture
def mock_reddit_api(respx_mock, mock_reddit_post):
    """Reddit APIエンドポイントのモック"""
    # OAuth認証
    respx_mock.post("https://www.reddit.com/api/v1/access_token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "test-access-token",
                "token_type": "bearer",
                "expires_in": 3600,
            },
        )
    )

    # 投稿一覧取得
    respx_mock.get(url__regex=r"https://oauth\.reddit\.com/r/.+/hot.*").mock(
        return_value=httpx.Response(
            200,
            json={
                "kind": "Listing",
                "data": {"children": [mock_reddit_post], "after": None, "before": None},
            },
        )
    )

    return respx_mock


# =============================================================================
# Hacker News API モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_hn_story():
    """Hacker Newsストーリーのサンプルデータ"""
    return {
        "id": 12345,
        "type": "story",
        "by": "test_author",
        "time": 1699999999,
        "title": "Test HN Story",
        "url": "https://example.com/test",
        "score": 200,
        "descendants": 50,
    }


@pytest.fixture
def mock_hn_api(respx_mock, mock_hn_story):
    """Hacker News APIエンドポイントのモック"""
    # トップストーリー一覧
    respx_mock.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
        return_value=httpx.Response(200, json=[12345, 67890])
    )

    # 個別ストーリー取得
    respx_mock.get(
        url__regex=r"https://hacker-news\.firebaseio\.com/v0/item/\d+\.json"
    ).mock(return_value=httpx.Response(200, json=mock_hn_story))

    return respx_mock


# =============================================================================
# GitHub Trending モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_github_trending_html():
    """GitHub TrendingページのモックHTML"""
    return """
    <html>
    <body>
        <article class="Box-row">
            <h2 class="h3 lh-condensed">
                <a href="/test/repo">test/repo</a>
            </h2>
            <p class="col-9 color-fg-muted my-1 pr-4">Test repository description</p>
            <div class="f6 color-fg-muted mt-2">
                <span class="d-inline-block mr-3">
                    <span class="repo-language-color" style="background-color:#3572A5;"></span>
                    <span>Python</span>
                </span>
                <span class="d-inline-block mr-3">
                    <svg></svg>
                    <span>1,234</span>
                </span>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def mock_github_api(respx_mock, mock_github_trending_html):
    """GitHub TrendingページのHTMLモック"""
    respx_mock.get(url__regex=r"https://github\.com/trending.*").mock(
        return_value=httpx.Response(200, text=mock_github_trending_html)
    )
    return respx_mock


# =============================================================================
# arxiv API モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_arxiv_entry_xml():
    """arxiv APIレスポンスのモックXML"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2301.00001v1</id>
            <title>Test Paper Title</title>
            <summary>This is a test paper abstract.</summary>
            <author><name>Test Author</name></author>
            <published>2023-01-01T00:00:00Z</published>
            <updated>2023-01-01T00:00:00Z</updated>
            <link href="http://arxiv.org/abs/2301.00001v1" rel="alternate"/>
            <link href="http://arxiv.org/pdf/2301.00001v1" title="pdf" rel="related"/>
            <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
        </entry>
    </feed>
    """


@pytest.fixture
def mock_arxiv_api(respx_mock, mock_arxiv_entry_xml):
    """arxiv APIエンドポイントのモック"""
    respx_mock.get(url__regex=r"http://export\.arxiv\.org/api/query.*").mock(
        return_value=httpx.Response(
            200, text=mock_arxiv_entry_xml, headers={"Content-Type": "application/xml"}
        )
    )
    return respx_mock


# =============================================================================
# RSSフィード モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_rss_feed_xml():
    """RSSフィードのモックXML"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <link>https://example.com</link>
            <description>Test RSS Feed</description>
            <item>
                <title>Test Article</title>
                <link>https://example.com/article1</link>
                <description>Test article description</description>
                <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
                <guid>https://example.com/article1</guid>
            </item>
        </channel>
    </rss>
    """


@pytest.fixture
def mock_rss_feed(respx_mock, mock_rss_feed_xml):
    """RSSフィードエンドポイントのモック"""
    # より具体的なパターンに限定（example.comドメインのみ）
    respx_mock.get(url__regex=r"https?://example\.com/.*\.xml").mock(
        return_value=httpx.Response(
            200, text=mock_rss_feed_xml, headers={"Content-Type": "application/xml"}
        )
    )
    return respx_mock


# =============================================================================
# ストレージ モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_storage(temp_data_dir, monkeypatch):
    """LocalStorageのモック（一時ディレクトリ使用）"""
    monkeypatch.setenv("DATA_DIR", str(temp_data_dir))
    from nook.common.storage import LocalStorage

    storage = LocalStorage(service_name="test_service")
    yield storage
    # クリーンアップ（テスト後に一時ファイル削除）


# =============================================================================
# 時刻固定フィクスチャ
# =============================================================================


@pytest.fixture
def fixed_datetime(monkeypatch):
    """日時を固定するフィクスチャ"""
    import datetime

    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 11, 14, 12, 0, 0)

    monkeypatch.setattr(datetime, "datetime", MockDatetime)
    return MockDatetime


# =============================================================================
# クリーンアップフィクスチャ
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """各テスト後の自動クリーンアップ"""
    yield
    # テスト後の処理（必要に応じて）
