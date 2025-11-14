"""
ZennExplorer._retrieve_article() メソッドのテスト

テスト観点:
- HTTPリクエスト成功/失敗
- BeautifulSoupによるHTML解析
- メタデータ抽出（description, published_at）
- 人気スコア抽出
- エラーハンドリング
- 各種フォールバックロジック

"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.base_feed_service import Article
from nook.services.zenn_explorer.zenn_explorer import ZennExplorer
from tests.conftest import create_mock_entry


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

        entry = create_mock_entry(
            title="テストZenn記事",
            link="https://example.com/test",
            summary="テストの説明",
        )

        service.http_client.get = AsyncMock(
            return_value=Mock(text="<html><body><p>これは日本語の記事です</p></body></html>")
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

        assert (
            result is not None
        ), "メタディスクリプションがある場合、Articleオブジェクトが返されるべき"
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

        entry = create_mock_entry(
            title="テスト記事",
            link="https://example.com/test",
            summary="エントリのサマリーテキスト",
        )

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

        assert (
            result is not None
        ), "メタディスクリプションと段落がある場合、Articleオブジェクトが返されるべき"
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

        assert (
            result is not None
        ), "メタディスクリプションのみがある場合、Articleオブジェクトが返されるべき"
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

        assert (
            result is not None
        ), "メタディスクリプションが空でも段落があればArticleオブジェクトが返されるべき"
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

        assert (
            result is not None
        ), "published_parsedが正しく解析されArticleオブジェクトが返されるべき"
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

        entry = create_mock_entry(
            title="テスト記事", link="https://example.com/test", summary="説明"
        )

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

        assert (
            result is not None
        ), "メタディスクリプションの優先順位が正しく、Articleオブジェクトが返されるべき"
        assert result.popularity_score == 200.0


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
