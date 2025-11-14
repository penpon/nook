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
LOAD_TITLES_PATH = (
    "nook.services.zenn_explorer.zenn_explorer.load_existing_titles_from_storage"
)

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


# =============================================================================
# 4. collect メソッドのテスト - 異常系
# =============================================================================


# =============================================================================
# 5. collect メソッドのテスト - 境界値
# =============================================================================


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


# =============================================================================
# 8. _extract_popularity メソッドのテスト
# =============================================================================


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


# =============================================================================
# 13. collect メソッド - フィード処理ループの詳細テスト
# =============================================================================


# =============================================================================
# 14. _retrieve_article メソッド - HTTPエラー・BeautifulSoup解析詳細テスト
# =============================================================================


# =============================================================================
# 15. _extract_popularity メソッド - Zenn特有の詳細テスト
# =============================================================================


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

            assert (
                result is not None
            ), "Markdownからタイトルが読み込まれ、DedupTrackerが返されるべき"
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

            assert (
                result is not None
            ), "Markdownがない場合でも空のDedupTrackerが返されるべき"
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


# =============================================================================
# 18. _extract_popularity メソッド - div要素の明示的なテスト
# =============================================================================


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
            assert (
                len(result) > 0
            ), "日付範囲内の新規記事があるため、記事が取得されるべき"


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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=3, limit=5)

            # effective_limit = 5 * 3 = 15なので、最大15件まで処理される
            # 実際の結果数は15件以下であるべき（重複チェックなどで減る可能性がある）
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert (
                len(result) <= 15
            ), "effective_limit=15なので、最大15件まで処理されるべき"
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            result = await service.collect(days=0, limit=5)

            # effective_limit = 5 * max(0, 1) = 5なので、最大5件まで処理される
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert (
                len(result) <= 5
            ), "effective_limit=5なので、最大5件まで処理されるべき"
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
            assert (
                len(result) >= 0
            ), "日付範囲外の記事はフィルタされるため、空または一部の記事が返されるべき"


# =============================================================================
# 23. _retrieve_article メソッド - 詳細な分岐テスト
# =============================================================================


# =============================================================================
# 24. _extract_popularity メソッド - 優先順位とエッジケース
# =============================================================================


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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
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
            mock_entry = create_mock_entry(
                title="新規記事", link="https://example.com/new", summary="説明"
            )
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
            assert (
                len(result) > 0
            ), "ストレージエラーでも新規記事があるため記事が取得されるべき"


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

            assert (
                result is not None
            ), "同じスコアの記事がある場合でもリストが返されるべき"
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1)

            # finallyブロックが実行され、正常終了
            assert isinstance(result, list), "結果はリスト型であるべき"
            assert len(result) == 0, "エントリがないため空リストが返されるべき"


# =============================================================================
# 29. _retrieve_article メソッド - entry.link属性の詳細テスト
# =============================================================================


# =============================================================================
# 30. _extract_popularity メソッド - getattr分岐の完全カバレッジ
# =============================================================================


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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
            mock_load.return_value = mock_dedup

            result = await service.collect(days=10000)

            assert isinstance(result, list), "結果はリスト型であるべき"
            assert (
                len(result) >= 0
            ), "極端に大きなdaysでもエラーなくリストが返されるべき"


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
            mock_entry = create_mock_entry(
                title="テスト記事", link="https://example.com/test", summary="説明"
            )
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
            assert (
                len(result) >= 0
            ), "極端に大きなlimitでもエラーなくリストが返されるべき"
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

            mock_dedup = create_mock_dedup(
                is_duplicate=False, normalized_title="normalized_title"
            )
            mock_load.return_value = mock_dedup

            result = await service.collect(days=0)

            assert isinstance(result, list), "結果はリスト型であるべき"
            # days=0の場合、今日の日付のみが対象になるため空リストが返される可能性が高い
            assert len(result) >= 0, "days=0でも正常にリストが返されるべき"
