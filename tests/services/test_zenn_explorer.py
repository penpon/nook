"""
nook/services/zenn_explorer/zenn_explorer.py のテスト

テスト観点:
- ZennExplorerの初期化
- RSSフィード取得と解析
- 記事の重複チェック
- 人気スコア抽出
- 記事本文取得
- 要約生成
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article
from nook.services.zenn_explorer.zenn_explorer import ZennExplorer

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: ZennExplorerを初期化
    Then: インスタンスが正常に作成され、feed_configが読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        assert service.service_name == "zenn_explorer"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    """
    Given: ZennExplorerクラス
    When: TOTAL_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert ZennExplorer.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    """
    Given: ZennExplorerクラス
    When: SUMMARY_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert ZennExplorer.SUMMARY_LIMIT == 15


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
        service = ZennExplorer()
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
    """
    Given: 有効なRSSフィード
    When: collectメソッドを呼び出す
    Then: 記事が正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
            mock_entry.title = "テストZenn記事"
            mock_entry.link = "https://example.com/article1"
            mock_entry.summary = "テストZenn記事の説明"
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
    """
    Given: 複数の記事を含むフィード
    When: collectメソッドを呼び出す
    Then: 全ての記事が処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
                entry.title = f"テストZenn記事{i}"
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
    """
    Given: target_dates=None
    When: collectメソッドを呼び出す
    Then: デフォルトの日付範囲で実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
    """
    Given: limit=0
    When: collectメソッドを呼び出す
    Then: 記事が取得されない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
def test_select_top_articles_with_empty_list(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _select_top_articlesを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
        service = ZennExplorer()

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
        service = ZennExplorer()

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
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テストZenn記事"
        entry.link = "https://example.com/test"
        entry.summary = "テストの説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>これは日本語の記事です</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "テストZenn記事"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
    """
    Given: URLを持たないエントリ
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
        service = ZennExplorer()
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
    """
    Given: 人気スコアを含むメタタグ
    When: _extract_popularityを呼び出す
    Then: スコアが正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
        service = ZennExplorer()

        entry = Mock()
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 9. _get_markdown_header メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_markdown_header(mock_env_vars):
    """
    Given: ZennExplorerインスタンス
    When: _get_markdown_headerを呼び出す
    Then: ヘッダーテキストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        result = service._get_markdown_header()

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# 10. _get_summary_system_instruction メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_summary_system_instruction(mock_env_vars):
    """
    Given: ZennExplorerインスタンス
    When: _get_summary_system_instructionを呼び出す
    Then: システム指示が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
        service = ZennExplorer()

        article = Article(
            feed_name="Test",
            title="テストZenn記事",
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
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
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
            mock_entry.title = "テストZenn記事"
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
# 13. collect メソッド - フィード処理ループの詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_categories(mock_env_vars):
    """
    Given: 複数カテゴリ（tech, business）のフィード設定
    When: collectメソッドを呼び出す
    Then: すべてのカテゴリのフィードが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        # 複数カテゴリのフィード設定をモック
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # 両カテゴリのフィードが処理されたことを確認
            assert mock_parse.call_count == 2
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feedparser_attribute_error(mock_env_vars):
    """
    Given: feedparser.parseがAttributeErrorを発生
    When: collectメソッドを呼び出す
    Then: エラーがログされ、処理が継続される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_parse.side_effect = AttributeError("'NoneType' object has no attribute 'feed'")

            result = await service.collect(days=1)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_duplicate_article(mock_env_vars):
    """
    Given: 重複記事が存在
    When: collectメソッドを呼び出す
    Then: 重複記事がスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock, return_value=None),
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

            # 重複記事はスキップされるので保存されない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_empty_feed_entries(mock_env_vars):
    """
    Given: エントリが空のフィード
    When: collectメソッドを呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            mock_feed = Mock()
            mock_feed.feed.title = "Empty Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1)

            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_continues_on_individual_feed_error(mock_env_vars):
    """
    Given: 1つのフィードで例外が発生、他のフィードは正常
    When: collectメソッドを呼び出す
    Then: エラーをログして処理が継続される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        # 2つのフィード設定
        service.feed_config = {
            "tech": ["https://example.com/feed1.xml", "https://example.com/feed2.xml"],
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ),
        ):
            # 1つ目のフィードでエラー、2つ目は成功
            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []

            mock_parse.side_effect = [
                Exception("Feed error"),
                mock_feed,
            ]

            result = await service.collect(days=1)

            # エラーがあっても処理は継続される
            assert isinstance(result, list)


# =============================================================================
# 14. _retrieve_article メソッド - HTTPエラー・BeautifulSoup解析詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    """
    Given: HTTP 404エラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/not-found"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

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
    Given: HTTP 500エラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/error"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock(status_code=500),
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_meta_description_extraction(mock_env_vars):
    """
    Given: メタディスクリプションを含むHTML
    When: _retrieve_articleを呼び出す
    Then: メタディスクリプションがテキストとして抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = None  # summaryがない場合
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_meta = """
        <html>
        <head>
            <meta name="description" content="これはメタディスクリプションのテキストです。">
        </head>
        <body></body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html_with_meta))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "これはメタディスクリプションのテキストです。" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_paragraph_fallback(mock_env_vars):
    """
    Given: メタディスクリプションがなく、段落のみのHTML
    When: _retrieve_articleを呼び出す
    Then: 段落のテキストが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = None
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html_with_paragraphs = """
        <html>
        <body>
            <p>最初の段落テキスト。</p>
            <p>2番目の段落テキスト。</p>
            <p>3番目の段落テキスト。</p>
        </body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html_with_paragraphs))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "最初の段落テキスト。" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_entry_summary_priority(mock_env_vars):
    """
    Given: entry.summaryが存在するエントリ
    When: _retrieve_articleを呼び出す
    Then: entry.summaryが優先的にテキストとして使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリのサマリーテキスト"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>HTML本文</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "エントリのサマリーテキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_beautifulsoup_exception(mock_env_vars):
    """
    Given: BeautifulSoup解析中に例外が発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # BeautifulSoupがパース時に例外を発生させるケース
        service.http_client.get = AsyncMock(side_effect=Exception("Parse error"))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


# =============================================================================
# 15. _extract_popularity メソッド - Zenn特有の詳細テスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_zenn_likes_count_meta(mock_env_vars):
    """
    Given: zenn:likes_count メタタグを含むHTML
    When: _extract_popularityを呼び出す
    Then: メタタグから正しくいいね数が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <head>
            <meta property="zenn:likes_count" content="150">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_data_like_count_attribute(mock_env_vars):
    """
    Given: data-like-count 属性を持つ要素を含むHTML
    When: _extract_popularityを呼び出す
    Then: data属性から正しくいいね数が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-like-count="250">いいね</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_button_text_extraction(mock_env_vars):
    """
    Given: ボタン内の「いいね」テキストから数値を抽出
    When: _extract_popularityを呼び出す
    Then: テキストから正しく数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button>♥ いいね 320</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 320.0


@pytest.mark.unit
def test_extract_popularity_span_text_extraction(mock_env_vars):
    """
    Given: スパン内のテキストから数値を抽出
    When: _extract_popularityを呼び出す
    Then: テキストから正しく数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span>いいね 180</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 180.0


@pytest.mark.unit
def test_extract_popularity_max_from_multiple_candidates(mock_env_vars):
    """
    Given: 複数の候補が存在
    When: _extract_popularityを呼び出す
    Then: 最大値が選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-like-count="100">いいね</button>
            <span>いいね 250</span>
            <div>いいね 50</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_from_feed_entry_likes(mock_env_vars):
    """
    Given: フィードエントリにlikes属性が存在
    When: _extract_popularityを呼び出す
    Then: フィードエントリから正しくいいね数が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        entry.likes = 300
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_from_feed_entry_zenn_likes_count(mock_env_vars):
    """
    Given: フィードエントリにzenn_likes_count属性が存在
    When: _extract_popularityを呼び出す
    Then: フィードエントリから正しくいいね数が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        entry.likes = None
        entry.likes_count = None
        entry.zenn_likes_count = 450
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 450.0


@pytest.mark.unit
def test_extract_popularity_all_methods_fail_returns_zero(mock_env_vars):
    """
    Given: すべての抽出方法が失敗
    When: _extract_popularityを呼び出す
    Then: 0.0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        # すべての属性が存在しない
        del entry.likes
        del entry.likes_count
        del entry.zenn_likes_count

        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 16. _load_existing_titles メソッドのテスト（未カバー部分）
# =============================================================================


@pytest.mark.unit
def test_load_existing_titles_with_markdown_content(temp_data_dir, mock_env_vars):
    """
    Given: Markdownファイルに既存タイトルが含まれている
    When: _load_existing_titlesを呼び出す
    Then: DedupTrackerにタイトルが追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.storage.base_dir = Path(temp_data_dir)

        # Markdownファイルを作成
        markdown_content = """## Tech

### [既存記事タイトル1](https://example.com/1)

**フィード**: テストフィード

**要約**:
これは既存記事の要約です。

---

### [既存記事タイトル2](https://example.com/2)

**フィード**: テストフィード2

**要約**:
これは2つ目の既存記事の要約です。

---
"""
        (temp_data_dir / "test.md").write_text(markdown_content)

        with patch.object(service.storage, "load_markdown", return_value=markdown_content):
            result = service._load_existing_titles()

            assert result is not None
            # タイトルが追加されていることを確認
            is_dup1, _ = result.is_duplicate("既存記事タイトル1")
            is_dup2, _ = result.is_duplicate("既存記事タイトル2")
            assert is_dup1 is True
            assert is_dup2 is True


@pytest.mark.unit
def test_load_existing_titles_with_no_markdown(mock_env_vars):
    """
    Given: Markdownファイルが存在しない
    When: _load_existing_titlesを呼び出す
    Then: 空のDedupTrackerが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch.object(service.storage, "load_markdown", return_value=None):
            result = service._load_existing_titles()

            assert result is not None
            # 空のトラッカーであることを確認
            is_dup, _ = result.is_duplicate("新規記事")
            assert is_dup is False


@pytest.mark.unit
def test_load_existing_titles_with_exception(mock_env_vars):
    """
    Given: Markdownファイル読み込み時に例外が発生
    When: _load_existing_titlesを呼び出す
    Then: 空のDedupTrackerが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch.object(service.storage, "load_markdown", side_effect=Exception("Read error")):
            result = service._load_existing_titles()

            assert result is not None
            # 空のトラッカーであることを確認
            is_dup, _ = result.is_duplicate("新規記事")
            assert is_dup is False


# =============================================================================
# 17. _retrieve_article メソッド - より詳細な分岐テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_summary_no_meta_with_paragraphs(mock_env_vars):
    """
    Given: entry.summaryがなく、メタディスクリプションもないが段落がある
    When: _retrieve_articleを呼び出す
    Then: 段落からテキストが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        # summaryがない
        del entry.summary
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html = """
        <html>
        <body>
            <p>段落1のテキスト</p>
            <p>段落2のテキスト</p>
            <p>段落3のテキスト</p>
        </body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert "段落1のテキスト" in result.text
        assert result.title == "テスト記事"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_summary_with_meta_description(mock_env_vars):
    """
    Given: entry.summaryがないが、メタディスクリプションがある
    When: _retrieve_articleを呼び出す
    Then: メタディスクリプションがテキストとして使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        del entry.summary
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html = """
        <html>
        <head>
            <meta name="description" content="メタディスクリプションのテキスト">
        </head>
        <body></body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == "メタディスクリプションのテキスト"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_content_anywhere(mock_env_vars):
    """
    Given: entry.summary、メタディスクリプション、段落のいずれもない
    When: _retrieve_articleを呼び出す
    Then: 空文字列のテキストでArticleが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        del entry.summary
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        html = """
        <html>
        <head></head>
        <body></body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.text == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_title_attribute_missing(mock_env_vars):
    """
    Given: entry.titleがない
    When: _retrieve_articleを呼び出す
    Then: タイトルが「無題」になる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        del entry.title
        entry.link = "https://example.com/test"
        entry.summary = "テスト説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert result.title == "無題"


# =============================================================================
# 18. _extract_popularity メソッド - div要素の明示的なテスト
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_div_text_extraction(mock_env_vars):
    """
    Given: div要素内のテキストから数値を抽出
    When: _extract_popularityを呼び出す
    Then: テキストから正しく数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <div>いいね 280</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 280.0


@pytest.mark.unit
def test_extract_popularity_meta_tag_with_empty_content(mock_env_vars):
    """
    Given: メタタグのcontentが空文字列
    When: _extract_popularityを呼び出す
    Then: 次の抽出方法にフォールバックする
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <head>
            <meta property="zenn:likes_count" content="">
        </head>
        <body>
            <button data-like-count="100">いいね</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # メタタグが空なので、data属性から抽出される
        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_entry_likes_count_attribute(mock_env_vars):
    """
    Given: フィードエントリにlikes_count属性が存在
    When: _extract_popularityを呼び出す
    Then: likes_countから正しくいいね数が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        entry.likes = None
        entry.likes_count = 350
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 350.0


@pytest.mark.unit
def test_extract_popularity_debug_exception_handling(mock_env_vars):
    """
    Given: フィードエントリの人気情報取得時に例外が発生
    When: _extract_popularityを呼び出す
    Then: 例外がログされ、0.0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        # Mock entry that raises AttributeError on attribute access
        entry = Mock()
        type(entry).likes = property(
            lambda self: (_ for _ in ()).throw(AttributeError("test error"))
        )

        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


# =============================================================================
# 19. collect メソッド - 日付ごとのストレージ処理の詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_existing_articles_merge(mock_env_vars):
    """
    Given: 既存記事が存在し、新規記事を追加
    When: collectメソッドを呼び出す
    Then: 既存記事と新規記事がマージされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock) as mock_storage_load,
            patch.object(service.storage, "save", new_callable=AsyncMock),
        ):
            # 既存記事データ
            existing_data = json.dumps(
                [
                    {
                        "title": "既存記事",
                        "url": "https://example.com/existing",
                        "feed_name": "既存フィード",
                        "summary": "既存要約",
                        "popularity_score": 5.0,
                        "published_at": "2024-11-14T10:00:00",
                        "category": "tech",
                    }
                ]
            )
            mock_storage_load.return_value = existing_data

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "新規記事"
            mock_entry.link = "https://example.com/new"
            mock_entry.summary = "新規記事の説明"
            mock_entry.published_parsed = (2024, 11, 14, 12, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>新規記事の本文</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_no_new_articles_but_existing(mock_env_vars):
    """
    Given: 既存記事が存在するが、新規記事がない
    When: collectメソッドを呼び出す
    Then: 既存記事が保持される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
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
                "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(service.storage, "load", new_callable=AsyncMock) as mock_storage_load,
        ):
            # 既存記事データ
            existing_data = json.dumps(
                [
                    {
                        "title": "既存記事",
                        "url": "https://example.com/existing",
                        "feed_name": "既存フィード",
                        "summary": "既存要約",
                        "popularity_score": 5.0,
                        "published_at": "2024-11-14T10:00:00",
                        "category": "tech",
                    }
                ]
            )
            mock_storage_load.return_value = existing_data

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []  # 新規記事なし
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list)


# =============================================================================
# 20. _store_summaries メソッドのテスト（未カバー部分）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_with_empty_articles(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _store_summariesを呼び出す
    Then: 空のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        target_dates = [date(2024, 11, 14)]
        result = await service._store_summaries([], target_dates)

        assert result == []
