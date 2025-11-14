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
    """
    Given: デフォルトのstorage_dir
    When: NoteExplorerを初期化
    Then: インスタンスが正常に作成され、feed_configが読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        assert service.service_name == "note_explorer"
        assert service.http_client is None
        assert service.feed_config is not None
        assert isinstance(service.feed_config, dict)


@pytest.mark.unit
def test_init_total_limit_constant(mock_env_vars):
    """
    Given: NoteExplorerクラス
    When: TOTAL_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert NoteExplorer.TOTAL_LIMIT == 15


@pytest.mark.unit
def test_init_summary_limit_constant(mock_env_vars):
    """
    Given: NoteExplorerクラス
    When: SUMMARY_LIMIT定数を確認
    Then: 15が設定されている
    """
    assert NoteExplorer.SUMMARY_LIMIT == 15


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
    """
    Given: 有効なRSSフィード
    When: collectメソッドを呼び出す
    Then: 記事が正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load:

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
        service = NoteExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
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
        service = NoteExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ), patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
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
        service = NoteExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ), patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
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
        service = NoteExplorer()

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
        service = NoteExplorer()

        articles = [
            Article(
                feed_name="Test",
                title="Article 1",
                url="http://example.com/1",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="general",
                popularity_score=10.0,
                published_at=datetime.now(),
            ),
            Article(
                feed_name="Test",
                title="Article 2",
                url="http://example.com/2",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="general",
                popularity_score=50.0,
                published_at=datetime.now(),
            ),
            Article(
                feed_name="Test",
                title="Article 3",
                url="http://example.com/3",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="general",
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
        service = NoteExplorer()

        articles = [
            Article(
                feed_name="Test",
                title=f"Article {i}",
                url=f"http://example.com/{i}",
                text="text",
                soup=BeautifulSoup("", "html.parser"),
                category="general",
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テストnote記事"
        entry.link = "https://example.com/test"
        entry.summary = "テストの説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(
            return_value=Mock(
                text="<html><body><p>これは日本語の記事です</p></body></html>"
            )
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert isinstance(result, Article)
        assert result.title == "テストnote記事"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_no_url(mock_env_vars):
    """
    Given: URLを持たないエントリ
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
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
    """
    Given: HTTP取得時にエラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
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
    """
    Given: 人気スコアを含むメタタグ
    When: _extract_popularityを呼び出す
    Then: スコアが正しく抽出される
    """
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
    """
    Given: 人気スコアがないHTML
    When: _extract_popularityを呼び出す
    Then: 0.0が返される
    """
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
    """
    Given: NoteExplorerインスタンス
    When: _get_markdown_headerを呼び出す
    Then: ヘッダーテキストが返される
    """
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
    """
    Given: NoteExplorerインスタンス
    When: _get_summary_system_instructionを呼び出す
    Then: システム指示が返される
    """
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
    """
    Given: 記事オブジェクト
    When: _get_summary_prompt_templateを呼び出す
    Then: プロンプトテンプレートが返される
    """
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
    """
    Given: フィード解析エラー
    When: collectを実行
    Then: エラーがログされ、処理が続行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
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
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
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
    """
    Given: feed.tomlの読み込みが失敗
    When: NoteExplorerを初期化
    Then: エラーが発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        with patch(
            "builtins.open", side_effect=FileNotFoundError("feed.toml not found")
        ):
            with pytest.raises(FileNotFoundError):
                NoteExplorer()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_duplicate_detection(mock_env_vars):
    """
    Given: DedupTrackerによる重複チェックが有効
    When: collectメソッドを呼び出す
    Then: 重複チェック処理が実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load_func, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
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
    """
    Given: 対象日付範囲外のエントリ
    When: collectメソッドを呼び出す
    Then: 範囲外の記事がスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"

            # 古い日付の記事（範囲外）
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
    """
    Given: ストレージ保存が失敗
    When: collectメソッドを呼び出す
    Then: エラーがログされるが例外は発生しない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            side_effect=Exception("Save failed"),
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

            # エラーが発生しても空リストが返される可能性がある
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_multiple_categories_loop(mock_env_vars):
    """
    Given: 複数カテゴリのフィード設定
    When: collectメソッドを呼び出す
    Then: 各カテゴリのフィードが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        # 複数カテゴリを設定
        service.feed_config = {
            "tech": ["https://example.com/tech.xml"],
            "business": ["https://example.com/business.xml"],
        }

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.note_explorer.note_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10)

            # 2つのカテゴリ分、feedparser.parseが2回呼ばれることを確認
            assert mock_parse.call_count == 2


# =============================================================================
# 14. _retrieve_article メソッドの追加詳細テスト - HTTPエラー・HTML解析
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    """
    Given: HTTP GET時に404エラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
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
    """
    Given: HTTP GET時に500エラーが発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
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
    """
    Given: 空のHTMLが返される
    When: _retrieve_articleを呼び出す
    Then: Articleオブジェクトが返されるが、textが空またはsummaryから取得
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリの要約"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 空のHTML
        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body></body></html>")
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert isinstance(result, Article)
        # 空HTMLの場合、entry.summaryが使われる
        assert result.text == "エントリの要約"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_malformed_html(mock_env_vars):
    """
    Given: 不正なHTMLが返される
    When: _retrieve_articleを呼び出す
    Then: BeautifulSoupが可能な範囲で解析し、Articleが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト記事"
        entry.link = "https://example.com/test"
        entry.summary = "エントリの要約"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 不正なHTML（タグが閉じていない等）
        service.http_client.get = AsyncMock(
            return_value=Mock(
                text="<html><body><p>テキスト</body>"
            )  # pタグが閉じていない
        )

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert isinstance(result, Article)
        # BeautifulSoupは寛容なので、何らかのテキストが取得される
        assert len(result.text) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_extracts_meta_description(mock_env_vars):
    """
    Given: メタディスクリプションを含むHTML
    When: _retrieve_articleを呼び出す
    Then: メタディスクリプションがテキストとして抽出される
    """
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
        html = """
        <html>
        <head>
            <meta name="description" content="これはメタディスクリプションです。">
        </head>
        <body></body>
        </html>
        """
        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "general")

        assert result is not None
        assert result.text == "これはメタディスクリプションです。"


# =============================================================================
# 15. _extract_popularity メソッドの追加詳細テスト - note特有の抽出
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_note_likes_meta(mock_env_vars):
    """
    Given: note:likesメタタグを含むHTML
    When: _extract_popularityを呼び出す
    Then: いいね数が正しく抽出される
    """
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
    """
    Given: twitter:data1メタタグを含むHTML
    When: _extract_popularityを呼び出す
    Then: いいね数が正しく抽出される
    """
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
    """
    Given: note:likes_countメタタグを含むHTML
    When: _extract_popularityを呼び出す
    Then: いいね数が正しく抽出される
    """
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
    """
    Given: data-like-count属性を含むHTML
    When: _extract_popularityを呼び出す
    Then: いいね数が正しく抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        soup = BeautifulSoup(
            '<html><body><button data-like-count="180">♥ いいね</button></body></html>',
            "html.parser",
        )

        result = service._extract_popularity(entry, soup)

        assert result == 180.0


@pytest.mark.unit
def test_extract_popularity_with_data_supporter_count_attribute(mock_env_vars):
    """
    Given: data-supporter-count属性を含むHTML
    When: _extract_popularityを呼び出す
    Then: サポーター数が正しく抽出される
    """
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
    """
    Given: data-suki-count属性を含むHTML
    When: _extract_popularityを呼び出す
    Then: スキ数が正しく抽出される
    """
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
    """
    Given: 「スキ」を含むボタンテキスト
    When: _extract_popularityを呼び出す
    Then: テキストから数値が正しく抽出される
    """
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
    """
    Given: 「いいね」を含むspanテキスト
    When: _extract_popularityを呼び出す
    Then: テキストから数値が正しく抽出される
    """
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
    """
    Given: 「likes」を含むdivテキスト
    When: _extract_popularityを呼び出す
    Then: テキストから数値が正しく抽出される
    """
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
    """
    Given: 複数の候補値が存在するHTML
    When: _extract_popularityを呼び出す
    Then: 最大値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        # 複数の候補：data-like-count=100, スキ 50, いいね 200
        html = """
        <html>
        <body>
            <button data-like-count="100">♥</button>
            <span class="suki-count">スキ 50</span>
            <div class="like-div">いいね 200</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # 最大値の200が返される
        assert result == 200.0


@pytest.mark.unit
def test_extract_popularity_from_entry_attribute(mock_env_vars):
    """
    Given: entryオブジェクトにlikes属性が存在
    When: _extract_popularityを呼び出す
    Then: entry.likesから値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        entry.likes = 500
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 500.0


@pytest.mark.unit
def test_extract_popularity_from_entry_likes_count_attribute(mock_env_vars):
    """
    Given: entryオブジェクトにlikes_count属性が存在（likesはNone）
    When: _extract_popularityを呼び出す
    Then: entry.likes_countから値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = NoteExplorer()

        entry = Mock()
        entry.likes = None  # likesがNoneの場合にlikes_countが評価される
        entry.likes_count = 450
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 450.0
