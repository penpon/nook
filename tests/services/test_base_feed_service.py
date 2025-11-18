"""
nook/services/base_feed_service.py のテスト

テスト観点:
- BaseFeedServiceの各内部メソッドの単体テスト
- 正常系、境界値、異常系、エッジケースを網羅
- 抽象メソッドは継承クラスでテスト実装
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.base_feed_service import Article, BaseFeedService

# JST timezone helper
JST = timezone(timedelta(hours=9))

# =============================================================================
# テスト用のBaseFeedService実装クラス
# =============================================================================


class TestFeedService(BaseFeedService):
    """テスト用のBaseFeedService実装（抽象メソッドを実装）"""

    def __init__(self):
        # setup_loggerをモック化して初期化
        with patch("nook.common.base_service.setup_logger"):
            super().__init__(service_name="test_feed_service")

    def _extract_popularity(self, soup: BeautifulSoup, entry: dict) -> float:
        """人気スコア抽出（テスト用実装）"""
        return 10.0

    def _get_markdown_header(self) -> str:
        """Markdownヘッダー取得（テスト用実装）"""
        return "Test Feed"

    def _get_summary_system_instruction(self) -> str:
        """システム指示取得（テスト用実装）"""
        return "Summarize this article."

    def _get_summary_prompt_template(self, article: Article) -> str:
        """プロンプトテンプレート取得（テスト用実装）"""
        return f"Please summarize: {article.title}"

    async def collect(self):
        """収集メソッド（テスト用ダミー）"""
        pass


# =============================================================================
# 1. _get_all_existing_dates メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_existing_dates_with_valid_files(temp_data_dir, mock_env_vars):
    """
    Given: 有効な日付形式のJSONファイルが複数存在
    When: _get_all_existing_datesを呼び出す
    Then: すべての日付がセットで返される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)

    # 有効な日付ファイルを作成
    (temp_data_dir / "2024-01-15.json").write_text("{}")
    (temp_data_dir / "2024-02-20.json").write_text("{}")
    (temp_data_dir / "2024-03-10.json").write_text("{}")

    # Act
    result = await service._get_all_existing_dates()

    # Assert
    assert len(result) == 3
    assert date(2024, 1, 15) in result
    assert date(2024, 2, 20) in result
    assert date(2024, 3, 10) in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_existing_dates_with_invalid_filenames(temp_data_dir, mock_env_vars):
    """
    Given: 無効な日付形式のファイルが混在
    When: _get_all_existing_datesを呼び出す
    Then: 有効な日付のみが返され、無効なファイルは無視される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)

    # 有効・無効な日付ファイルを作成
    (temp_data_dir / "2024-01-15.json").write_text("{}")
    (temp_data_dir / "invalid-date.json").write_text("{}")
    (temp_data_dir / "2024-13-99.json").write_text("{}")  # 無効な月日
    (temp_data_dir / "readme.txt").write_text("")

    # Act
    result = await service._get_all_existing_dates()

    # Assert
    assert len(result) == 1
    assert date(2024, 1, 15) in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_existing_dates_with_empty_directory(temp_data_dir, mock_env_vars):
    """
    Given: ストレージディレクトリが空
    When: _get_all_existing_datesを呼び出す
    Then: 空のセットが返される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)

    # Act
    result = await service._get_all_existing_dates()

    # Assert
    assert len(result) == 0
    assert isinstance(result, set)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_existing_dates_with_nonexistent_directory(tmp_path, mock_env_vars):
    """
    Given: ストレージディレクトリが存在しない
    When: _get_all_existing_datesを呼び出す
    Then: 空のセットが返される（エラーにならない）
    """
    # Arrange
    nonexistent_dir = tmp_path / "nonexistent"
    service = TestFeedService()
    service.storage.base_dir = Path(nonexistent_dir)

    # Act
    result = await service._get_all_existing_dates()

    # Assert
    assert len(result) == 0
    assert isinstance(result, set)


# =============================================================================
# 2. _filter_entries メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_filter_entries_within_target_dates(mock_env_vars, mock_feed_entry):
    """
    Given: 対象日付内のエントリ
    When: _filter_entriesを呼び出す
    Then: エントリが返される
    """
    # Arrange
    service = TestFeedService()
    target_dates = [date(2024, 11, 14)]
    entries = [mock_feed_entry]

    # Act
    result = service._filter_entries(entries, target_dates)

    # Assert
    assert len(result) == 1
    assert result[0] == mock_feed_entry


@pytest.mark.unit
def test_filter_entries_with_limit(mock_env_vars, mock_feed_entry):
    """
    Given: 複数エントリとリミット指定
    When: _filter_entriesを呼び出す
    Then: リミット数まで返される
    """
    # Arrange
    service = TestFeedService()
    target_dates = [date(2024, 11, 14)]
    entries = [mock_feed_entry, mock_feed_entry, mock_feed_entry]

    # Act
    result = service._filter_entries(entries, target_dates, limit=2)

    # Assert
    assert len(result) == 2


@pytest.mark.unit
def test_filter_entries_without_limit(mock_env_vars, mock_feed_entry):
    """
    Given: 複数エントリとリミットなし
    When: _filter_entriesを呼び出す
    Then: すべてのエントリが返される
    """
    # Arrange
    service = TestFeedService()
    target_dates = [date(2024, 11, 14)]
    entries = [mock_feed_entry, mock_feed_entry, mock_feed_entry]

    # Act
    result = service._filter_entries(entries, target_dates, limit=None)

    # Assert
    assert len(result) == 3


@pytest.mark.unit
def test_filter_entries_with_empty_entries(mock_env_vars):
    """
    Given: 空のエントリリスト
    When: _filter_entriesを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    target_dates = [date(2024, 11, 14)]
    entries = []

    # Act
    result = service._filter_entries(entries, target_dates)

    # Assert
    assert len(result) == 0


# =============================================================================
# 3. _group_articles_by_date メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_group_articles_by_date_normal(mock_env_vars, article_factory):
    """
    Given: 異なる日付の記事リスト
    When: _group_articles_by_dateを呼び出す
    Then: 日付ごとにグループ化された辞書が返される
    """
    # Arrange
    service = TestFeedService()

    # naive datetimeはUTCとして扱われ、JST(UTC+9)に変換されるため、
    # UTCの10:00, 11:00はJSTの19:00, 20:00（同じ日）になる
    article1 = article_factory(title="記事1")
    article1.published_at = datetime(2024, 11, 14, 10, 0, 0, tzinfo=JST)

    article2 = article_factory(title="記事2")
    article2.published_at = datetime(2024, 11, 14, 15, 0, 0, tzinfo=JST)

    article3 = article_factory(title="記事3")
    article3.published_at = datetime(2024, 11, 15, 10, 0, 0, tzinfo=JST)

    articles = [article1, article2, article3]

    # Act
    result = service._group_articles_by_date(articles)

    # Assert
    # article1: 2024-11-14 10:00 UTC → 2024-11-14 19:00 JST (2024-11-14)
    # article2: 2024-11-14 11:00 UTC → 2024-11-14 20:00 JST (2024-11-14)
    # article3: 2024-11-15 10:00 UTC → 2024-11-15 19:00 JST (2024-11-15)
    assert len(result) == 2
    assert "2024-11-14" in result
    assert "2024-11-15" in result
    assert len(result["2024-11-14"]) == 2
    assert len(result["2024-11-15"]) == 1


@pytest.mark.unit
def test_group_articles_by_date_with_none_published_at(mock_env_vars, article_factory):
    """
    Given: published_atがNoneの記事
    When: _group_articles_by_dateを呼び出す
    Then: デフォルト日付（今日）でグループ化される
    """
    # Arrange
    service = TestFeedService()

    article = article_factory(title="記事1")
    article.published_at = None

    articles = [article]

    # Act
    with patch("nook.services.base_feed_service.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 11, 14, 12, 0, 0)
        mock_datetime.strftime = datetime.strftime
        result = service._group_articles_by_date(articles)

    # Assert
    assert "2024-11-14" in result
    assert len(result["2024-11-14"]) == 1


@pytest.mark.unit
def test_group_articles_by_date_with_empty_list(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _group_articles_by_dateを呼び出す
    Then: 空の辞書が返される
    """
    # Arrange
    service = TestFeedService()
    articles = []

    # Act
    result = service._group_articles_by_date(articles)

    # Assert
    assert len(result) == 0
    assert isinstance(result, dict)


# =============================================================================
# 4. _serialize_articles メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_serialize_articles_normal(mock_env_vars, article_factory):
    """
    Given: 通常の記事リスト
    When: _serialize_articlesを呼び出す
    Then: dict形式にシリアライズされる
    """
    # Arrange
    service = TestFeedService()

    article = article_factory(
        title="テスト記事",
        url="https://example.com/test",
        text="本文テキスト",
        category="tech",
        popularity_score=15.0,
    )
    article.published_at = datetime(2024, 11, 14, 12, 0, 0)
    article.summary = "要約テキスト"

    articles = [article]

    # Act
    result = service._serialize_articles(articles)

    # Assert
    assert len(result) == 1
    assert result[0]["title"] == "テスト記事"
    assert result[0]["url"] == "https://example.com/test"
    assert result[0]["summary"] == "要約テキスト"
    assert result[0]["popularity_score"] == 15.0
    assert result[0]["category"] == "tech"
    assert result[0]["published_at"] == "2024-11-14T12:00:00"


@pytest.mark.unit
def test_serialize_articles_with_none_category(mock_env_vars, article_factory):
    """
    Given: categoryがNoneの記事
    When: _serialize_articlesを呼び出す
    Then: categoryが"uncategorized"に設定される
    """
    # Arrange
    service = TestFeedService()

    article = article_factory(title="記事1", category=None)
    articles = [article]

    # Act
    result = service._serialize_articles(articles)

    # Assert
    assert result[0]["category"] == "uncategorized"


@pytest.mark.unit
def test_serialize_articles_with_none_published_at(mock_env_vars, article_factory):
    """
    Given: published_atがNoneの記事
    When: _serialize_articlesを呼び出す
    Then: published_atがNoneのままシリアライズされる
    """
    # Arrange
    service = TestFeedService()

    article = article_factory(title="記事1")
    article.published_at = None
    articles = [article]

    # Act
    result = service._serialize_articles(articles)

    # Assert
    assert result[0]["published_at"] is None


@pytest.mark.unit
def test_serialize_articles_with_empty_list(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _serialize_articlesを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    articles = []

    # Act
    result = service._serialize_articles(articles)

    # Assert
    assert len(result) == 0
    assert isinstance(result, list)


# =============================================================================
# 5. _safe_parse_int メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_safe_parse_int_with_int(mock_env_vars):
    """
    Given: 整数値
    When: _safe_parse_intを呼び出す
    Then: そのまま整数が返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int(123)

    # Assert
    assert result == 123


@pytest.mark.unit
def test_safe_parse_int_with_float(mock_env_vars):
    """
    Given: 浮動小数点値
    When: _safe_parse_intを呼び出す
    Then: 整数に変換される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int(123.45)

    # Assert
    assert result == 123


@pytest.mark.unit
def test_safe_parse_int_with_numeric_string(mock_env_vars):
    """
    Given: 数値文字列
    When: _safe_parse_intを呼び出す
    Then: 整数が返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("456")

    # Assert
    assert result == 456


@pytest.mark.unit
def test_safe_parse_int_with_comma_separated_string(mock_env_vars):
    """
    Given: カンマ区切りの数値文字列
    When: _safe_parse_intを呼び出す
    Then: カンマを除去して整数が返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("1,234")

    # Assert
    assert result == 1234


@pytest.mark.unit
def test_safe_parse_int_with_text_and_number(mock_env_vars):
    """
    Given: テキストと数値が混在した文字列
    When: _safe_parse_intを呼び出す
    Then: 最初の数値が抽出される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("Price: 999 yen")

    # Assert
    assert result == 999


@pytest.mark.unit
def test_safe_parse_int_with_negative_number(mock_env_vars):
    """
    Given: 負の数値文字列
    When: _safe_parse_intを呼び出す
    Then: 負の整数が返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("-50")

    # Assert
    assert result == -50


@pytest.mark.unit
def test_safe_parse_int_with_none(mock_env_vars):
    """
    Given: None値
    When: _safe_parse_intを呼び出す
    Then: Noneが返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int(None)

    # Assert
    assert result is None


@pytest.mark.unit
def test_safe_parse_int_with_no_number_string(mock_env_vars):
    """
    Given: 数値を含まない文字列
    When: _safe_parse_intを呼び出す
    Then: Noneが返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("no numbers here")

    # Assert
    assert result is None


@pytest.mark.unit
def test_safe_parse_int_with_empty_string(mock_env_vars):
    """
    Given: 空文字列
    When: _safe_parse_intを呼び出す
    Then: Noneが返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._safe_parse_int("")

    # Assert
    assert result is None


# =============================================================================
# 6. _load_existing_articles メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_articles_from_json(temp_data_dir, mock_env_vars):
    """
    Given: JSONファイルが存在
    When: _load_existing_articlesを呼び出す
    Then: JSONから記事が読み込まれる
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)
    target_date = datetime(2024, 11, 14, 12, 0, 0)

    # JSONファイルを作成
    json_data = [
        {
            "title": "記事1",
            "url": "https://example.com/1",
            "feed_name": "テストフィード",
            "summary": "要約1",
            "popularity_score": 10.0,
            "published_at": "2024-11-14T12:00:00",
            "category": "tech",
        }
    ]
    json_file = temp_data_dir / "2024-11-14.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False))

    # Act
    result = await service._load_existing_articles(target_date)

    # Assert
    assert len(result) == 1
    assert result[0]["title"] == "記事1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_articles_from_markdown(temp_data_dir, mock_env_vars):
    """
    Given: JSONファイルが存在せずMarkdownファイルが存在
    When: _load_existing_articlesを呼び出す
    Then: Markdownから記事が読み込まれる
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)
    target_date = datetime(2024, 11, 14, 12, 0, 0)

    # Markdownファイルを作成
    markdown_content = """## Tech

### [記事タイトル](https://example.com/article)

**フィード**: テストフィード

**要約**:
これは要約テキストです。

---
"""
    md_file = temp_data_dir / "2024-11-14.md"
    md_file.write_text(markdown_content)

    # Act
    result = await service._load_existing_articles(target_date)

    # Assert
    assert len(result) == 1
    assert result[0]["title"] == "記事タイトル"
    assert result[0]["url"] == "https://example.com/article"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_existing_articles_no_files(temp_data_dir, mock_env_vars):
    """
    Given: ファイルが存在しない
    When: _load_existing_articlesを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)
    target_date = datetime(2024, 11, 14, 12, 0, 0)

    # Act
    result = await service._load_existing_articles(target_date)

    # Assert
    assert len(result) == 0
    assert isinstance(result, list)


# =============================================================================
# 7. _article_sort_key メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_article_sort_key_normal(mock_env_vars):
    """
    Given: 通常の記事データ
    When: _article_sort_keyを呼び出す
    Then: タプル(人気スコア、日時)が返される
    """
    # Arrange
    service = TestFeedService()
    item = {
        "popularity_score": 15.0,
        "published_at": "2024-11-14T12:00:00",
    }

    # Act
    result = service._article_sort_key(item)

    # Assert
    assert result[0] == 15.0
    assert result[1] == datetime(2024, 11, 14, 12, 0, 0)


@pytest.mark.unit
def test_article_sort_key_with_none_popularity(mock_env_vars):
    """
    Given: popularity_scoreがNone
    When: _article_sort_keyを呼び出す
    Then: popularity_scoreが0.0として扱われる
    """
    # Arrange
    service = TestFeedService()
    item = {
        "popularity_score": None,
        "published_at": "2024-11-14T12:00:00",
    }

    # Act
    result = service._article_sort_key(item)

    # Assert
    assert result[0] == 0.0


@pytest.mark.unit
def test_article_sort_key_with_invalid_published_at(mock_env_vars):
    """
    Given: published_atが不正な形式
    When: _article_sort_keyを呼び出す
    Then: datetime.minとして扱われる
    """
    # Arrange
    service = TestFeedService()
    item = {
        "popularity_score": 10.0,
        "published_at": "invalid-date",
    }

    # Act
    result = service._article_sort_key(item)

    # Assert
    assert result[1] == datetime.min


@pytest.mark.unit
def test_article_sort_key_with_none_published_at(mock_env_vars):
    """
    Given: published_atがNone
    When: _article_sort_keyを呼び出す
    Then: datetime.minとして扱われる
    """
    # Arrange
    service = TestFeedService()
    item = {
        "popularity_score": 10.0,
        "published_at": None,
    }

    # Act
    result = service._article_sort_key(item)

    # Assert
    assert result[1] == datetime.min


# =============================================================================
# 8. _parse_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_parse_markdown_with_single_category(mock_env_vars):
    """
    Given: 1つのカテゴリと記事を含むMarkdown
    When: _parse_markdownを呼び出す
    Then: 記事が正しく解析される
    """
    # Arrange
    service = TestFeedService()
    markdown = """## Tech

### [記事タイトル](https://example.com/article)

**フィード**: テストフィード

**要約**:
これは要約テキストです。

---
"""

    # Act
    result = service._parse_markdown(markdown)

    # Assert
    assert len(result) == 1
    assert result[0]["title"] == "記事タイトル"
    assert result[0]["url"] == "https://example.com/article"
    assert result[0]["feed_name"] == "テストフィード"
    assert result[0]["summary"] == "これは要約テキストです。"
    assert result[0]["category"] == "tech"


@pytest.mark.unit
def test_parse_markdown_with_multiple_categories(mock_env_vars):
    """
    Given: 複数カテゴリと記事を含むMarkdown
    When: _parse_markdownを呼び出す
    Then: すべての記事が正しく解析される
    """
    # Arrange
    service = TestFeedService()
    markdown = """## Tech

### [記事1](https://example.com/1)

**フィード**: フィード1

**要約**:
要約1

---

## Business News

### [記事2](https://example.com/2)

**フィード**: フィード2

**要約**:
要約2

---
"""

    # Act
    result = service._parse_markdown(markdown)

    # Assert
    assert len(result) == 2
    assert result[0]["category"] == "tech"
    assert result[1]["category"] == "business_news"


@pytest.mark.unit
def test_parse_markdown_with_empty_string(mock_env_vars):
    """
    Given: 空のMarkdown文字列
    When: _parse_markdownを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    markdown = ""

    # Act
    result = service._parse_markdown(markdown)

    # Assert
    assert len(result) == 0


@pytest.mark.unit
def test_parse_markdown_with_no_articles(mock_env_vars):
    """
    Given: カテゴリのみで記事がないMarkdown
    When: _parse_markdownを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    markdown = """## Tech

## Business

"""

    # Act
    result = service._parse_markdown(markdown)

    # Assert
    assert len(result) == 0


# =============================================================================
# 9. _select_top_articles メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_select_top_articles_within_limit(mock_env_vars, article_factory):
    """
    Given: TOTAL_LIMIT以下の記事リスト
    When: _select_top_articlesを呼び出す
    Then: すべての記事が返される
    """
    # Arrange
    service = TestFeedService()

    articles = []
    for i in range(3):
        article = article_factory(title=f"記事{i}", popularity_score=float(10 - i))
        article.published_at = datetime(2024, 11, 14, 12, 0, 0)
        articles.append(article)

    # Act
    result = service._select_top_articles(articles)

    # Assert
    assert len(result) == 3


@pytest.mark.unit
def test_select_top_articles_exceeds_limit(mock_env_vars, article_factory):
    """
    Given: TOTAL_LIMITを超える記事リスト
    When: _select_top_articlesを呼び出す
    Then: 上位TOTAL_LIMIT件が返される
    """
    # Arrange
    service = TestFeedService()

    # TOTAL_LIMIT + 5の記事を作成
    articles = []
    for i in range(service.TOTAL_LIMIT + 5):
        article = article_factory(title=f"記事{i}", popularity_score=float(100 - i))
        article.published_at = datetime(2024, 11, 14, 12, 0, 0)
        articles.append(article)

    # Act
    result = service._select_top_articles(articles)

    # Assert
    assert len(result) == service.TOTAL_LIMIT
    # 人気スコアが高い順に選択されていることを確認
    assert result[0].popularity_score >= result[-1].popularity_score


@pytest.mark.unit
def test_select_top_articles_with_empty_list(mock_env_vars):
    """
    Given: 空の記事リスト
    When: _select_top_articlesを呼び出す
    Then: 空のリストが返される
    """
    # Arrange
    service = TestFeedService()
    articles = []

    # Act
    result = service._select_top_articles(articles)

    # Assert
    assert len(result) == 0


@pytest.mark.unit
def test_select_top_articles_with_multiple_dates(mock_env_vars, article_factory):
    """
    Given: 複数の日付にまたがる記事リスト
    When: _select_top_articlesを呼び出す
    Then: 各日付ごとにTOTAL_LIMIT件まで選択される
    """
    # Arrange
    service = TestFeedService()

    articles = []
    # 日付1の記事
    for i in range(3):
        article = article_factory(title=f"日付1_記事{i}", popularity_score=float(10 - i))
        article.published_at = datetime(2024, 11, 14, 12, 0, 0)
        articles.append(article)

    # 日付2の記事
    for i in range(3):
        article = article_factory(title=f"日付2_記事{i}", popularity_score=float(10 - i))
        article.published_at = datetime(2024, 11, 15, 12, 0, 0)
        articles.append(article)

    # Act
    result = service._select_top_articles(articles)

    # Assert
    assert len(result) == 6  # 両日付とも3件ずつ


# =============================================================================
# 10. _store_summaries_for_date メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_for_date_normal(temp_data_dir, mock_env_vars, article_factory):
    """
    Given: 記事リストと日付文字列
    When: _store_summaries_for_dateを呼び出す
    Then: JSONとMarkdownファイルが作成される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)

    article = article_factory(title="記事1", url="https://example.com/1")
    article.published_at = datetime(2024, 11, 14, 12, 0, 0)
    article.summary = "要約テキスト"

    articles = [article]
    date_str = "2024-11-14"

    # Act
    json_path, md_path = await service._store_summaries_for_date(articles, date_str)

    # Assert
    assert json_path != ""
    assert md_path != ""
    assert (temp_data_dir / "2024-11-14.json").exists()
    assert (temp_data_dir / "2024-11-14.md").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_for_date_with_empty_articles(temp_data_dir, mock_env_vars):
    """
    Given: 空の記事リスト
    When: _store_summaries_for_dateを呼び出す
    Then: 空の文字列が返される
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)
    articles = []
    date_str = "2024-11-14"

    # Act
    json_path, md_path = await service._store_summaries_for_date(articles, date_str)

    # Assert
    assert json_path == ""
    assert md_path == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_for_date_merges_with_existing(
    temp_data_dir, mock_env_vars, article_factory
):
    """
    Given: 既存ファイルと新規記事
    When: _store_summaries_for_dateを呼び出す
    Then: 既存記事とマージされる
    """
    # Arrange
    service = TestFeedService()
    service.storage.base_dir = Path(temp_data_dir)
    date_str = "2024-11-14"

    # 既存ファイルを作成
    existing_data = [
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
    json_file = temp_data_dir / "2024-11-14.json"
    json_file.write_text(json.dumps(existing_data, ensure_ascii=False))

    # 新規記事
    new_article = article_factory(title="新規記事", popularity_score=20.0)
    new_article.published_at = datetime(2024, 11, 14, 12, 0, 0)
    new_article.summary = "新規要約"

    # Act
    await service._store_summaries_for_date([new_article], date_str)

    # Assert
    # JSONファイルを読み込んで確認
    with open(temp_data_dir / "2024-11-14.json") as f:
        merged_data = json.load(f)

    assert len(merged_data) == 2
    # 人気スコア順でソートされているはず
    assert merged_data[0]["title"] == "新規記事"  # 高いスコア


# =============================================================================
# 11. _render_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_render_markdown_normal(mock_env_vars):
    """
    Given: 通常の記事レコードリスト
    When: _render_markdownを呼び出す
    Then: Markdown形式の文字列が返される
    """
    # Arrange
    service = TestFeedService()
    records = [
        {
            "title": "記事1",
            "url": "https://example.com/1",
            "feed_name": "フィード1",
            "summary": "要約1",
            "category": "tech",
        }
    ]
    today = datetime(2024, 11, 14, 12, 0, 0)

    # Act
    result = service._render_markdown(records, today)

    # Assert
    assert "# Test Feed (2024-11-14)" in result
    assert "## Tech" in result
    assert "### [記事1](https://example.com/1)" in result
    assert "**フィード**: フィード1" in result
    assert "**要約**:\n要約1" in result


@pytest.mark.unit
def test_render_markdown_with_multiple_categories(mock_env_vars):
    """
    Given: 複数カテゴリの記事レコード
    When: _render_markdownを呼び出す
    Then: カテゴリごとにセクション分けされたMarkdownが返される
    """
    # Arrange
    service = TestFeedService()
    records = [
        {
            "title": "Tech記事",
            "url": "https://example.com/tech",
            "feed_name": "Techフィード",
            "summary": "Tech要約",
            "category": "tech",
        },
        {
            "title": "Business記事",
            "url": "https://example.com/business",
            "feed_name": "Businessフィード",
            "summary": "Business要約",
            "category": "business_news",
        },
    ]
    today = datetime(2024, 11, 14, 12, 0, 0)

    # Act
    result = service._render_markdown(records, today)

    # Assert
    assert "## Tech" in result
    assert "## Business news" in result


@pytest.mark.unit
def test_render_markdown_with_empty_records(mock_env_vars):
    """
    Given: 空の記事レコードリスト
    When: _render_markdownを呼び出す
    Then: ヘッダーのみのMarkdownが返される
    """
    # Arrange
    service = TestFeedService()
    records = []
    today = datetime(2024, 11, 14, 12, 0, 0)

    # Act
    result = service._render_markdown(records, today)

    # Assert
    assert "# Test Feed (2024-11-14)" in result
    assert "##" not in result.split("\n")[2]  # カテゴリヘッダーなし


# =============================================================================
# 12. _summarize_article メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_article_success(mock_env_vars, article_factory):
    """
    Given: 記事オブジェクトとGPTクライアント
    When: _summarize_articleを呼び出す
    Then: 記事のsummaryフィールドが設定される
    """
    # Arrange
    service = TestFeedService()
    article = article_factory(title="記事1")

    # GPTクライアントをモック化
    mock_gpt = Mock()
    mock_gpt.generate_content = Mock(return_value="生成された要約")
    service.gpt_client = mock_gpt

    # Act
    await service._summarize_article(article)

    # Assert
    assert article.summary == "生成された要約"
    mock_gpt.generate_content.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_article_with_error(mock_env_vars, article_factory):
    """
    Given: GPTクライアントがエラーを発生
    When: _summarize_articleを呼び出す
    Then: エラーメッセージがsummaryに設定される
    """
    # Arrange
    service = TestFeedService()
    article = article_factory(title="記事1")

    # GPTクライアントがエラーを発生するようにモック化
    mock_gpt = Mock()
    mock_gpt.generate_content = Mock(side_effect=Exception("API Error"))
    service.gpt_client = mock_gpt

    # Act
    await service._summarize_article(article)

    # Assert
    assert "要約の生成中にエラーが発生しました" in article.summary
    assert "API Error" in article.summary


# =============================================================================
# 13. _needs_japanese_check メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_needs_japanese_check_default(mock_env_vars):
    """
    Given: BaseFeedServiceのデフォルト実装
    When: _needs_japanese_checkを呼び出す
    Then: Falseが返される
    """
    # Arrange
    service = TestFeedService()

    # Act
    result = service._needs_japanese_check()

    # Assert
    assert result is False


# =============================================================================
# 14. _detect_japanese_content メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_detect_japanese_content_with_html_lang_ja(mock_env_vars):
    """
    Given: html langタグがjaのHTML
    When: _detect_japanese_contentを呼び出す
    Then: Trueが返される
    """
    # Arrange
    service = TestFeedService()
    html = '<html lang="ja"><body><p>Test</p></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://example.com"

    # Act
    result = service._detect_japanese_content(soup, "Test", entry)

    # Assert
    assert result is True


@pytest.mark.unit
def test_detect_japanese_content_with_japanese_title(mock_env_vars):
    """
    Given: 日本語文字を含むタイトル
    When: _detect_japanese_contentを呼び出す
    Then: Trueが返される
    """
    # Arrange
    service = TestFeedService()
    html = "<html><body><p>Test</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://example.com"

    # Act
    result = service._detect_japanese_content(soup, "これは日本語のタイトルです", entry)

    # Assert
    assert result is True


@pytest.mark.unit
def test_detect_japanese_content_with_japanese_paragraph(mock_env_vars):
    """
    Given: 日本語文字を含む段落
    When: _detect_japanese_contentを呼び出す
    Then: Trueが返される
    """
    # Arrange
    service = TestFeedService()
    html = "<html><body><p>これは日本語の段落です。テストに使います。</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://example.com"
    entry.summary = ""  # 文字列として設定

    # Act
    result = service._detect_japanese_content(soup, "Test", entry)

    # Assert
    assert result is True


@pytest.mark.unit
def test_detect_japanese_content_with_japanese_domain(mock_env_vars):
    """
    Given: 日本語ドメインのURL
    When: _detect_japanese_contentを呼び出す
    Then: Trueが返される
    """
    # Arrange
    service = TestFeedService()
    html = "<html><body><p>Test</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://www.nikkei.com/article/test"
    entry.summary = ""  # 文字列として設定

    # Act
    result = service._detect_japanese_content(soup, "Test", entry)

    # Assert
    assert result is True


@pytest.mark.unit
def test_detect_japanese_content_with_english_only(mock_env_vars):
    """
    Given: 英語のみのコンテンツ
    When: _detect_japanese_contentを呼び出す
    Then: Falseが返される
    """
    # Arrange
    service = TestFeedService()
    html = '<html lang="en"><body><p>This is an English article.</p></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://example.com"
    entry.summary = ""  # 文字列として設定

    # Act
    result = service._detect_japanese_content(soup, "Test Article", entry)

    # Assert
    assert result is False


@pytest.mark.unit
def test_detect_japanese_content_with_meta_lang(mock_env_vars):
    """
    Given: metaタグでcontent-language=jaのHTML
    When: _detect_japanese_contentを呼び出す
    Then: Trueが返される
    """
    # Arrange
    service = TestFeedService()
    html = '<html><head><meta http-equiv="content-language" content="ja"></head><body><p>Test</p></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    entry = Mock()
    entry.link = "https://example.com"

    # Act
    result = service._detect_japanese_content(soup, "Test", entry)

    # Assert
    assert result is True
