"""pytest共通設定・フィクスチャ"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

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
# arXiv 専用フィクスチャ
# =============================================================================


@pytest.fixture
def arxiv_service(mock_env_vars):
    """ArxivSummarizerサービスのフィクスチャ（共通セットアップ）"""
    with patch("nook.common.logging.setup_logger"):
        from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer

        service = ArxivSummarizer()
        yield service


@pytest.fixture
def test_date():
    """テスト用固定日付"""
    from datetime import date

    return date(2024, 1, 1)


@pytest.fixture
def test_datetime():
    """テスト用固定日時"""
    from datetime import datetime, timezone

    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def paper_info_factory():
    """PaperInfoオブジェクトを生成するファクトリー"""
    from datetime import datetime, timezone

    def _create(
        title="Test Paper",
        abstract="Test Abstract",
        url=None,
        arxiv_id="2301.00001",
        contents="Test contents",
        published_at=None,
        **kwargs,
    ):
        from nook.services.arxiv_summarizer.arxiv_summarizer import PaperInfo

        if url is None:
            url = f"http://arxiv.org/abs/{arxiv_id}"

        if published_at is None:
            published_at = datetime(2023, 1, 1, tzinfo=timezone.utc)

        paper = PaperInfo(
            title=title,
            abstract=abstract,
            url=url,
            contents=contents,
            published_at=published_at,
        )

        # summaryが指定されていれば設定
        if "summary" in kwargs:
            paper.summary = kwargs["summary"]

        return paper

    return _create


@pytest.fixture
def mock_arxiv_paper_factory():
    """arxiv.Resultオブジェクトのモックを生成するファクトリー"""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    def _create(
        arxiv_id="2301.00001",
        title="Test Paper Title",
        summary="Test abstract",
        published=None,
        **kwargs,
    ):
        if published is None:
            published = datetime(2023, 1, 1, tzinfo=timezone.utc)

        mock_paper = Mock()
        mock_paper.entry_id = f"http://arxiv.org/abs/{arxiv_id}"
        mock_paper.title = title
        mock_paper.summary = summary
        mock_paper.published = published

        # 追加属性
        for key, value in kwargs.items():
            setattr(mock_paper, key, value)

        return mock_paper

    return _create


# =============================================================================
# arXiv テストヘルパー
# =============================================================================


class ArxivTestHelper:
    """
    arXivテスト用のヘルパークラス

    テスト定数とモック作成メソッドを提供し、テストコードの重複を削減します。

    使用例:
        def test_example(arxiv_helper):
            # 定数を使用
            arxiv_id = arxiv_helper.DEFAULT_ARXIV_ID

            # モック作成
            mock_client = arxiv_helper.create_mock_http_client()
    """

    # ============================================================================
    # テスト定数
    # ============================================================================
    DEFAULT_ARXIV_ID = "2301.00001"
    DEFAULT_MIN_LINE_LENGTH = 80
    SAMPLE_PAPER_IDS = ["2301.00001", "2301.00002", "2301.00003"]

    # テストデータ定数
    SAMPLE_PAPER_TITLE = "Test Paper Title"
    SAMPLE_ABSTRACT = "Test abstract"
    SAMPLE_CONTENTS = "Test contents"
    SAMPLE_SUMMARY = "Test summary"

    # HTML/Markdown テストデータ
    SAMPLE_MARKDOWN_VALID = """# arXiv 論文要約 (2024-01-01)

## [Test Paper 1](http://arxiv.org/abs/2301.00001)

**abstract**:
Abstract 1

**summary**:
Summary 1

---
"""

    # ============================================================================
    # モック作成メソッド
    # ============================================================================

    @staticmethod
    def create_mock_http_client():
        """HTTPクライアントのモックを作成

        Returns:
            AsyncMock: コンテキストマネージャーとして使用可能なモック
        """
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        return mock_client

    @staticmethod
    def create_mock_pdf_response(content=b"%PDF-1.4 test content"):
        """PDFレスポンスのモックを作成

        Args:
            content: PDFバイナリコンテンツ

        Returns:
            Mock: HTTPレスポンスモック
        """
        mock_response = Mock()
        mock_response.content = content
        mock_response.raise_for_status = Mock()
        return mock_response

    @staticmethod
    def create_mock_html_response(text="<html><body>Test</body></html>"):
        """HTMLレスポンスのモックを作成

        Args:
            text: HTMLテキスト

        Returns:
            Mock: HTTPレスポンスモック
        """
        mock_response = Mock()
        mock_response.text = text
        mock_response.raise_for_status = Mock()
        return mock_response

    @staticmethod
    def create_mock_arxiv_client(results=None):
        """arxiv.Clientのモックを作成

        Args:
            results: resultsメソッドが返すリスト（デフォルトは空リスト）

        Returns:
            Mock: arxiv.Clientモック
        """
        if results is None:
            results = []
        mock_client = Mock()
        mock_client.results.return_value = results
        return mock_client

    @staticmethod
    def create_mock_pdf(text="Test PDF content"):
        """pdfplumber PDFオブジェクトのモックを作成

        Args:
            text: 抽出されるテキスト

        Returns:
            Mock: PDFモック（コンテキストマネージャー対応）
        """
        mock_page = Mock()
        mock_page.extract_text.return_value = text

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__aexit__.return_value = None

        return mock_pdf


@pytest.fixture
def arxiv_helper():
    """ArxivTestHelperインスタンスを提供"""
    return ArxivTestHelper()


# =============================================================================
# クリーンアップフィクスチャ
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """各テスト後の自動クリーンアップ"""
    return
    # テスト後の処理（必要に応じて）
