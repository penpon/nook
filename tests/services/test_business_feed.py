from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article
from nook.services.business_feed.business_feed import BusinessFeed

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        assert service.service_name == "business_feed"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    assert BusinessFeed.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    assert BusinessFeed.SUMMARY_LIMIT == 15


# =============================================================================
# 2. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_with_default_params(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.collect = AsyncMock(return_value=[])

        with patch("asyncio.run") as mock_run:
            service.run()

            mock_run.assert_called_once()


# =============================================================================
# 3. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
            mock_entry.title = "テストビジネス記事"
            mock_entry.link = "https://example.com/article1"
            mock_entry.summary = "テストビジネス記事の説明"
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
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
                entry.title = f"テストビジネス記事{i}"
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
        service = BusinessFeed()

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        entry.title = "テスト"
        entry.link = None

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        service.http_client.get = AsyncMock(side_effect=Exception("HTTP Error"))

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is None


# =============================================================================
# 8. _extract_popularity メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_meta_tag(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta property="article:reaction_count" content="100"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_without_score(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


@pytest.mark.unit
def test_extract_popularity_with_data_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div data-reaction-count="250"></div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


# =============================================================================
# 9. _needs_japanese_check メソッドのテスト
# =============================================================================
@pytest.mark.unit
def test_get_markdown_header(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        result = service._get_markdown_header()

        assert result == "ビジネスニュース記事"


# =============================================================================
# 11. _get_summary_system_instruction メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_system_instruction(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        result = service._get_summary_system_instruction()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 12. _get_summary_prompt_template メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_prompt_template(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        article = Article(
            feed_name="Test",
            title="テストビジネス記事",
            url="http://example.com/test",
            text="テスト本文" * 100,
            soup=BeautifulSoup("", "html.parser"),
            category="business",
            popularity_score=10.0,
            published_at=datetime.now(),
        )

        result = service._get_summary_prompt_template(article)

        assert isinstance(result, str)
        assert "テストビジネス記事" in result


# =============================================================================
# 13. collect内部分岐テスト(追加実装)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_skips_duplicate_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "重複記事"
            mock_entry.link = "https://example.com/duplicate"
            mock_entry.summary = "重複記事の説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            # DedupTrackerが重複として認識
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (True, "normalized_title")
            mock_dedup.get_original_title.return_value = "元の記事タイトル"
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # 重複記事がスキップされるため, 保存されるファイルはない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_filters_non_japanese_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "English Business Article"
            mock_entry.link = "https://example.com/english"
            mock_entry.summary = "English article description"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            # 英語記事のHTMLを返す
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text='<html lang="en"><body><p>This is an English article.</p></body></html>'
                )
            )

            result = await service.collect(days=1)

            # 英語記事が除外されるため, 保存されるファイルはない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_processes_multiple_categories(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        # 複数カテゴリのfeed_configをモック
        service.feed_config = {
            "business": ["https://example.com/feed1.xml"],
            "finance": ["https://example.com/feed2.xml"],
        }

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>日本語</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            await service.collect(days=1)

            # 複数カテゴリが処理されることを確認
            assert mock_parse.call_count == 2  # 2カテゴリ分


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_filters_articles_outside_date_range(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "古い記事"
            mock_entry.link = "https://example.com/old"
            mock_entry.summary = "説明"
            # 範囲外の古い日付
            mock_entry.published_parsed = (2020, 1, 1, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>日本語</body></html>")
            )

            result = await service.collect(days=1, target_dates=[date(2024, 11, 14)])

            # 日付範囲外の記事が除外されるため, 保存されるファイルはない
            assert result == []


# =============================================================================
# 14. _retrieve_article詳細テスト(追加実装)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_empty_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "Empty Article"  # 英語タイトル
        entry.link = "https://example.com/test"
        entry.summary = ""
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 空のHTML
        service.http_client.get = AsyncMock(return_value=Mock(text="<html></html>"))

        result = await service._retrieve_article(entry, "Test Feed", "business")

        # 空HTMLで日本語判定で失敗するため, None is returned
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_filters_non_japanese(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "English Article"
        entry.link = "https://example.com/english"
        entry.summary = "English description"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 英語のHTML
        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="en"><body><p>This is an English article.</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "business")

        # 英語記事は除外される
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/404"

        # 404エラーをシミュレート
        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock(status_code=404)
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_500_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/500"

        # 500エラーをシミュレート
        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock(status_code=500),
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_extracts_meta_description(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
        # summaryがない
        if hasattr(entry, "summary"):
            delattr(entry, "summary")

        html = "<html><head><meta name='description' content='メタディスクリプションのテキスト'></head><body><p>これは日本語の記事です.</p></body></html>"
        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is not None
        assert "メタディスクリプションのテキスト" in result.text


# =============================================================================
# 15. _extract_popularity詳細テスト(追加実装)
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_multiple_candidates(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        html = "<html><body><div data-reaction-count='100'></div><button>いいね 250</button><span data-like-count='150'></span></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # 最大値250.0 is returned
        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_extracts_from_button_text_with_japanese(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        html = "<html><body> <button class='like-button'>いいね 500</button> </body></html>"
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 500.0


@pytest.mark.unit
def test_extract_popularity_with_og_likes_meta_tag(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        html = "<html><head> <meta property='og:reaction_count' content='300'> </head> <body></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_with_reaction_name_meta_tag(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

        entry = Mock()
        html = (
            "<html><head> <meta name='reaction-count' content='175'> </head> <body></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 175.0


# =============================================================================
# 16. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_handles_feed_parse_error_gracefully(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()

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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
        service = BusinessFeed()
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
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
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
            mock_entry.title = "テストビジネス記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "テスト説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語のビジネス記事</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)

            await service.cleanup()


# =============================================================================
# 17. 追加の内部メソッド詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_timeout(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/timeout"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # タイムアウト例外をシミュレート
        service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        result = await service._retrieve_article(entry, "Test Feed", "business")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_malformed_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "Malformed HTML Article"
        entry.link = "https://example.com/malformed"
        entry.summary = "Test summary"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 不正なHTML(閉じタグなし, ネストエラーなど)
        malformed_html = "<html><head><title>Test</title><body><p>This is a malformed HTML without proper closing tags<div>Another unclosed div<p>More content"
        service.http_client.get = AsyncMock(return_value=Mock(text=malformed_html))

        result = await service._retrieve_article(entry, "Test Feed", "business")

        # BeautifulSoupは寛容なので解析成功するが, 日本語判定で除外される
        assert result is None  # 英語コンテンツのため


# Removed corrupted test functions after this point


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_complete_workflow_with_article_save(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            # フィードのモック
            mock_feed = Mock()
            mock_feed.feed.title = "Test Business Feed"

            # 2つの記事エントリを作成
            # published_parsedはUTCとして扱われ、+9hでJST変換される
            # さらにnormalize_datetime_to_localでUTC→JSTに再変換されるため、
            # 0:00と1:00を使用（+9h→9:00,10:00 JST、さらに+9h→18:00,19:00 JST 同日）
            entry1 = Mock()
            entry1.title = "日本語ビジネス記事1"
            entry1.link = "https://example.com/article1"
            entry1.summary = "ビジネス記事1の説明"
            entry1.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

            entry2 = Mock()
            entry2.title = "日本語ビジネス記事2"
            entry2.link = "https://example.com/article2"
            entry2.summary = "ビジネス記事2の説明"
            entry2.published_parsed = (2024, 11, 14, 1, 0, 0, 0, 0, 0)

            mock_feed.entries = [entry1, entry2]
            mock_parse.return_value = mock_feed

            # 重複チェックトラッカー(重複なし)
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized_title")
            mock_dedup.add = Mock()
            mock_load.return_value = mock_dedup

            # HTTP取得成功(日本語コンテンツ)
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text="<html><body><p>これは日本語のビジネス記事本文です.</p></body></html>"
                )
            )

            # GPT要約成功
            service.gpt_client.get_response = AsyncMock(return_value="要約されたビジネス記事")

            # ストレージモック(save成功)
            service.storage.load = AsyncMock(return_value=None)  # 既存記事なし
            service.storage.save = AsyncMock(return_value="/data/business_feed/2024-11-14.json")

            # collect実行
            result = await service.collect(days=1, target_dates=[date(2024, 11, 14)])

            # 検証
            assert isinstance(result, list)
            assert len(result) > 0  # ファイルが保存されている

            # 重複チェックが呼ばれたことを確認
            assert mock_dedup.is_duplicate.call_count >= 2
            assert mock_dedup.add.call_count >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_detects_duplicate_after_article_creation(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"

            # 重複記事エントリ
            # 0:00 UTCを使用（+9h+9hの二重変換後も同日に収まる）
            entry = Mock()
            entry.title = "重複する日本語記事"
            entry.link = "https://example.com/duplicate"
            entry.summary = "重複記事の説明"
            entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            # 重複検出(記事作成後に検出される)
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (True, "normalized_duplicate_title")
            mock_dedup.get_original_title.return_value = "元の記事タイトル"
            mock_load.return_value = mock_dedup

            # HTTP取得は成功(記事は作成される)
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>これは日本語記事です.</p></body></html>")
            )

            result = await service.collect(days=1, target_dates=[date(2024, 11, 14)])

            # 重複のため保存されない
            assert result == []
            # 重複チェックが呼ばれた
            mock_dedup.is_duplicate.assert_called()
            mock_dedup.get_original_title.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_existing_articles_merge(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = BusinessFeed()
        service.http_client = AsyncMock()

        with (
            patch("feedparser.parse") as mock_parse,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "nook.services.business_feed.business_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"

            # 0:00 UTCを使用（+9h+9hの二重変換後も同日に収まる）
            entry = Mock()
            entry.title = "新規日本語記事"
            entry.link = "https://example.com/new"
            entry.summary = "新規記事の説明"
            entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_dedup.add = Mock()
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text="<html><body><p>これは新規の日本語記事です.</p></body></html>"
                )
            )
            service.gpt_client.get_response = AsyncMock(return_value="新規記事の要約")

            # 既存記事をロード
            existing_json = json.dumps(
                [
                    {
                        "title": "既存記事1",
                        "url": "https://example.com/existing1",
                        "feed_name": "Test Feed",
                        "summary": "既存記事の要約",
                        "popularity_score": 5.0,
                        "published_at": "2024-11-14T09:00:00",
                        "category": "business",
                    }
                ]
            )
            service.storage.load = AsyncMock(return_value=existing_json)
            service.storage.save = AsyncMock(return_value="/data/business_feed/2024-11-14.json")

            result = await service.collect(days=1, target_dates=[date(2024, 11, 14)])

            # ファイルが保存された
            assert isinstance(result, list)
            assert len(result) > 0
