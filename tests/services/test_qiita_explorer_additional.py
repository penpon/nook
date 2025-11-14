"""
nook/services/qiita_explorer/qiita_explorer.py の追加単体テスト

テスト観点:
- collect()の内部分岐詳細テスト
- _retrieve_article()のHTTPエラー・BeautifulSoup解析詳細
- _extract_popularity()のQiita特有のメタタグ/data属性/テキスト抽出詳細
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article
from nook.services.qiita_explorer.qiita_explorer import QiitaExplorer


# =============================================================================
# 1. collect内部分岐 詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_multiple_categories_processing(mock_env_vars):
    """
    Given: 複数カテゴリのフィード設定
    When: collectメソッドを呼び出す
    Then: 各カテゴリのフィードが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        # feed_configを複数カテゴリに設定
        service.feed_config = {
            "tech": ["https://example.com/tech.xml"],
            "programming": ["https://example.com/programming.xml"],
        }

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage, "save", new_callable=AsyncMock
        ):

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_load.return_value = mock_dedup

            result = await service.collect(days=1, limit=10)

            # 2つのカテゴリ × 1フィード = 2回呼び出される
            assert mock_parse.call_count == 2
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_date_filtering_outside_range(mock_env_vars):
    """
    Given: 対象日付範囲外のエントリ
    When: collectメソッドを呼び出す
    Then: 範囲外の記事は除外される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            # 古い日付のエントリ（2020年）
            mock_entry = Mock()
            mock_entry.title = "古い記事"
            mock_entry.link = "https://example.com/old"
            mock_entry.summary = "古い記事の説明"
            mock_entry.published_parsed = (2020, 1, 1, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (False, "normalized")
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )

            result = await service.collect(days=1, limit=10)

            # 日付範囲外なので保存されない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_duplicate_check_excludes_duplicates(mock_env_vars):
    """
    Given: 重複タイトルのエントリ
    When: collectメソッドを呼び出す
    Then: 重複記事がスキップされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load:

            mock_feed = Mock()
            mock_feed.feed.title = "Test Feed"
            mock_entry = Mock()
            mock_entry.title = "重複記事"
            mock_entry.link = "https://example.com/dup"
            mock_entry.summary = "重複記事の説明"
            mock_entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)
            mock_feed.entries = [mock_entry]
            mock_parse.return_value = mock_feed

            # 重複として検出されるようにモック設定
            mock_dedup = Mock()
            mock_dedup.is_duplicate.return_value = (True, "normalized_title")
            mock_dedup.get_original_title.return_value = "重複記事"
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )

            result = await service.collect(days=1, limit=10)

            # 重複なので保存されない
            assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_storage_save_failure(mock_env_vars):
    """
    Given: ストレージ保存が失敗
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ) as mock_load, patch.object(
            service.storage, "load", new_callable=AsyncMock, return_value=None
        ), patch.object(
            service.storage,
            "save",
            new_callable=AsyncMock,
            side_effect=Exception("Storage error"),
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
            mock_load.return_value = mock_dedup

            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
            )
            service.gpt_client.get_response = AsyncMock(return_value="要約")

            # 例外が発生するが、collectは完了する
            result = await service.collect(days=1, limit=10)

            # エラーが発生してもリストが返される
            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feed_parse_exception_continues(mock_env_vars):
    """
    Given: フィード解析時に例外発生
    When: collectメソッドを呼び出す
    Then: 例外がログされ、処理が続行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        # 複数フィード設定（1つ目は失敗、2つ目は成功）
        service.feed_config = {
            "tech": [
                "https://example.com/bad-feed.xml",
                "https://example.com/good-feed.xml",
            ]
        }

        with patch("feedparser.parse") as mock_parse, patch.object(
            service, "setup_http_client", new_callable=AsyncMock
        ), patch.object(
            service, "_get_all_existing_dates", new_callable=AsyncMock, return_value=[]
        ), patch(
            "nook.services.qiita_explorer.qiita_explorer.load_existing_titles_from_storage",
            new_callable=AsyncMock,
        ):

            # 1回目は例外、2回目は成功
            mock_feed = Mock()
            mock_feed.feed.title = "Good Feed"
            mock_feed.entries = []
            mock_parse.side_effect = [Exception("Parse error"), mock_feed]

            result = await service.collect(days=1)

            # エラーがあっても処理は継続
            assert isinstance(result, list)
            # 2回呼び出される（1回目失敗、2回目成功）
            assert mock_parse.call_count == 2


# =============================================================================
# 2. _retrieve_article 詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_timeout(mock_env_vars):
    """
    Given: HTTP GET時にタイムアウト発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

        service.http_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_http_404_error(mock_env_vars):
    """
    Given: HTTP GET時に404エラー発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

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
    Given: HTTP GET時に500エラー発生
    When: _retrieve_articleを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"

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
async def test_retrieve_article_empty_html(mock_env_vars):
    """
    Given: 空のHTMLが返される
    When: _retrieve_articleを呼び出す
    Then: Articleオブジェクトが返される（空のテキスト）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"
        entry.summary = ""
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        service.http_client.get = AsyncMock(return_value=Mock(text=""))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        assert result.text == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_malformed_html(mock_env_vars):
    """
    Given: 不正なHTMLが返される
    When: _retrieve_articleを呼び出す
    Then: Articleオブジェクトが返される（BeautifulSoupは寛容に解析）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"
        entry.summary = "説明"
        entry.published_parsed = (2024, 11, 14, 0, 0, 0, 0, 0, 0)

        # 不正なHTML（閉じタグなし）
        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>テキスト")
        )

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        assert isinstance(result, Article)
        # BeautifulSoupは不正なHTMLでも解析できる
        assert result.text == "説明"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_article_with_meta_description(mock_env_vars):
    """
    Given: メタディスクリプションを含むHTML
    When: _retrieve_articleを呼び出す（entry.summaryなし）
    Then: メタディスクリプションが抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"
        # summaryなし
        delattr(entry, "summary")
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
async def test_retrieve_article_with_paragraphs(mock_env_vars):
    """
    Given: 段落を含むHTML（meta descriptionなし）
    When: _retrieve_articleを呼び出す（entry.summaryなし）
    Then: 最初の5段落が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()
        service.http_client = AsyncMock()

        entry = Mock()
        entry.title = "テスト"
        entry.link = "https://example.com/test"
        # summaryなし
        delattr(entry, "summary")
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
        </body>
        </html>
        """
        service.http_client.get = AsyncMock(return_value=Mock(text=html))

        result = await service._retrieve_article(entry, "Test Feed", "tech")

        assert result is not None
        # 最初の5段落
        assert "段落1" in result.text
        assert "段落5" in result.text
        assert "段落6" not in result.text


# =============================================================================
# 3. _extract_popularity 詳細テスト（Qiita特有）
# =============================================================================


@pytest.mark.unit
def test_extract_popularity_with_qiita_likes_count_attribute(mock_env_vars):
    """
    Given: entryにqiita_likes_count属性がある
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.qiita_likes_count = 42
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 42.0


@pytest.mark.unit
def test_extract_popularity_with_likes_count_attribute(mock_env_vars):
    """
    Given: entryにlikes_count属性がある
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.likes_count = 100
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 100.0


@pytest.mark.unit
def test_extract_popularity_with_lgtm_attribute(mock_env_vars):
    """
    Given: entryにlgtm属性がある
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.lgtm = 75
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 75.0


@pytest.mark.unit
def test_extract_popularity_with_lgtm_count_attribute(mock_env_vars):
    """
    Given: entryにlgtm_count属性がある
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        entry.lgtm_count = 88
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 88.0


@pytest.mark.unit
def test_extract_popularity_with_meta_twitter_data1(mock_env_vars):
    """
    Given: metaタグ（twitter:data1）に「150 likes」形式
    When: _extract_popularityを呼び出す
    Then: 数値部分が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <head>
            <meta name="twitter:data1" content="150 likes">
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_with_data_lgtm_count(mock_env_vars):
    """
    Given: data-lgtm-count属性を持つ要素
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-lgtm-count="200">LGTM</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 200.0


@pytest.mark.unit
def test_extract_popularity_with_data_likes_count(mock_env_vars):
    """
    Given: data-likes-count属性を持つ要素
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span data-likes-count="300">いいね</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 300.0


@pytest.mark.unit
def test_extract_popularity_with_data_qiita_lgtm_count(mock_env_vars):
    """
    Given: data-qiita-lgtm-count属性を持つ要素
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <div data-qiita-lgtm-count="250">LGTM</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 250.0


@pytest.mark.unit
def test_extract_popularity_with_js_lgtm_count_class(mock_env_vars):
    """
    Given: .js-lgtm-countクラスを持つ要素（LGTMキーワード含む）
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span class="js-lgtm-count">LGTM 125</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 125.0


@pytest.mark.unit
def test_extract_popularity_with_it_actions_itemcount_class(mock_env_vars):
    """
    Given: .it-Actions_itemCountクラスを持つ要素（いいねキーワード含む）
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span class="it-Actions_itemCount">いいね 99</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 99.0


@pytest.mark.unit
def test_extract_popularity_with_button_likes_text(mock_env_vars):
    """
    Given: ボタンに「いいね」を含むテキスト
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button>いいね 180</button>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 180.0


@pytest.mark.unit
def test_extract_popularity_with_span_lgtm_text(mock_env_vars):
    """
    Given: spanに「LGTM」を含むテキスト
    When: _extract_popularityを呼び出す
    Then: テキストから数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <span>LGTM 220</span>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 220.0


@pytest.mark.unit
def test_extract_popularity_with_multiple_candidates_returns_max(mock_env_vars):
    """
    Given: 複数の候補値が存在
    When: _extract_popularityを呼び出す
    Then: 最大値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = Mock()
        html = """
        <html>
        <body>
            <button data-lgtm-count="50">LGTM</button>
            <span data-likes-count="150">いいね</span>
            <div class="js-lgtm-count">75</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = service._extract_popularity(entry, soup)

        # 最大値150が返される
        assert result == 150.0


@pytest.mark.unit
def test_extract_popularity_with_comma_separated_number(mock_env_vars):
    """
    Given: カンマ区切りの数値（「1,234 いいね」）
    When: _extract_popularityを呼び出す
    Then: カンマを除去して数値が抽出される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

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
def test_extract_popularity_entry_as_dict_with_qiita_likes(mock_env_vars):
    """
    Given: entryが辞書型でqiita_likes_countキーを持つ
    When: _extract_popularityを呼び出す
    Then: その値が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = QiitaExplorer()

        entry = {"qiita_likes_count": 150}
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

        result = service._extract_popularity(entry, soup)

        assert result == 150.0
