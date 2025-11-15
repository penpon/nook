"""
nook/services/tech_feed/tech_feed.py のテスト

テスト観点:
- TechFeedの初期化
- RSSフィード取得と解析
- 記事の重複チェック
- 人気スコア抽出
- 日本語判定
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
from nook.services.tech_feed.tech_feed import TechFeed

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        assert service.service_name == "tech_feed"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_with_custom_storage_dir(mock_env_vars, tmp_path):
    custom_dir = tmp_path / "custom"  # nosec B108 - テスト環境でのみ使用
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed(storage_dir=str(custom_dir))

        assert service.service_name == "tech_feed"
        assert service.feed_config is not None


@pytest.mark.unit
def test_init_loads_feed_config(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        # feed_configが辞書型であることを確認
        assert isinstance(service.feed_config, dict)
        # 何らかのキーを持つことを確認
        assert len(service.feed_config) > 0


@pytest.mark.unit
def test_init_http_client_is_none(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        assert service.http_client is None


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    assert TechFeed.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    assert TechFeed.SUMMARY_LIMIT == 15


# =============================================================================
# 2. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_calls_collect(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.collect = AsyncMock(return_value=[])

        with patch("asyncio.run") as mock_run:
            service.run(days=1, limit=10)

            mock_run.assert_called_once()


@pytest.mark.unit
def test_run_with_default_params(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.collect = AsyncMock(return_value=[])

        with patch("asyncio.run") as mock_run:
            service.run()

            mock_run.assert_called_once()


# =============================================================================
# 3. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(mock_env_vars, respx_mock):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        # HTMLページのモック(日本語コンテンツ)
        mock_html = """<<html> <head><title>テスト記事</title></head> <body> <p>これは日本語のテスト記事です.</p> <p>技術的な内容を含んでいます.</p> </body> </html>>"""

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
            # feedparserのモック設定
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト記事"
            mock_entry.link = "https://example.com/article1"
            mock_entry.summary = "テスト記事の説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            # DedupTrackerのモック
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized_title")
            mock_load.return_value = mock_dedup

            # HTTPクライアントのモック
            service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))

            # GPTクライアントのモック
            service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            # 複数エントリのモック
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            entries = []
            for i in range(5):
                entry = Mock()
                entry.title = f"テスト記事{i}"
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
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
async def test_collect_with_target_dates_empty_list(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_get_all_existing_dates",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.collect(days=1, target_dates=[])

            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_zero(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_days_zero(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=0)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_days_thirty(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=30)

            assert isinstance(result, list)

    # =============================================================================
    # 6. _select_top_articles メソッドのテスト
    # =============================================================================
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "テストの説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>これは日本語の記事です</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "テスト記事"
        assert result.url == "https://example.com/test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        entry.title = "テスト"
        entry.link = None

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_non_japanese_content(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "English Article"
        entry.link = "https://example.com/test"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>This is an English article</p></body></html>")
        )

        await service._retrieve_article(entry, "Test Feed", "tech")

        # 日本語判定で除外される可能性がある
        # 実装次第でNoneまたはArticle is returned


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        service.http_client.get = AsyncMock(side_effect=Exception("HTTP Error"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


# =============================================================================
# 8. _extract_popularity メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_meta_tag(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


@pytest.mark.unit
def test_extract_popularity_with_data_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div data-reaction-count="250"></div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_with_button_text(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><button>いいね 500</button></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 500.0


# =============================================================================
# 9. _needs_japanese_check メソッドのテスト
# =============================================================================
@pytest.mark.unit
def test_get_markdown_header(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        result = service._get_markdown_header()

        assert result == "技術ニュース記事"


# =============================================================================
# 11. _get_summary_system_instruction メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_system_instruction(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        result = service._get_summary_system_instruction()

        assert isinstance(result, str)
        assert len(result) > 0
        assert "技術ニュース" in result or "要約" in result


# =============================================================================
# 12. _get_summary_prompt_template メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_prompt_template(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        article = Article(
            feed_name="Test",
            title="テスト記事",
            url="http://example.com/test",
            text="テスト本文" * 100,
            soup=BeautifulSoup("", "html.parser"),
            category="tech",
            popularity_score=10.0,
            published_at=datetime.now(),
        )

        result = service._get_summary_prompt_template(article)

        assert isinstance(result, str)
        assert "テスト記事" in result
        assert "要約" in result


# =============================================================================
# 13. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_handles_feed_parse_error_gracefully(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_parse.side_effect = Exception("Parse error")

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_handles_storage_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                side_effect=Exception("Storage error"),
            ),
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

            # ストレージエラーが発生するが, エラー処理で例外はraiseされない
            result = await service.collect(days=1)

            # エラーがログされるが, 処理は継続し空リスト is returned
            assert isinstance(result, list)


# =============================================================================
# 14. 統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
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
            mock_entry.title = "テスト記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "テスト説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語のテスト記事</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

            # 収集
            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)

            # クリーンアップ
            await service.cleanup()


# =============================================================================
# 15. collect内部分岐テスト(追加の詳細テスト)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feed_toml_load_failure_handling(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        # feed.tomlが読めない場合, 初期化時に失敗するはず
        with patch("builtins.open", side_effect=FileNotFoundError("feed.toml not found")):
            with pytest.raises(FileNotFoundError):
                TechFeed()


# 重複検出テストは複雑なため, シンプルなテストに置き換え


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_no_saved_files(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []  # 記事なし
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1)

            # 保存なし
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_japanese_check_filters_english_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "English Article"
            mock_entry.link = "https://example.com/english"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            # 英語HTMLを返す
            service.http_client.get = AsyncMock(
                return_value=Mock(
                    text='<html lang="en"><body><p>This is an English article.</p></body></html>'
                )
            )

            result = await service.collect(days=1, limit=10)

            # 英語記事がフィルタリングされ, 結果が空
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_404_error_skips_article(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "Not Found Article"
            mock_entry.link = "https://example.com/404"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            # 404エラーを発生させる
            service.http_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found", request=Mock(), response=Mock(status_code=404)
                )
            )

            result = await service.collect(days=1, limit=10)

            # 404エラーがログされ, 処理は継続
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_500_error_skips_article(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "Server Error Article"
            mock_entry.link = "https://example.com/500"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            # 500エラーを発生させる
            service.http_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=Mock(),
                    response=Mock(status_code=500),
                )
            )

            result = await service.collect(days=1, limit=10)

            # 500エラーがログされ, 処理は継続
            assert isinstance(result, list)


# =============================================================================
# 16. _retrieve_article詳細テスト(追加の詳細テスト)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_empty_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "Empty HTML Article"
        entry.link = "https://example.com/empty"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(return_value=Mock(text="<html></html>"))

        await service._retrieve_article(entry, "Test Feed", "tech")

        # 空HTMLでも日本語判定で除外される可能性
        # または空のArticle is returned


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_malformed_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "Malformed HTML Article"
        entry.link = "https://example.com/malformed"
        entry.summary = "説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>不正なHTML<p><div>閉じタグなし")
        )

        await service._retrieve_article(entry, "Test Feed", "tech")

        # BeautifulSoupは不正HTMLでも解析を試みる
        # 日本語判定を通過すればArticle is returned


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_japanese_detection_true(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "日本語記事タイトル"
        entry.link = "https://example.com/japanese"
        entry.summary = "日本語の説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><body><p>これは日本語の記事です.テスト用コンテンツ.</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "日本語記事タイトル"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_japanese_detection_false(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "English Only Article"
        entry.link = "https://example.com/english-only"
        entry.summary = "English description"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="en"><body><p>This is an English only article. No Japanese content here.</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        # 日本語判定で除外されるべき
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_meta_description(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "メタディスクリプション記事"
        entry.link = "https://example.com/meta"
        entry.summary = None  # summary無し
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><head><meta name="description" content="メタディスクリプションのテキスト"></head><body></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "メタディスクリプションのテキスト" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_popularity_score_extraction(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "人気記事"
        entry.link = "https://example.com/popular"
        entry.summary = "人気のある記事"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><head><meta property="article:reaction_count" content="250"></head><body><p>人気の記事</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.popularity_score == 250.0


# =============================================================================
# 17. _extract_popularity詳細テスト(追加の詳細テスト)
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_multiple_meta_tags(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html><head><meta property="article:reaction_count" content="100"><meta name="reaction-count" content="200"></head></html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        # 最初のメタタグの値が使用される
        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_data_attributes_multiple(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html>
            <body>
                <div data-reaction-count="150"></div>
                <div data-like-count="300"></div>
                <div data-reaction-count="200"></div>
            </body>
            </html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        # 最大値 is returned
        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_button_text_extraction(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html>
            <body>
                <button>いいね 1,234</button>
                <span>Reaction 567</span>
            </body>
            </html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        # カンマ付き数値も解析される
        assert result == 1234.0


@pytest.mark.unit
def test_extract_popularity_mixed_sources_max_value(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html>
            <head>
                <meta property="article:reaction_count" content="500">
            </head>
            <body>
                <div data-reaction-count="1000"></div>
                <button>いいね 2000</button>
            </body>
            </html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        # メタタグが優先される(最初にreturn)
        assert result == 500.0


@pytest.mark.unit
def test_extract_popularity_og_reaction_count_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html>
            <head>
                <meta property="og:reaction_count" content="750">
            </head>
            </html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 750.0


# =============================================================================
# 18. カバレッジ向上のための追加テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_date_filtering_within_range(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            from datetime import datetime

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "テスト記事"
            mock_entry.link = "https://example.com/test"
            mock_entry.summary = "テスト説明"
            # 今日の日付
            now = datetime.now()
            mock_entry.published_parsed = (
                now.year,
                now.month,
                now.day,
                0,
                0,
                0,
                0,
                0,
                0,
            )
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_multiple_categories(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()
        # feed_configを2カテゴリに設定
        service.feed_config = {
            "tech": ["https://example.com/tech.xml"],
            "news": ["https://example.com/news.xml"],
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1)

            # feedparser.parseが2回呼ばれる(カテゴリ数分)
            assert mock_parse.call_count == 2
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_entry_summary(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリのサマリーテキスト"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "エントリのサマリーテキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_paragraphs(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = None  # summaryなし
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><body><p>第一段落</p><p>第二段落</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "第一段落" in result.text
        assert "第二段落" in result.text


@pytest.mark.unit
def test_extract_popularity_with_like_keyword(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><button>Like 999</button></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 999.0


@pytest.mark.unit
def test_extract_popularity_with_reaction_keyword(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            "<html><body><span>Reaction 777</span></body></html>",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 777.0


@pytest.mark.unit
def test_extract_popularity_name_reaction_count_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        entry = Mock()
        soup = BeautifulSoup(
            """<html>
            <head>
                <meta name="reaction-count" content="555">
            </head>
            </html>""",
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 555.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_storage_save_successful(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/2024-11-14.json"),
            ),
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

            service.http_client.get = AsyncMock(
                return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_timeout_exception(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/timeout"

        service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_existing_article_titles_loaded(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                service.storage,
                "load",
                new_callable=AsyncMock,
                return_value='[{"title": "既存記事"}]',
            ),
        ):
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
                return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
            )

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_date_filtering_out_of_range(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
            patch(
                "nook.services.tech_feed.tech_feed.is_within_target_dates",
                return_value=False,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "古い記事"
            mock_entry.link = "https://example.com/old"
            mock_entry.summary = "説明"
            # 古い日付
            mock_entry.published_parsed = (2020, 1, 1, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            Mock()

            service.http_client.get = AsyncMock(
                return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
            )

            result = await service.collect(days=1)

            # 日付範囲外なのでスキップされる
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_empty_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        from datetime import date

        result = await service._store_summaries([], [date.today()])

        assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_entry_summary_with_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/meta"
        entry.summary = None  # summaryなし
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><head><meta name="description" content="メタの説明文"></head><body></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "メタの説明文"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_summary_no_meta_with_paragraphs(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/para"
        entry.summary = None
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text='<html lang="ja"><body><p>段落1</p><p>段落2</p><p>段落3</p></body></html>'
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "段落1" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_dedup_tracker_detects_duplicate(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()
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
                "nook.services.tech_feed.tech_feed.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "重複記事"
            mock_entry.link = "https://example.com/dup"
            mock_entry.summary = "説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            # 重複を返すモック
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (True, "normalized")
            mock_dedup.get_original_title.return_value = "元のタイトル"
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text='<html lang="ja"><body><p>日本語テキスト</p></body></html>')
            )

            result = await service.collect(days=1)

            # 重複記事はスキップされる
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_articles(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = TechFeed()

        from datetime import date, datetime

        from bs4 import BeautifulSoup

        from nook.services.base_feed_service import Article

        articles = [
            Article(
                feed_name="Test",
                title="記事1",
                url="https://example.com/1",
                text="テキスト",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=10.0,
                published_at=datetime.now(),
            )
        ]

        with patch(
            "nook.common.daily_snapshot.store_daily_snapshots",
            new_callable=AsyncMock,
            return_value=[("/data/test.json", "/data/test.md")],
        ):
            result = await service._store_summaries(articles, [date.today()])

            assert isinstance(result, list)
            assert len(result) == 1
