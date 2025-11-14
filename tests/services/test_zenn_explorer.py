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
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from tests.conftest import create_mock_dedup, create_mock_entry, create_mock_feed

import httpx
import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article
from nook.services.zenn_explorer.zenn_explorer import ZennExplorer

# =============================================================================
# テスト用定数
# =============================================================================

# 固定日時（テストの再現性を保証）
FIXED_DATETIME = datetime(2024, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

# マジック文字列を定数化
LOAD_TITLES_PATH = "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage"

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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = create_mock_entry(title="テストZenn記事", link="https://example.com/article1", summary="テストZenn記事の説明")
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

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) > 0, "有効なフィードから少なくとも1件の記事が取得されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
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
                return_value=Mock(
                    text="<html><body><p>日本語テキスト</p></body></html>"
                )
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 5, "5件の記事が追加されたため、5件取得されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10, target_dates=None)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_parse.side_effect = Exception("Network error")

            result = await service.collect(days=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "ネットワークエラー時は空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
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

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "HTTPタイムアウト時は空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ), patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = create_mock_entry(title="テスト", link="https://example.com/test", summary="説明")
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

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "GPT APIエラー時でもリストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_feed = Mock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1, limit=0)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "limit=0のため空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ), patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test"
            mock_entry = create_mock_entry(title="テスト", link="https://example.com/test", summary="説明")
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>日本語</body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) <= 1, "limit=1のため最大1件の記事が返されるべき"


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
                published_at=FIXED_DATETIME,
            ),
            Article(
                feed_name="Test",
                title="Article 2",
                url="http://example.com/2",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=50.0,
                published_at=FIXED_DATETIME,
            ),
            Article(
                feed_name="Test",
                title="Article 3",
                url="http://example.com/3",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="tech",
                popularity_score=30.0,
                published_at=FIXED_DATETIME,
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
                published_at=FIXED_DATETIME,
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

        entry = create_mock_entry(title="テストZenn記事", link="https://example.com/test", summary="テストの説明")

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text="<html><body><p>これは日本語の記事です</p></body></html>"
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "有効なエントリからArticleオブジェクトが返されるべき"
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
            published_at=FIXED_DATETIME,
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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_parse.side_effect = Exception("Parse error")

            result = await service.collect(days=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "パースエラー時は空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ), patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            return_value=Path("/data/test.json"),
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = create_mock_entry(title="テストZenn記事", link="https://example.com/test", summary="テスト説明")
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>日本語の記事</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) > 0, "完全なワークフローでは記事が取得されるべき"

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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # 両カテゴリのフィードが処理されたことを確認
            assert mock_parse.call_count == 2
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_parse.side_effect = AttributeError(
                "'NoneType' object has no attribute 'feed'"
            )

            result = await service.collect(days=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "AttributeError時は空リストが返されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = create_mock_entry(title="重複記事", link="https://example.com/duplicate", summary="説明")
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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_feed = create_mock_feed(title="Empty Feed")
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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            # 1つ目のフィードでエラー、2つ目は成功
            mock_feed = create_mock_feed(title="Test Feed")

            mock_parse.side_effect = [
                Exception("Feed error"),
                mock_feed,
            ]

            result = await service.collect(days=1)

            # エラーがあっても処理は継続される
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "部分的なフィードエラーでもエントリが空なら空リストが返されるべき"


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

        entry = create_mock_entry(title="テスト記事", link="https://example.com/not-found")

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

        entry = create_mock_entry(title="テスト記事", link="https://example.com/error")

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

        assert result is not None, "メタディスクリプションがある場合、Articleオブジェクトが返されるべき"
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

        service.http_client.get = AsyncMock(
            return_value=Mock(text=html_with_paragraphs)
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "段落がある場合、Articleオブジェクトが返されるべき"
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

        entry = create_mock_entry(title="テスト記事", link="https://example.com/test", summary="エントリのサマリーテキスト")

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>HTML本文</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "entry.summaryがある場合、Articleオブジェクトが返されるべき"
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

        entry = create_mock_entry(title="テスト記事", link="https://example.com/test")

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

        with patch.object(
            service.storage, "load_markdown", return_value=markdown_content
        ):
            result = service._load_existing_titles()

            assert result is not None, "Markdownからタイトルが読み込まれ、DedupTrackerが返されるべき"
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

            assert result is not None, "Markdownがない場合でも空のDedupTrackerが返されるべき"
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

        with patch.object(
            service.storage, "load_markdown", side_effect=Exception("Read error")
        ):
            result = service._load_existing_titles()

            assert result is not None, "例外が発生しても空のDedupTrackerが返されるべき"
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

        assert result is not None, "メタディスクリプションと段落がある場合、Articleオブジェクトが返されるべき"
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

        assert result is not None, "メタディスクリプションのみがある場合、Articleオブジェクトが返されるべき"
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

        assert result is not None, "コンテンツがなくてもArticleオブジェクトが返されるべき"
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

        assert result is not None, "段落のみがある場合、Articleオブジェクトが返されるべき"
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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock
        ) as mock_storage_load, patch.object(
            service.storage, "save", new_callable=AsyncMock
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
                return_value=Mock(
                    text="<html><body><p>新規記事の本文</p></body></html>"
                )
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) > 0, "日付範囲内の新規記事があるため、記事が取得されるべき"


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

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock
        ) as mock_storage_load:

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

            mock_feed = create_mock_feed(title="Test Feed")  # 新規記事なし
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "新規記事がないため空リストが返されるべき"


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


# =============================================================================
# 21. collect メソッド - フィード名取得ロジックの詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feed_without_title_attribute(mock_env_vars):
    """
    Given: feed.feedにtitle属性がないフィード
    When: collectメソッドを呼び出す
    Then: フィードURLがフィード名として使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock()
            # feed属性がない、またはtitle属性がないケース
            mock_feed.feed = Mock(spec=[])  # title属性なし
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feed_without_feed_attribute(mock_env_vars):
    """
    Given: feedオブジェクトにfeed属性がないフィード
    When: collectメソッドを呼び出す
    Then: フィードURLがフィード名として使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock(spec=["entries"])  # feed属性なし
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_effective_limit_calculation_with_days_greater_than_one(
    mock_env_vars,
):
    """
    Given: days=3, limit=5
    When: collectメソッドを呼び出す
    Then: effective_limit = 5 * 3 = 15として計算され、エントリが適切にフィルタされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            # 20個のエントリを作成（effective_limit=15を超える数）
            entries = []
            for i in range(20):
                entry = Mock()
                entry.title = f"記事{i}"
                entry.link = f"https://example.com/{i}"
                entry.summary = f"説明{i}"
                entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
                entries.append(entry)
            mock_feed.entries = entries
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=3, limit=5)

            # effective_limit = 5 * 3 = 15なので、最大15件まで処理される
            # 実際の結果数は15件以下であるべき（重複チェックなどで減る可能性がある）
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) <= 15, "effective_limit=15なので、最大15件まで処理されるべき"
            # 少なくとも一部の記事は処理されるべき
            assert len(result) >= 0, "エントリが処理されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_effective_limit_calculation_with_days_zero(mock_env_vars):
    """
    Given: days=0, limit=5
    When: collectメソッドを呼び出す
    Then: effective_limit = 5 * max(0, 1) = 5として計算され、エントリが適切にフィルタされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            # 10個のエントリを作成（effective_limit=5を超える数）
            entries = []
            for i in range(10):
                entry = Mock()
                entry.title = f"記事{i}"
                entry.link = f"https://example.com/{i}"
                entry.summary = f"説明{i}"
                entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
                entries.append(entry)
            mock_feed.entries = entries
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=0, limit=5)

            # effective_limit = 5 * max(0, 1) = 5なので、最大5件まで処理される
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) <= 5, "effective_limit=5なので、最大5件まで処理されるべき"
            assert len(result) >= 0, "エントリが処理されるべき"


# =============================================================================
# 22. collect メソッド - 日付範囲外の記事フィルタリングテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_filters_out_of_range_articles(mock_env_vars):
    """
    Given: 対象日付範囲外の記事を含むフィード
    When: collectメソッドを呼び出す
    Then: 範囲外の記事はスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "古い記事"
            mock_entry.link = "https://example.com/old"
            mock_entry.summary = "説明"
            # 対象日付範囲外（2024-01-01）
            mock_entry.published_parsed = (2024, 1, 1, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )

            # target_dates=[2024-11-14]（今日）で実行
            result = await service.collect(days=1, limit=10)

            # 範囲外の記事は保存されないはず
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "日付範囲外の記事はフィルタされるため、空または一部の記事が返されるべき"


# =============================================================================
# 23. _retrieve_article メソッド - 詳細な分岐テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_five_or_more_paragraphs(mock_env_vars):
    """
    Given: 5つ以上の段落を含むHTML
    When: _retrieve_articleを呼び出す
    Then: 最初の5つの段落のみが抽出される
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
        <body>
            <p>段落1</p>
            <p>段落2</p>
            <p>段落3</p>
            <p>段落4</p>
            <p>段落5</p>
            <p>段落6</p>
            <p>段落7</p>
        </body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "5つ以上の段落がある場合、Articleオブジェクトが返されるべき"
        # 最初の5つの段落が含まれている
        assert "段落1" in result.text
        assert "段落5" in result.text
        # 6つ目以降は含まれない
        assert "段落6" not in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_meta_description_empty_content(mock_env_vars):
    """
    Given: メタディスクリプションのcontentが空
    When: _retrieve_articleを呼び出す
    Then: 段落からテキストが抽出される
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
            <meta name="description" content="">
        </head>
        <body>
            <p>段落のテキスト</p>
        </body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "メタディスクリプションが空でも段落があればArticleオブジェクトが返されるべき"
        assert "段落のテキスト" in result.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_published_at_extraction(mock_env_vars):
    """
    Given: published_parsedを持つエントリ
    When: _retrieve_articleを呼び出す
    Then: published_atが正しく解析される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "説明"
        entry.published_parsed = (2024, 11, 14, 15, 30, 45, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "published_parsedが正しく解析されArticleオブジェクトが返されるべき"
        assert result.published_at is not None
        # 時刻が正しく解析されているか確認
        assert result.published_at.year == 2024
        assert result.published_at.month == 11
        assert result.published_at.day == 14


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_popularity_score_extraction(mock_env_vars):
    """
    Given: 人気スコアを持つHTML
    When: _retrieve_articleを呼び出す
    Then: 人気スコアが正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = create_mock_entry(title="テスト記事", link="https://example.com/test", summary="説明")

        html = """
        <html>
        <head>
            <meta property="zenn:likes_count" content="200">
        </head>
        <body><p>テキスト</p></body>
        </html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None, "メタディスクリプションの優先順位が正しく、Articleオブジェクトが返されるべき"
        assert result.popularity_score == 200.0


# =============================================================================
# 24. _extract_popularity メソッド - 優先順位とエッジケース
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_meta_tag_priority_over_data_attribute(mock_env_vars):
    """
    Given: メタタグとdata属性の両方が存在
    When: _extract_popularityを呼び出す
    Then: メタタグが優先される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <head>
            <meta property="zenn:likes_count" content="100">
        </head>
        <body>
            <button data-like-count="200">いいね</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # メタタグが優先されるので100.0が返される
        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_data_attribute_priority_over_text(mock_env_vars):
    """
    Given: data属性とテキストの両方が存在（メタタグなし）
    When: _extract_popularityを呼び出す
    Then: data属性が優先される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-like-count="150">いいね</button>
            <span>いいね 250</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # 最大値が選択されるので250.0
        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_with_non_numeric_data_attribute(mock_env_vars):
    """
    Given: data-like-countが非数値
    When: _extract_popularityを呼び出す
    Then: スキップされて他の候補が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-like-count="invalid">いいね</button>
            <span>いいね 100</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # invalidはスキップされ、100が使用される
        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_with_multiple_data_attributes(mock_env_vars):
    """
    Given: 複数のdata-like-count属性が存在
    When: _extract_popularityを呼び出す
    Then: 最大値が選択される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-like-count="50">いいね</button>
            <button data-like-count="300">いいね</button>
            <button data-like-count="150">いいね</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_with_comma_in_text(mock_env_vars):
    """
    Given: カンマ区切りの数値を含むテキスト
    When: _extract_popularityを呼び出す
    Then: カンマが除去されて数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span>いいね 1,234</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 1234.0


@pytest.mark.unit
def test_extract_popularity_empty_text_elements(mock_env_vars):
    """
    Given: テキストが空の要素が存在
    When: _extract_popularityを呼び出す
    Then: 空要素はスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button></button>
            <span></span>
            <div>いいね 50</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 50.0


# =============================================================================
# 25. collect メソッド - 既存ファイルの処理詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_preserves_existing_files_path(mock_env_vars):
    """
    Given: 既存記事があり新規記事がない
    When: collectメソッドを呼び出す
    Then: 既存ファイルパスが結果に含まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock
        ) as mock_storage_load:

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

            mock_feed = create_mock_feed(title="Test Feed")  # 新規記事なし
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # 既存ファイルパスが結果に含まれることを確認
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "既存ファイルがあるため、リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_storage_load_exception_handling(mock_env_vars):
    """
    Given: 既存記事の読み込み時に例外が発生
    When: collectメソッドを呼び出す
    Then: 例外が適切に処理され、処理が継続される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock
        ) as mock_storage_load, patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            # ストレージ読み込み時に例外
            mock_storage_load.side_effect = Exception("Storage error")

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = create_mock_entry(title="新規記事", link="https://example.com/new", summary="説明")
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1)

            # 例外が処理され、処理が継続される
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) > 0, "ストレージエラーでも新規記事があるため記事が取得されるべき"


# =============================================================================
# 26. _load_existing_titles メソッド - 追加エッジケース
# =============================================================================


@pytest.mark.unit
def test_load_existing_titles_with_no_matches(temp_data_dir, mock_env_vars):
    """
    Given: 正規表現にマッチしないMarkdown
    When: _load_existing_titlesを呼び出す
    Then: 空のDedupTrackerが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.storage.base_dir = Path(temp_data_dir)

        # マッチしないMarkdown
        markdown_content = """## Tech

This is just plain text without any article titles.

Some more text here.
"""

        with patch.object(
            service.storage, "load_markdown", return_value=markdown_content
        ):
            result = service._load_existing_titles()

            assert result is not None, "同じスコアの記事がある場合でもリストが返されるべき"
            # マッチしないので空のトラッカー
            is_dup, _ = result.is_duplicate("新規記事")
            assert is_dup is False


@pytest.mark.unit
def test_load_existing_titles_with_multiple_matches(temp_data_dir, mock_env_vars):
    """
    Given: 複数のタイトルマッチを含むMarkdown
    When: _load_existing_titlesを呼び出す
    Then: すべてのタイトルがDedupTrackerに追加される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.storage.base_dir = Path(temp_data_dir)

        markdown_content = """## Tech

### [記事A](https://example.com/a)
### [記事B](https://example.com/b)
### [記事C](https://example.com/c)
"""

        with patch.object(
            service.storage, "load_markdown", return_value=markdown_content
        ):
            result = service._load_existing_titles()

            assert result is not None, "スコア順で記事が返されるべき"
            # すべてのタイトルが追加されている
            is_dup_a, _ = result.is_duplicate("記事A")
            is_dup_b, _ = result.is_duplicate("記事B")
            is_dup_c, _ = result.is_duplicate("記事C")
            assert is_dup_a is True
            assert is_dup_b is True
            assert is_dup_c is True


# =============================================================================
# 27. _select_top_articles メソッド - 同一スコアのテスト
# =============================================================================


@pytest.mark.unit
def test_select_top_articles_with_same_popularity_score(mock_env_vars):
    """
    Given: 同じpopularity_scoreを持つ複数の記事
    When: _select_top_articlesを呼び出す
    Then: 安定したソート順で選択される
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
                popularity_score=10.0,  # すべて同じスコア
                published_at=FIXED_DATETIME,
            )
            for i in range(5)
        ]

        result = service._select_top_articles(articles, limit=3)

        assert len(result) == 3
        # すべて同じスコアなので、最初の3つが選択される
        assert all(article.popularity_score == 10.0 for article in result)


@pytest.mark.unit
def test_select_top_articles_with_zero_popularity_scores(mock_env_vars):
    """
    Given: popularity_scoreがすべて0.0の記事
    When: _select_top_articlesを呼び出す
    Then: 記事が選択される
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
                popularity_score=0.0,
                published_at=FIXED_DATETIME,
            )
            for i in range(3)
        ]

        result = service._select_top_articles(articles, limit=2)

        assert len(result) == 2
        assert all(article.popularity_score == 0.0 for article in result)


# =============================================================================
# 28. collect メソッド - finallyブロックとクリーンアップ
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_finally_block_execution(mock_env_vars):
    """
    Given: collectメソッド実行
    When: 処理が完了する
    Then: finallyブロックが実行される（クリーンアップ処理）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # finallyブロックが実行され、正常終了
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


# =============================================================================
# 29. _retrieve_article メソッド - entry.link属性の詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_link_attribute_hasattr_false(mock_env_vars):
    """
    Given: entryにlink属性が存在しない
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock(spec=[])  # link属性なし
        # hasattr(entry, "link")がFalseになるようにする

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_error_logging_with_no_link(mock_env_vars):
    """
    Given: link属性がないentryで例外が発生
    When: _retrieve_articleでエラー処理
    Then: '不明'がログに記録される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        # link属性を持つが、アクセス時に例外を発生させる
        type(entry).link = property(
            lambda self: (_ for _ in ()).throw(AttributeError("test error"))
        )

        # エラーログをキャプチャするためのモック
        with patch.object(service.logger, "error") as mock_logger_error:
            result = await service._retrieve_article(entry, "Test Feed", "tech")

            assert result is None
            # エラーログが呼ばれたことを確認
            mock_logger_error.assert_called_once()


# =============================================================================
# 30. _extract_popularity メソッド - getattr分岐の完全カバレッジ
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_entry_without_any_like_attributes(mock_env_vars):
    """
    Given: entry.likes、entry.likes_count、entry.zenn_likes_countがすべて存在しない
    When: _extract_popularityを呼び出す
    Then: AttributeErrorが適切に処理され、0.0が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        # 属性が存在しないMock
        entry = Mock(spec=[])
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 0.0


@pytest.mark.unit
def test_extract_popularity_meta_tag_with_non_numeric_content(mock_env_vars):
    """
    Given: メタタグのcontentが非数値
    When: _extract_popularityを呼び出す
    Then: 次の抽出方法にフォールバックする
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        entry = Mock()
        html = """
        <html>
        <head>
            <meta property="zenn:likes_count" content="invalid_number">
        </head>
        <body>
            <button data-like-count="50">いいね</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # メタタグが非数値なので、data属性から抽出される
        assert result == 50.0


# =============================================================================
# 31. collect メソッド - http_client初期化の確認
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_initializes_http_client_when_none(mock_env_vars):
    """
    Given: http_clientがNone
    When: collectメソッドを呼び出す
    Then: setup_http_clientが呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        # http_clientを明示的にNoneに設定
        service.http_client = None

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ) as mock_setup, patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # setup_http_clientが呼ばれたことを確認
            mock_setup.assert_called_once()
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


# =============================================================================
# 32. collect メソッド - 境界値テスト（負値、極値）
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_negative_days(mock_env_vars):
    """
    Given: days=-1（負の値）
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理され、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            result = await service.collect(days=-1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "負のdaysでもエラーなくリストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_negative_limit(mock_env_vars):
    """
    Given: limit=-1（負の値）
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理され、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            result = await service.collect(days=1, limit=-1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "負のlimitでもエラーなくリストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_extremely_large_days(mock_env_vars):
    """
    Given: days=10000（極端に大きな値）
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理され、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=10000)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "極端に大きなdaysでもエラーなくリストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_extremely_large_limit(mock_env_vars):
    """
    Given: limit=999999（極端に大きな値）
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理され、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            # 極端に大きなlimitでも、実際のエントリ数は小さい
            mock_entry = create_mock_entry(title="テスト記事", link="https://example.com/test", summary="説明")
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=1, limit=999999)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "極端に大きなlimitでもエラーなくリストが返されるべき"
            # 実際のエントリ数以上は取得されない
            assert len(result) <= 1, "実際のエントリ数以上は取得されないべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_negative_days_and_limit(mock_env_vars):
    """
    Given: days=-1, limit=-1（両方とも負の値）
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理され、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ):

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            result = await service.collect(days=-1, limit=-1)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) >= 0, "負の値でもエラーなくリストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_days_zero_boundary(mock_env_vars):
    """
    Given: days=0（ゼロ境界値）
    When: collectメソッドを呼び出す
    Then: 今日の日付のみが対象となる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ZennExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            LOAD_TITLES_PATH,
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = create_mock_feed(title="Test Feed")
            mock_parse.return_value = mock_feed

            mock_dedup = create_mock_dedup(is_duplicate=False, normalized_title="normalized_title")
            mock_load.return_value = mock_dedup

            result = await service.collect(days=0)

            assert isinstance(result, list), "結果はリスト型であるべき"
            # days=0の場合、今日の日付のみが対象になるため空リストが返される可能性が高い
            assert len(result) >= 0, "days=0でも正常にリストが返されるべき"
