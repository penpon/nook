"""
nook/services/note_explorer/note_explorer.py のテスト

テスト観点:
- NoteExplorerの初期化
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
from nook.services.note_explorer.note_explorer import NoteExplorer

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        assert service.service_name == "note_explorer"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    assert NoteExplorer.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    assert NoteExplorer.SUMMARY_LIMIT == 15


# =============================================================================
# 2. run メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_run_with_default_params(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
            mock_entry.title = "テストnote記事"
            mock_entry.link = "https://example.com/article1"
            mock_entry.summary = "テストnote記事の説明"
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
                entry.title = f"テストnote記事{i}"
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
        service = NoteExplorer()

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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

        entry = Mock()
        entry.title = "テスト"
        entry.link = None

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        service.http_client.get = AsyncMock(side_effect=Exception("HTTP Error"))

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is None


# =============================================================================
# 8. _extract_popularity メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_meta_tag(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

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
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 9. _get_markdown_header メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_markdown_header(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        result = service._get_markdown_header()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 10. _get_summary_system_instruction メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_system_instruction(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        result = service._get_summary_system_instruction()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 11. _get_summary_prompt_template メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_prompt_template(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        article = Article(
            feed_name="Test",
            title="テストnote記事",
            url="http://example.com/test",
            text="テスト本文" * 100,
            soup=BeautifulSoup("", "html.parser"),
            category="general",
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
        service = NoteExplorer()

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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
            mock_entry.title = "テストnote記事"
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
# 13. collect メソッドの追加詳細テスト - フィード処理ループ・重複チェック
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feed_toml_load_failure(mock_env_vars):
    with (
        patch("nook.common.base_service.setup_logger"),
        patch("builtins.open", side_effect=FileNotFoundError("feed.toml not found")),
        pytest.raises(FileNotFoundError),
    ):
        NoteExplorer()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_duplicate_detection(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load_func,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            # DedupTrackerのモックを作成
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized_title")
            mock_dedup.add = Mock()
            mock_load_func.return_value = mock_dedup

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"

            entry = Mock()
            entry.title = "テスト記事"
            entry.link = "https://example.com/article"
            entry.summary = "説明"
            entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            # load_existing_titles_from_storageが呼ばれたことを確認
            assert mock_load_func.called
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_date_out_of_range(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"

            # 古い日付の記事(範囲外)
            entry = Mock()
            entry.title = "古い記事"
            entry.link = "https://example.com/old"
            entry.summary = "古い記事の説明"
            entry.published_parsed = (2020, 1, 1, 0, 0, 0, 0, 0, 0)  # 2020年

            mock_feed.entries = [entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            # days=1で今日の記事のみ対象
            result = await service.collect(days=1, limit=10)

            # 範囲外なので保存されない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_storage_save_failure(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                side_effect=Exception("Save failed"),
            ),
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
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            # 例外が発生しないことを確認
            result = await service.collect(days=1, limit=10)

            # エラーが発生しても空リスト is returned可能性がある
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_multiple_categories_loop(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        # 複数カテゴリを設定
        service.feed_config = {
            "tech": ["https://example.com/tech.xml"],
            "business": ["https://example.com/business.xml"],
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            await service.collect(days=1, limit=10)

            # 2つのカテゴリ分, feedparser.parseが2回呼ばれることを確認
            assert mock_parse.call_count == 2


# =============================================================================
# 14. _retrieve_article メソッドの追加詳細テスト - HTTPエラー・HTML解析
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        # 404エラーをシミュレート
        response_mock = Mock()
        response_mock.status_code = 404
        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=response_mock
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_500_error(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        # 500エラーをシミュレート
        response_mock = Mock()
        response_mock.status_code = 500
        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Internal Server Error", request=Mock(), response=response_mock
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_empty_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリの要約"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 空のHTML
        service.http_client.get = AsyncMock(return_value=Mock(text="<html><body></body></html>"))

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert isinstance(result, Article)
        # 空HTMLの場合, entry.summaryが使われる
        assert result.text == "エントリの要約"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_malformed_html(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリの要約"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 不正なHTML(タグが閉じていない等)
        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>テキスト</body>")  # pタグが閉じていない
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert isinstance(result, Article)
        # BeautifulSoupは寛容なので, 何らかのテキストが取得される
        assert len(result.text) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_extracts_meta_description(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        # summaryがない場合
        if hasattr(entry, "summary"):
            del entry.summary
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # メタディスクリプション付きHTML
        html = "<html><head><meta name='description' content='これはメタディスクリプションです.'></head><body></body></html>"
        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert result.text == "これはメタディスクリプションです."


# =============================================================================
# 15. _extract_popularity メソッドの追加詳細テスト - note特有の抽出
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_note_likes_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta name="note:likes" content="250"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_with_twitter_data1_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta name="twitter:data1" content="150 likes"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_with_note_likes_count_meta(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><head><meta name="note:likes_count" content="350"></head></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 350.0


@pytest.mark.unit
def test_extract_popularity_with_data_like_count_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><button data-like-count="180">HEART いいね</button></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 180.0


@pytest.mark.unit
def test_extract_popularity_with_data_supporter_count_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div data-supporter-count="75">サポーター</div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 75.0


@pytest.mark.unit
def test_extract_popularity_with_data_suki_count_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><span data-suki-count="220">スキ</span></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 220.0


@pytest.mark.unit
def test_extract_popularity_from_button_text_with_suki(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><button class="like-button">スキ 95</button></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 95.0


@pytest.mark.unit
def test_extract_popularity_from_span_text_with_iine(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><span class="like-span">いいね 120</span></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 120.0


@pytest.mark.unit
def test_extract_popularity_from_div_text_with_likes(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><div class="likes">300 likes</div></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_multiple_candidates_returns_max(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        # 複数の候補：data-like-count=100, スキ 50, いいね 200
        html = "<html><body><button data-like-count='100'>HEART</button><span class='suki-count'>スキ 50</span><div class='like-div'>いいね 200</div></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # 最大値の200 is returned
        assert result == 200.0


@pytest.mark.unit
def test_extract_popularity_from_entry_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        entry.likes = 500
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 500.0


@pytest.mark.unit
def test_extract_popularity_from_entry_likes_count_attribute(mock_env_vars):
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        entry.likes = None  # likesがNoneの場合にlikes_countが評価される
        entry.likes_count = 450
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 450.0


# =============================================================================
# 未カバー部分の追加テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_existing_json_parse_error(mock_env_vars):
    """既存記事JSONのパースエラー処理をテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

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
        assert len(result) == NoteExplorer.SUMMARY_LIMIT
        # 人気スコアの降順でソートされている
        assert result[0].popularity_score == 19.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_articles(mock_env_vars):
    """_store_summariesメソッドの正常系をテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

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
                return_value=Path("data/note_explorer/2024-11-14.json"),
            ),
            patch.object(
                service,
                "save_markdown",
                new_callable=AsyncMock,
                return_value=Path("data/note_explorer/2024-11-14.md"),
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
        service = NoteExplorer()

        from datetime import date

        target_dates = [date(2024, 11, 14)]
        result = await service._store_summaries([], target_dates)

        assert result == []


@pytest.mark.unit
def test_select_top_articles_with_custom_limit(mock_env_vars):
    """カスタムlimitが正しく適用されることをテスト"""
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

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
        service = NoteExplorer()
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
                "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
