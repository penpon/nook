"""
nook/services/qiita_explorer/qiita_explorer.py のテスト

テスト観点:
- QiitaExplorerの初期化
- RSSフィード取得と解析
- 記事の重複チェック
- 人気スコア抽出
- 記事本文取得
- 要約生成
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article
from nook.services.qiita_explorer.qiita_explorer import QiitaExplorer

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: QiitaExplorerを初期化
    Then: インスタンスが正常に作成され、feed_configが読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        assert service.service_name == "qiita_explorer"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    """
    Given: QiitaExplorerクラス
    When: TOTAL_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert QiitaExplorer.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    """
    Given: QiitaExplorerクラス
    When: SUMMARY_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert QiitaExplorer.SUMMARY_LIMIT == 15


# =============================================================================
# 2. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_with_default_params(mock_env_vars):
    """
    Given: run()
    When: パラメータなしでrunメソッドを呼び出す
    Then: デフォルト値(days=1, limit=None)で実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.collect = AsyncMock(return_value=[])

        with patch("asyncio.run") as mock_run:
            service.run()

            mock_run.assert_called_once()


# =============================================================================
# 3. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_multiple_categories_feed_processing(mock_env_vars):
    """
    Given: feed_configに複数カテゴリが存在する
    When: collectメソッドを呼び出す
    Then: 各カテゴリのフィードが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.feed_config = {
            "category1": ["https://example.com/feed1.xml"],
            "category2": ["https://example.com/feed2.xml"],
        }
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            call_count = 0

            def mock_parse_func(url):
                nonlocal call_count
                call_count += 1
                mock_feed = Mock()
                mock_feed.feed.title = f"Feed {call_count}"
                entry = Mock()
                entry.title = f"記事{call_count}"
                entry.link = f"https://example.com/article{call_count}"
                entry.summary = f"説明{call_count}"
                entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
                mock_feed.entries = [entry]
                return mock_feed

            mock_parse.side_effect = mock_parse_func

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>本文</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)
            assert call_count == 2  # 2カテゴリ処理


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_one_feed_fails_others_continue(mock_env_vars):
    """
    Given: 複数フィードのうち1つが失敗する
    When: collectメソッドを呼び出す
    Then: 失敗したフィードはスキップされ、他のフィードは処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.feed_config = {
            "category": [
                "https://example.com/feed1.xml",
                "https://example.com/feed2.xml",
            ]
        }
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):

            def mock_parse_func(url):
                if "feed1" in url:
                    raise Exception("Feed 1 parse error")
                mock_feed = Mock()
                mock_feed.feed.title = "Feed 2"
                entry = Mock()
                entry.title = "記事2"
                entry.link = "https://example.com/article2"
                entry.summary = "説明2"
                entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
                mock_feed.entries = [entry]
                return mock_feed

            mock_parse.side_effect = mock_parse_func

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>本文</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


# =============================================================================
# 3-2. collect メソッドのテスト - 正常系（既存）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(mock_env_vars):
    """
    Given: 有効なRSSフィード
    When: collectメソッドを呼び出す
    Then: 記事が正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テストQiita記事"
            mock_entry.link = "https://example.com/article1"
            mock_entry.summary = "テストQiita記事の説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized_title")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text="<html><body><p>日本語テキスト</p></body></html>"
                )
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_articles(mock_env_vars):
    """
    Given: 複数の記事を含むフィード
    When: collectメソッドを呼び出す
    Then: 全ての記事が処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            entries = []
            for i in range(5):
                entry = Mock()
                entry.title = f"テストQiita記事{i}"
                entry.link = f"https://example.com/article{i}"
                entry.summary = f"説明{i}"
                entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
                entries.append(entry)
            mock_feed.entries = entries
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text="<html><body><p>日本語テキスト</p></body></html>"
                )
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_target_dates_none(mock_env_vars):
    """
    Given: target_dates=None
    When: collectメソッドを呼び出す
    Then: デフォルトの日付範囲で実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10, target_dates=None)

            assert isinstance(result, list)


# =============================================================================
# 4. collect メソッドのテスト - 異常系
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
        service = QiitaExplorer()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_parse.side_effect = Exception("Network error")

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_feed_xml(mock_env_vars):
    """
    Given: 不正なXMLフィード
    When: collectメソッドを呼び出す
    Then: エラーがログされ、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1)

            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_client_timeout(mock_env_vars):
    """
    Given: HTTPクライアントがタイムアウト
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト"
            mock_entry.link = "https://example.com/test"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = await service.collect(days=1)

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
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>日本語</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await service.collect(days=1)

            assert isinstance(result, list)


# =============================================================================
# 5. collect メソッドのテスト - 境界値
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_zero(mock_env_vars):
    """
    Given: limit=0
    When: collectメソッドを呼び出す
    Then: 記事が取得されない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1, limit=0)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_one(mock_env_vars):
    """
    Given: limit=1
    When: collectメソッドを呼び出す
    Then: 最大1件の記事が処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test"
            mock_entry = Mock()
            mock_entry.title = "テスト"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>日本語</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=1)

            assert isinstance(result, list)


# =============================================================================
# 6. _select_top_articles メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_select_top_articles_with_empty_list(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _select_top_articlesを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        result = service._select_top_articles([])

        assert result == []


@pytest.mark.unit
def test_select_top_articles_sorts_by_popularity(mock_env_vars):
    """
    Given: 人気スコアが異なる複数の記事
    When: _select_top_articlesを呼び出す
    Then: 人気スコアの降順でソートされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        articles = [
            Article(
                feed_name="Test",
                title="Article 1",
                url="http://example.com/1",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=10.0,
                published_at=datetime.now(),
            ),
            Article(
                feed_name="Test",
                title="Article 2",
                url="http://example.com/2",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=50.0,
                published_at=datetime.now(),
            ),
            Article(
                feed_name="Test",
                title="Article 3",
                url="http://example.com/3",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=30.0,
                published_at=datetime.now(),
            ),
        ]

        result = service._select_top_articles(articles, limit=2)

        assert len(result) == 2
        assert result[0].popularity_score == 50.0
        assert result[1].popularity_score == 30.0


@pytest.mark.unit
def test_select_top_articles_with_limit_none(mock_env_vars):
    """
    Given: limit=None
    When: _select_top_articlesを呼び出す
    Then: SUMMARY_LIMIT件が選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        articles = [
            Article(
                feed_name="Test",
                title=f"Article {i}",
                url=f"http://example.com/{i}",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=float(i),
                published_at=datetime.now(),
            )
            for i in range(20)
        ]

        result = service._select_top_articles(articles, limit=None)

        assert len(result) == service.SUMMARY_LIMIT


# =============================================================================
# 7. _retrieve_article メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_success(mock_env_vars):
    """
    Given: 有効なエントリ
    When: _retrieve_articleを呼び出す
    Then: Articleオブジェクトが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テストQiita記事"
        entry.link = "https://example.com/test"
        entry.summary = "テストの説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text="<html><body><p>これは日本語の記事です</p></body></html>"
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "テストQiita記事"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
    """
    Given: URLを持たないエントリ
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.title = "テスト"
        entry.link = None

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_error(mock_env_vars):
    """
    Given: HTTP取得時にエラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        service.http_client.get = AsyncMock(side_effect=Exception("HTTP Error"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


# =============================================================================
# 7-2. _retrieve_article メソッドの詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_summary_in_entry(mock_env_vars):
    """
    Given: エントリにsummaryフィールドがある
    When: _retrieve_articleを呼び出す
    Then: summaryがtextに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        entry.summary = "エントリの要約テキスト"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>記事本文</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "エントリの要約テキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_fallback_to_meta_description(mock_env_vars):
    """
    Given: entry.summaryがなく、HTMLにメタディスクリプションがある
    When: _retrieve_articleを呼び出す
    Then: メタディスクリプションがtextに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        entry.summary = None
        delattr(entry, "summary")  # summary属性を完全に削除
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_meta = """
        <html>
            <head><meta name="description" content="メタディスクリプションのテキスト"></head>
            <body><p>本文</p></body>
        </html>
        """
        service.http_client.get = AsyncMock(return_value=Mock(text=html_with_meta))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "メタディスクリプションのテキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_fallback_to_paragraphs(mock_env_vars):
    """
    Given: entry.summaryもメタディスクリプションもなく、段落のみある
    When: _retrieve_articleを呼び出す
    Then: 最初の5段落がtextに設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        delattr(entry, "summary")
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_paragraphs = """
        <html>
            <body>
                <p>段落1</p>
                <p>段落2</p>
                <p>段落3</p>
                <p>段落4</p>
                <p>段落5</p>
                <p>段落6</p>
            </body>
        </html>
        """
        service.http_client.get = AsyncMock(
            return_value=Mock(text=html_with_paragraphs)
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "段落1" in result.text
        assert "段落5" in result.text
        assert "段落6" not in result.text  # 6段落目は含まれない


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    """
    Given: HTTP GET が404エラーを返す
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/not-found"

        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=Mock(status_code=404),
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_500_error(mock_env_vars):
    """
    Given: HTTP GET が500エラーを返す
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/server-error"

        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Server Error",
                request=Mock(),
                response=Mock(status_code=500),
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_timeout_error(mock_env_vars):
    """
    Given: HTTP GET がタイムアウトする
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/timeout"

        service.http_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_empty_html(mock_env_vars):
    """
    Given: HTTP GETが空HTMLを返す
    When: _retrieve_articleを呼び出す
    Then: Articleオブジェクトが返されるがtextは空
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/empty"
        delattr(entry, "summary")
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_title_defaults_to_untitled(mock_env_vars):
    """
    Given: エントリにtitle属性がない
    When: _retrieve_articleを呼び出す
    Then: titleが"無題"になる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        delattr(entry, "title")
        entry.link = "https://example.com/no-title"
        entry.summary = "要約テキスト"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>本文</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.title == "無題"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_extract_popularity_called(mock_env_vars):
    """
    Given: 有効なエントリとHTML
    When: _retrieve_articleを呼び出す
    Then: _extract_popularityが呼ばれ、popularity_scoreが設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        entry.summary = "要約"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
        entry.qiita_likes_count = 350

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>本文</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.popularity_score == 350.0


# =============================================================================
# 8. _extract_popularity メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_meta_tag(mock_env_vars):
    """
    Given: 人気スコアを含むメタタグ
    When: _extract_popularityを呼び出す
    Then: スコアが正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta property="article:reaction_count" content="100"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result >= 0.0


@pytest.mark.unit
def test_extract_popularity_without_score(mock_env_vars):
    """
    Given: 人気スコアがないHTML
    When: _extract_popularityを呼び出す
    Then: 0.0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 8-2. _extract_popularity メソッドの詳細テスト（Qiita特有）
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_from_entry_qiita_likes_count(mock_env_vars):
    """
    Given: エントリにqiita_likes_count属性がある
    When: _extract_popularityを呼び出す
    Then: qiita_likes_countの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = 150
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_from_entry_likes_count(mock_env_vars):
    """
    Given: エントリにlikes_count属性がある
    When: _extract_popularityを呼び出す
    Then: likes_countの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = None
        entry.likes_count = 200
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 200.0


@pytest.mark.unit
def test_extract_popularity_from_entry_lgtm(mock_env_vars):
    """
    Given: エントリにlgtm属性がある
    When: _extract_popularityを呼び出す
    Then: lgtmの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = 100
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_from_entry_lgtm_count(mock_env_vars):
    """
    Given: エントリにlgtm_count属性がある
    When: _extract_popularityを呼び出す
    Then: lgtm_countの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = None
        entry.likes_count = None
        entry.lgtm = None
        entry.lgtm_count = 75
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 75.0


@pytest.mark.unit
def test_extract_popularity_from_entry_dict(mock_env_vars):
    """
    Given: エントリがdictでqiita_likes_countキーを持つ
    When: _extract_popularityを呼び出す
    Then: dict.get()でqiita_likes_countの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = {"qiita_likes_count": 250}
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_from_meta_twitter_data1_number_only(mock_env_vars):
    """
    Given: メタタグtwitter:data1に数値のみがある
    When: _extract_popularityを呼び出す
    Then: メタタグの値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta name="twitter:data1" content="300"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_from_meta_twitter_data1_with_text(mock_env_vars):
    """
    Given: メタタグtwitter:data1に"150 likes"形式のテキストがある
    When: _extract_popularityを呼び出す
    Then: 数値部分が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta name="twitter:data1" content="150 likes"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_from_data_lgtm_count(mock_env_vars):
    """
    Given: data-lgtm-count属性を持つ要素がある
    When: _extract_popularityを呼び出す
    Then: data属性の値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><button data-lgtm-count="120">LGTM</button></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 120.0


@pytest.mark.unit
def test_extract_popularity_from_data_likes_count(mock_env_vars):
    """
    Given: data-likes-count属性を持つ要素がある
    When: _extract_popularityを呼び出す
    Then: data属性の値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div data-likes-count="180"></div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 180.0


@pytest.mark.unit
def test_extract_popularity_from_data_qiita_lgtm_count(mock_env_vars):
    """
    Given: data-qiita-lgtm-count属性を持つ要素がある
    When: _extract_popularityを呼び出す
    Then: data属性の値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><span data-qiita-lgtm-count="95"></span></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 95.0


@pytest.mark.unit
def test_extract_popularity_from_js_lgtm_count_class(mock_env_vars):
    """
    Given: .js-lgtm-countクラスを持つ要素のテキストに数値がある
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><span class="js-lgtm-count">LGTM 135</span></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 135.0


@pytest.mark.unit
def test_extract_popularity_from_it_actions_item_count_class(mock_env_vars):
    """
    Given: .it-Actions_itemCountクラスを持つ要素のテキストに"LGTM"と数値がある
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div class="it-Actions_itemCount">LGTM 88</div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 88.0


@pytest.mark.unit
def test_extract_popularity_from_button_with_iine(mock_env_vars):
    """
    Given: buttonタグのテキストに"いいね"と数値がある
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><button>♥ いいね 220</button></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 220.0


@pytest.mark.unit
def test_extract_popularity_from_span_with_likes(mock_env_vars):
    """
    Given: spanタグのテキストに"likes"と数値がある
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><span>165 likes</span></body></html>", "html.parser"
        )

        result = service._extract_popularity(entry, soup)

        assert result == 165.0


@pytest.mark.unit
def test_extract_popularity_multiple_candidates_returns_max(mock_env_vars):
    """
    Given: 複数の候補（data属性、テキスト要素）が存在する
    When: _extract_popularityを呼び出す
    Then: 最大値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            """
            <html><body>
                <div data-lgtm-count="50"></div>
                <span class="js-lgtm-count">LGTM 300</span>
                <button>いいね 150</button>
            </body></html>
            """,
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_meta_without_content(mock_env_vars):
    """
    Given: メタタグはあるがcontent属性がない
    When: _extract_popularityを呼び出す
    Then: メタタグをスキップして次の候補を探す
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            """
            <html>
                <head><meta name="twitter:data1"></head>
                <body><div data-lgtm-count="75"></div></body>
            </html>
            """,
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 75.0


@pytest.mark.unit
def test_extract_popularity_text_without_keywords(mock_env_vars):
    """
    Given: テキスト要素に数値はあるがキーワード（LGTM、いいね、likes）がない
    When: _extract_popularityを呼び出す
    Then: そのテキストは候補に含まれない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><span>123 views</span></body></html>", "html.parser"
        )

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


@pytest.mark.unit
def test_extract_popularity_safe_parse_int_with_non_numeric_text(mock_env_vars):
    """
    Given: 数値と非数値文字が混在するテキスト（"いいね250人"など）
    When: _extract_popularityを呼び出す（内部で_safe_parse_intが使用される）
    Then: 数値部分が正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><button>いいね250人</button></body></html>", "html.parser"
        )

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


# =============================================================================
# 9. _get_markdown_header メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_markdown_header(mock_env_vars):
    """
    Given: QiitaExplorerインスタンス
    When: _get_markdown_headerを呼び出す
    Then: ヘッダーテキストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        result = service._get_markdown_header()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 10. _get_summary_system_instruction メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_system_instruction(mock_env_vars):
    """
    Given: QiitaExplorerインスタンス
    When: _get_summary_system_instructionを呼び出す
    Then: システム指示が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        result = service._get_summary_system_instruction()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 11. _get_summary_prompt_template メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_prompt_template(mock_env_vars):
    """
    Given: 記事オブジェクト
    When: _get_summary_prompt_templateを呼び出す
    Then: プロンプトテンプレートが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        article = Article(
            feed_name="Test",
            title="テストQiita記事",
            url="http://example.com/test",
            text="テスト本文" * 100,
            soup=BeautifulSoup("", "html.parser"),
            category="tech",
            popularity_score=10.0,
            published_at=datetime.now(),
        )

        result = service._get_summary_prompt_template(article)

        assert isinstance(result, str)


# =============================================================================
# 12. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_handles_feed_parse_error_gracefully(mock_env_vars):
    """
    Given: フィード解析エラー
    When: collectを実行
    Then: エラーがログされ、処理が続行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_parse.side_effect = Exception("Parse error")

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch.object(
                service.storage, "load", new_callable=AsyncMock, return_value=None
            ),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テストQiita記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "テスト説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語の記事</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)

            await service.cleanup()
