"""nook/services/qiita_explorer/qiita_explorer.py のテスト

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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        assert service.service_name == "qiita_explorer"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    assert QiitaExplorer.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    assert QiitaExplorer.SUMMARY_LIMIT == 15


# =============================================================================
# 2. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_with_default_params(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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
# 3-2. collect メソッドのテスト - 正常系(既存)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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
                return_value=Mock(text="<html><body><p>日本語テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_articles(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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
                return_value=Mock(text="<html><body><p>日本語テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_target_dates_none(mock_env_vars):
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

            service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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
            service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

            result = await service.collect(days=1)

            assert isinstance(result, list)


# =============================================================================
# 5. collect メソッドのテスト - 境界値
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_zero(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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

    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テストQiita記事"
        entry.link = "https://example.com/test"
        entry.summary = "テストの説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>これは日本語の記事です</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "テストQiita記事"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        entry.summary = None
        delattr(entry, "summary")  # summary属性を完全に削除
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_meta = "<html><head><meta name='description' content='メタディスクリプションのテキスト'></head><body><p>本文</p></body></html>"
        service.http_client.get = AsyncMock(return_value=Mock(text=html_with_meta))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "メタディスクリプションのテキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_fallback_to_paragraphs(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/article"
        delattr(entry, "summary")
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_paragraphs = "<html><body><p>段落1</p><p>段落2</p><p>段落3</p><p>段落4</p><p>段落5</p><p>段落6</p></body></html>"
        service.http_client.get = AsyncMock(return_value=Mock(text=html_with_paragraphs))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "段落1" in result.text
        assert "段落5" in result.text
        assert "段落6" not in result.text  # 6段落目は含まれない


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/timeout"

        service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_empty_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/empty"
        delattr(entry, "summary")
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(return_value=Mock(text="<html><body></body></html>"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_title_defaults_to_untitled(mock_env_vars):
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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 8-2. _extract_popularity メソッドの詳細テスト(Qiita特有)
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_from_entry_qiita_likes_count(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = 150
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_from_entry_likes_count(mock_env_vars):
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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = {"qiita_likes_count": 250}
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_from_meta_twitter_data1_number_only(mock_env_vars):
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
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><button>HEART いいね 220</button></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 220.0


@pytest.mark.unit
def test_extract_popularity_from_span_with_likes(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body><span>165 likes</span></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 165.0


@pytest.mark.unit
def test_extract_popularity_multiple_candidates_returns_max(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><div data-lgtm-count='50'></div><span class='js-lgtm-count'>LGTM 300</span><button>いいね 150</button></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_meta_without_content(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><head><meta name='twitter:data1'></head><body><div data-lgtm-count='75'></div></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 75.0


@pytest.mark.unit
def test_extract_popularity_text_without_keywords(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body><span>123 views</span></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


@pytest.mark.unit
def test_extract_popularity_safe_parse_int_with_non_numeric_text(mock_env_vars):
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
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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


# =============================================================================
# 未カバー部分の追加テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_existing_json_parse_error(mock_env_vars):
    """既存記事JSONのパースエラー処理をテスト"""
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
            patch.object(service.storage, "load", new_callable=AsyncMock) as mock_storage_load,
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            # 不正なJSONを返す
            mock_storage_load.return_value = "invalid json {{"

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "新規記事"
            mock_entry.link = "https://example.com/new"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>本文</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            # JSONパースエラーがあっても処理は継続される
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_existing_file_load_exception(mock_env_vars):
    """既存ファイルロード時の例外処理をテスト"""
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
            patch.object(service.storage, "load", new_callable=AsyncMock) as mock_storage_load,
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            # ロード時に例外を発生させる
            mock_storage_load.side_effect = Exception("File read error")

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>本文</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            # 例外があっても処理は継続される
            assert isinstance(result, list)


@pytest.mark.unit
def test_select_top_articles_with_limit_none(mock_env_vars):
    """limit=Noneの場合にSUMMARY_LIMITが使用されることをテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        # 20個の記事を作成
        articles = []
        for i in range(20):
            article = Article(
                feed_name="Test",
                title=f"記事{i}",
                url=f"https://example.com/article{i}",
                text="本文",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=float(i),
                published_at=datetime.now(),
            )
            articles.append(article)

        # limit=None で呼び出し
        result = service._select_top_articles(articles, limit=None)

        # SUMMARY_LIMIT(15)個が返される
        assert len(result) == QiitaExplorer.SUMMARY_LIMIT
        # 人気スコアの降順でソートされている
        assert result[0].popularity_score == 19.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_articles(mock_env_vars):
    """_store_summariesメソッドの正常系をテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        from datetime import date

        articles = [
            Article(
                feed_name="Test Feed",
                title="記事1",
                url="https://example.com/1",
                text="本文1",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=10.0,
                published_at=datetime(2024, 11, 14, 10, 0, 0),
            ),
            Article(
                feed_name="Test Feed",
                title="記事2",
                url="https://example.com/2",
                text="本文2",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=20.0,
                published_at=datetime(2024, 11, 14, 12, 0, 0),
            ),
        ]

        target_dates = [date(2024, 11, 14)]

        with (
            patch.object(
                service,
                "_load_existing_articles",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(
                service,
                "save_json",
                new_callable=AsyncMock,
                return_value=Path("data/qiita_explorer/2024-11-14.json"),
            ),
            patch.object(
                service,
                "save_markdown",
                new_callable=AsyncMock,
                return_value=Path("data/qiita_explorer/2024-11-14.md"),
            ),
        ):
            result = await service._store_summaries(articles, target_dates)

            assert isinstance(result, list)
            assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_empty_articles(mock_env_vars):
    """_store_summariesで空の記事リストをテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        from datetime import date

        target_dates = [date(2024, 11, 14)]
        result = await service._store_summaries([], target_dates)

        assert result == []


@pytest.mark.unit
def test_select_top_articles_with_custom_limit(mock_env_vars):
    """カスタムlimitが正しく適用されることをテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        # 10個の記事を作成
        articles = []
        for i in range(10):
            article = Article(
                feed_name="Test",
                title=f"記事{i}",
                url=f"https://example.com/{i}",
                text="本文",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=float(i),
                published_at=datetime.now(),
            )
            articles.append(article)

        # limit=5 で呼び出し
        result = service._select_top_articles(articles, limit=5)

        # 5個が返される
        assert len(result) == 5
        # 人気スコアの降順でソートされている
        assert result[0].popularity_score == 9.0
        assert result[4].popularity_score == 5.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_duplicate_article(mock_env_vars):
    """重複記事が正しくスキップされることをテスト"""
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
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "重複記事"
            mock_entry.link = "https://example.com/duplicate"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            # 重複として判定するDedupTrackerをモック
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (True, "normalized_title")
            mock_dedup.get_original_title.return_value = "元のタイトル"
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )

            result = await service.collect(days=1)

            # 重複記事はスキップされる
            assert result == []
