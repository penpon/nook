"""pytest共通設定・フィクスチャ"""

import asyncio
import sys
from pathlib import Path
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
        "DATA_DIR": "/tmp/nook_test_data",  # nosec B108
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
    respx_mock.get(url__regex=r"https://hacker-news\.firebaseio\.com/v0/item/\d+\.json").mock(
        return_value=httpx.Response(200, json=mock_hn_story)
    )

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
    return storage
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
# GPTクライアント モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_gpt_client():
    """GPTクライアントのモック"""
    mock_client = AsyncMock()
    mock_client.get_response = AsyncMock(return_value="テスト要約結果です。")
    mock_client.generate_async = AsyncMock(return_value="テスト翻訳結果です。")
    return mock_client


# =============================================================================
# feedparser モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_feed_entry():
    """feedparserエントリのモックデータ"""
    entry = Mock()
    entry.title = "テスト記事タイトル"
    entry.link = "https://example.com/test-article"
    entry.summary = "これはテスト記事の説明です。"
    entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
    entry.description = "<p>記事の説明</p>"
    return entry


@pytest.fixture
def mock_feedparser_result(mock_feed_entry):
    """feedparser.parseの返り値モック"""
    mock_feed = Mock()
    mock_feed.feed = Mock()
    mock_feed.feed.title = "テストフィード"
    mock_feed.feed.link = "https://example.com"
    mock_feed.entries = [mock_feed_entry]
    mock_feed.bozo = 0  # エラーなし
    return mock_feed


# =============================================================================
# BeautifulSoup モックHTMLフィクスチャ（人気スコア抽出用）
# =============================================================================


@pytest.fixture
def mock_html_with_meta_likes():
    """いいね数メタタグ付きHTML（Zenn/Qiita/Note用）"""
    return """
    <html>
    <head>
        <meta property="article:reaction_count" content="150">
        <meta property="zenn:likes_count" content="150">
        <meta property="qiita:likes_count" content="150">
        <meta name="twitter:data1" content="150 likes">
    </head>
    <body>
        <button data-like-count="150">♥ 150</button>
        <span class="js-lgtm-count">150</span>
        <p>これは日本語の記事本文です。</p>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_japanese_article():
    """日本語記事HTMLモック"""
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <title>日本語のテスト記事タイトル</title>
    </head>
    <body>
        <article>
            <h1>日本語記事のタイトル</h1>
            <p>これは日本語で書かれた記事の本文です。テストに使用します。</p>
            <p>複数段落があります。</p>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_english_article():
    """英語記事HTMLモック"""
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <title>English Test Article</title>
    </head>
    <body>
        <article>
            <h1>English Article Title</h1>
            <p>This is an English article body for testing purposes.</p>
            <p>Multiple paragraphs exist.</p>
        </article>
    </body>
    </html>
    """


# =============================================================================
# 4chan/5chan モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_4chan_catalog():
    """4chanカタログAPIレスポンスモック"""
    return [
        {
            "page": 0,
            "threads": [
                {
                    "no": 123456,
                    "sub": "AI Discussion Thread",
                    "com": "Let's talk about artificial intelligence and machine learning",
                    "replies": 50,
                    "images": 10,
                    "bumps": 45,
                    "time": 1699999999,
                }
            ],
        }
    ]


@pytest.fixture
def mock_4chan_thread():
    """4chanスレッド詳細APIレスポンスモック"""
    return {
        "posts": [
            {
                "no": 123456,
                "time": 1699999999,
                "com": "First post about AI",
                "replies": 50,
            },
            {
                "no": 123457,
                "time": 1700000000,
                "com": "Reply about machine learning",
            },
        ]
    }


@pytest.fixture
def mock_5chan_subject_txt():
    """5chan subject.txtモック（Shift_JIS形式）"""
    return "1234567890.dat<>AI・人工知能について語るスレ (100)\n9876543210.dat<>機械学習の最新動向 (50)\n"


@pytest.fixture
def mock_5chan_dat():
    """5chan datファイルモック（Shift_JIS形式）"""
    return """名無しさん<>sage<>2024/11/14(木) 12:00:00.00 ID:test1234<>AIについて語りましょう<>
名無しさん<>sage<>2024/11/14(木) 12:01:00.00 ID:test5678<>機械学習は面白い<>
"""


# =============================================================================
# Article/Record ファクトリーフィクスチャ
# =============================================================================


@pytest.fixture
def article_factory():
    """Articleオブジェクトを生成するファクトリー"""
    from datetime import datetime

    from bs4 import BeautifulSoup

    from nook.services.base_feed_service import Article

    def _create_article(
        title="テスト記事",
        url="https://example.com/test",
        text="記事本文テキスト",
        popularity_score=10.0,
        category="tech",
        feed_name="テストフィード",
    ):
        return Article(
            feed_name=feed_name,
            title=title,
            url=url,
            text=text,
            soup=BeautifulSoup("<p>test</p>", "html.parser"),
            category=category,
            popularity_score=popularity_score,
            published_at=datetime(2024, 11, 14, 12, 0, 0),
        )

    return _create_article


@pytest.fixture
def thread_factory():
    """Threadオブジェクトを生成するファクトリー"""

    def _create_thread(
        thread_id=123456,
        title="テストスレッド",
        url="https://example.com/thread/123456",
        board="test",
        posts=None,
        popularity_score=10.0,
    ):
        if posts is None:
            posts = [{"name": "名無しさん", "mail": "sage", "msg": "テスト投稿"}]

        # 各サービスで定義されているThreadクラスを使用する想定
        from dataclasses import dataclass, field
        from typing import Any

        @dataclass
        class Thread:
            thread_id: int
            title: str
            url: str
            board: str
            posts: list[dict[str, Any]]
            timestamp: int
            summary: str = field(default="")
            popularity_score: float = field(default=0.0)

        return Thread(
            thread_id=thread_id,
            title=title,
            url=url,
            board=board,
            posts=posts,
            timestamp=1699999999,
            summary="",
            popularity_score=popularity_score,
        )

    return _create_thread


# =============================================================================
# DedupTracker モックフィクスチャ
# =============================================================================


@pytest.fixture
def mock_dedup_tracker():
    """DedupTrackerのモック"""
    mock_tracker = Mock()
    mock_tracker.is_duplicate = Mock(return_value=(False, "normalized_title"))
    mock_tracker.add = Mock()
    return mock_tracker


# =============================================================================
# ロガーモックフィクスチャ（全テスト自動適用）
# =============================================================================


@pytest.fixture(autouse=True)
def auto_mock_logger():
    """全テストで自動的にsetup_loggerをモック

    このフィクスチャにより、各テストで個別に
    patch("nook.common.base_service.setup_logger")を
    書く必要がなくなります。
    """
    from unittest.mock import patch

    with patch("nook.common.base_service.setup_logger"):
        yield


# =============================================================================
# クリーンアップフィクスチャ
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """各テスト後の自動クリーンアップ"""
    return
    # テスト後の処理（必要に応じて）


# =============================================================================
# Zenn Explorer テスト用ヘルパー関数
# =============================================================================


def create_mock_entry(
    title="テスト記事",
    link="https://example.com/test",
    summary="テスト説明",
    published_parsed=(2024, 11, 14, 0, 0, 0, 0, 0, 0),
):
    """標準的なモックエントリを作成

    Args:
        title: 記事タイトル
        link: 記事URL
        summary: 記事サマリー
        published_parsed: 公開日時タプル

    Returns:
        Mock: 設定済みのモックエントリ
    """
    from unittest.mock import Mock

    entry = Mock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = published_parsed
    return entry


def create_mock_feed(title="Test Feed", entries=None):
    """標準的なモックフィードを作成

    Args:
        title: フィードタイトル
        entries: エントリのリスト（Noneの場合は空リスト）

    Returns:
        Mock: 設定済みのモックフィード
    """
    from unittest.mock import Mock

    feed = Mock()
    feed.feed.title = title
    feed.entries = entries if entries is not None else []
    return feed


def create_mock_dedup(is_duplicate=False, normalized_title="normalized_title"):
    """標準的なモックDedupTrackerを作成

    Args:
        is_duplicate: 重複判定の返り値
        normalized_title: 正規化されたタイトル

    Returns:
        Mock: 設定済みのモックDedupTracker
    """
    from unittest.mock import Mock

    dedup = Mock()
    dedup.is_duplicate.return_value = (is_duplicate, normalized_title)
    dedup.add.return_value = None
    return dedup


# =============================================================================
# Zenn Explorer テスト用統合フィクスチャ（Phase 2.1）
# =============================================================================


@pytest.fixture
def zenn_service_with_mocks(mock_env_vars):
    """ZennExplorerサービスと共通モックの統合セットアップ

    深いネストを解消し、テストコードを簡潔にするための統合フィクスチャ。
    collect()メソッドのテストで頻繁に使用される全モックをセットアップ。

    Returns:
        dict: 以下のキーを含む辞書
            - service: ZennExplorerインスタンス
            - mock_parse: feedparser.parseのモック
            - mock_load: load_existing_titles_from_storageのモック
            - mock_setup_http: setup_http_clientのモック
            - mock_get_dates: _get_all_existing_datesのモック
            - mock_storage_load: storage.loadのモック
            - mock_storage_save: storage.saveのモック

    使用例:
        def test_something(zenn_service_with_mocks):
            svc = zenn_service_with_mocks["service"]
            mock_parse = zenn_service_with_mocks["mock_parse"]
            # テストロジック...
    """
    from pathlib import Path
    from unittest.mock import AsyncMock, patch

    # auto_mock_loggerが既に適用されているため、手動パッチ不要
    from nook.services.zenn_explorer.zenn_explorer import ZennExplorer

    service = ZennExplorer()
    service.http_client = AsyncMock()

    # LOAD_TITLES_PATHの定義（test_zenn_explorer.pyと同じ）
    load_titles_path = "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage"

    with (
        patch("feedparser.parse") as mock_parse,
        patch.object(service, "setup_http_client", new_callable=AsyncMock) as mock_setup_http,
        patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ) as mock_get_dates,
        patch(load_titles_path, new_callable=AsyncMock) as mock_load,
        patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ) as mock_storage_load,
        patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ) as mock_storage_save,
    ):
        yield {
            "service": service,
            "mock_parse": mock_parse,
            "mock_load": mock_load,
            "mock_setup_http": mock_setup_http,
            "mock_get_dates": mock_get_dates,
            "mock_storage_load": mock_storage_load,
            "mock_storage_save": mock_storage_save,
        }


# =============================================================================
# テストデータ定数（Phase 2.4 - レビュー対応）
# =============================================================================

# HTML templates
TEST_HTML_SIMPLE = "<html><body><p>テキスト</p></body></html>"
TEST_HTML_JAPANESE = "<html><body><p>日本語テキスト</p></body></html>"
TEST_HTML_WITH_META = """<html>
<head><meta name="description" content="テスト説明"></head>
<body><p>コンテンツ</p></body>
</html>"""

# URLs
TEST_URL = "https://example.com/test"
TEST_FEED_URL = "https://example.com/feed.xml"
TEST_ARTICLE_BASE_URL = "https://example.com/article"

# Common values
TEST_FEED_NAME = "Test Feed"
TEST_CATEGORY_TECH = "tech"
TEST_CATEGORY_BUSINESS = "business"
TEST_SUMMARY = "要約"
TEST_TITLE = "テスト記事"

# Error messages（共通アサーションメッセージ）
MSG_RESULT_SHOULD_BE_LIST = "結果はリスト型であるべき"
MSG_RESULT_SHOULD_BE_ARTICLE = "結果はArticle型であるべき"
MSG_RESULT_SHOULD_NOT_BE_NONE = "結果はNoneであってはならない"


# =============================================================================
# テストヘルパー関数（Phase 2.4 - レビュー対応）
# =============================================================================


def setup_http_client_mock(service, html_content=TEST_HTML_SIMPLE):
    """HTTP clientのモックをセットアップ

    Args:
        service: ZennExplorerインスタンス
        html_content: 返すHTMLコンテンツ（デフォルト: TEST_HTML_SIMPLE）
    """
    from unittest.mock import AsyncMock, Mock

    service.http_client.get = AsyncMock(return_value=Mock(text=html_content))


def setup_gpt_client_mock(service, summary=TEST_SUMMARY):
    """GPT clientのモックをセットアップ

    Args:
        service: ZennExplorerインスタンス
        summary: 返す要約テキスト（デフォルト: TEST_SUMMARY）
    """
    from unittest.mock import AsyncMock

    service.gpt_client.get_response = AsyncMock(return_value=summary)


def assert_article_list_result(result, expected_count=None, min_count=None):
    """記事リストの共通アサーション

    Args:
        result: テスト結果
        expected_count: 期待される件数（Noneの場合はチェックしない）
        min_count: 最小件数（Noneの場合はチェックしない）
    """
    assert isinstance(result, list), MSG_RESULT_SHOULD_BE_LIST

    if expected_count is not None:
        assert len(result) == expected_count, (
            f"期待される件数は{expected_count}件、実際は{len(result)}件"
        )

    if min_count is not None:
        assert len(result) >= min_count, f"最小{min_count}件の記事が必要、実際は{len(result)}件"


def assert_article_result(result):
    """単一Article結果の共通アサーション

    Args:
        result: テスト結果
    """
    from nook.services.base_feed_service import Article

    assert result is not None, MSG_RESULT_SHOULD_NOT_BE_NONE
    assert isinstance(result, Article), MSG_RESULT_SHOULD_BE_ARTICLE


def create_test_html(content="テキスト", meta_description=None):
    """テスト用HTMLを生成

    Args:
        content: body内のコンテンツ
        meta_description: メタディスクリプション（Noneの場合は追加しない）

    Returns:
        str: 生成されたHTML
    """
    meta_tag = ""
    if meta_description:
        meta_tag = f'<head><meta name="description" content="{meta_description}"></head>'

    return f"<html>{meta_tag}<body><p>{content}</p></body></html>"
