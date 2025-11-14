"""
ZennExplorer._extract_popularity() メソッドのテスト

テスト観点:
- Zenn特有のメタタグからの抽出
- data-like-count属性からの抽出
- ボタン/スパンのテキストからの抽出
- div要素のテキストからの抽出
- フィードエントリの属性からの抽出
- 複数候補から最大値を選択
- 非数値・空値のハンドリング
- 優先順位の確認
- エッジケース

"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.zenn_explorer.zenn_explorer import ZennExplorer


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
