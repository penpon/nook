import sys
import types
from collections import namedtuple
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr


# bs4 が無くても動かせるように簡易スタブを注入
class _DummyBS4Module(types.SimpleNamespace):
    def __init__(self):
        super().__init__(BeautifulSoup=object)


_ORIGINAL_BS4 = sys.modules.get("bs4")
# Baseクラスimport時にbs4が必要になるため、未インストール時のみ一時的にスタブを差し込む
if _ORIGINAL_BS4 is None:
    sys.modules["bs4"] = _DummyBS4Module()

from nook.core.config import BaseConfig  # noqa: E402
from nook.services.base_feed_service import Article, BaseFeedService  # noqa: E402

# import 完了後は元の状態に戻す
if _ORIGINAL_BS4 is None:
    sys.modules.pop("bs4", None)
else:
    sys.modules["bs4"] = _ORIGINAL_BS4


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """必須環境変数をテスト用ダミーで埋める"""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")


@pytest.fixture(autouse=True)
def _stub_bs4(monkeypatch):
    monkeypatch.setitem(sys.modules, "bs4", _DummyBS4Module())
    yield
    if _ORIGINAL_BS4 is not None:
        monkeypatch.setitem(sys.modules, "bs4", _ORIGINAL_BS4)
    else:
        sys.modules.pop("bs4", None)


class DummyConfig(BaseConfig):
    OPENAI_API_KEY: SecretStr = SecretStr("dummy-key")


class MockGPTClient:
    def __init__(self):
        self.generate_content_called = False
        self.generate_content_return = "Generated Summary"
        self.raise_error = None

    def generate_content(self, prompt, system_instruction, temperature, max_tokens):
        self.generate_content_called = True
        if self.raise_error:
            raise self.raise_error
        return self.generate_content_return


class DummyFeedService(BaseFeedService):
    TOTAL_LIMIT = 2

    def __init__(self):
        super().__init__("dummy", config=DummyConfig())
        # データディレクトリをテスト用に差し替える（各テストで上書き可）
        self.storage = types.SimpleNamespace(
            base_dir="dummy_data",
            save=lambda data, filename: Path(filename),
            load=lambda filename: None,
            exists=lambda filename: False,
            rename=lambda old, new: None,
            glob=lambda pattern: [],
        )
        self._existing: list[dict] = []
        self.gpt_client = MockGPTClient()
        self.logger = types.SimpleNamespace(
            debug=lambda msg, *args: None,
            info=lambda msg, *args: None,
            error=lambda msg, *args: None,
        )

    async def collect(self):  # pragma: no cover - テストでは直接呼ばない
        return []

    # 抽象メソッドの最小実装
    def _extract_popularity(self, _, __) -> float:  # pragma: no cover
        return 0.0

    def _get_markdown_header(self) -> str:
        return "Dummy Header"

    def _get_summary_system_instruction(self) -> str:
        return "System Instruction"

    def _get_summary_prompt_template(self, _) -> str:
        return "Prompt Template"

    async def _load_existing_articles(self, target_date: datetime) -> list[dict]:
        return self._existing

    async def save_json(self, data, filename):
        self._saved_json = {"data": data, "filename": filename}
        return Path(filename)

    async def save_markdown(self, content: str, filename: str):
        self._saved_md = {"content": content, "filename": filename}
        return Path(filename)


def make_article(
    feed_name: str,
    title: str,
    popularity: float = 0.0,
    published_at: datetime | None = None,
    category: str | None = None,
) -> Article:
    return Article(
        feed_name=feed_name,
        title=title,
        url=f"https://example.com/{title}",
        text="body",
        soup=None,
        category=category,
        popularity_score=popularity,
        published_at=published_at,
    )


def test_filter_entries_respects_dates_and_limit():
    service = DummyFeedService()
    # Given
    entries = [
        {"published": "2024-01-01T00:00:00Z"},
        {"published": "2024-01-02T00:00:00Z"},
        {"updated": "2023-12-31T00:00:00Z"},  # Out of range
        {"no_date": "invalid"},  # Should be skipped
    ]
    targets = [date(2024, 1, 1), date(2024, 1, 2)]

    # When
    filtered = service._filter_entries(entries, targets, limit=1)

    # Then
    assert len(filtered) == 1
    assert filtered[0]["published"] == "2024-01-01T00:00:00Z"

    # Test without limit
    filtered_all = service._filter_entries(entries, targets)
    assert len(filtered_all) == 2


def test_safe_parse_int_variants():
    service = DummyFeedService()
    # Given
    targets = [3.5, "1,234", "abc", None, "500 comments"]

    # When & Then
    assert service._safe_parse_int(targets[0]) == 3
    assert service._safe_parse_int(targets[1]) == 1234
    assert service._safe_parse_int(targets[2]) is None
    assert service._safe_parse_int(targets[3]) is None
    assert service._safe_parse_int(targets[4]) == 500


def test_parse_markdown_extracts_articles():
    service = DummyFeedService()
    # Given
    md = (
        "## Tech\n\n"
        "### [Title](https://example.com)\n\n"
        "**フィード**: tech\n\n"
        "**要約**:\nSummary\n\n"
        "---\n"
        "## Business\n\n"
        "### [BizTitle](https://biz.example.com)\n\n"
        "**フィード**: biz\n\n"
        "**要約**:\nBizSummary\n\n"
        "---\n"
    )

    # When
    articles = service._parse_markdown(md)

    # Then
    assert len(articles) == 2
    assert articles[0]["title"] == "Title"
    assert articles[0]["category"] == "tech"
    assert articles[1]["title"] == "BizTitle"
    assert articles[1]["category"] == "business"


def test_select_top_articles_limits_per_day():
    service = DummyFeedService()
    service.TOTAL_LIMIT = 1
    # Given
    dt1 = datetime(2024, 1, 1)
    dt2 = datetime(2024, 1, 2)
    articles = [
        make_article("a", "day1_low", popularity=1, published_at=dt1),
        make_article("a", "day1_high", popularity=5, published_at=dt1),
        make_article("a", "day2_single", popularity=3, published_at=dt2),
        make_article(
            "a", "no_date", popularity=10, published_at=None
        ),  # Gets today's date usually or skipped in logic?
    ]
    # Note: _select_top_articles requires published_at to group by date.
    # If published_at is None, it won't be in articles_by_date unless handled.
    # The current implementation checks `if article.published_at:` so None is skipped.

    # When
    selected = service._select_top_articles(articles)

    # Then
    # Should have 1 from day1, 1 from day2. None date is skipped.
    assert len(selected) == 2
    titles = {a.title for a in selected}
    assert "day1_high" in titles
    assert "day2_single" in titles
    assert "day1_low" not in titles


def test_article_sort_key():
    service = DummyFeedService()
    # Case 1: Standard
    item1 = {"popularity_score": 10.0, "published_at": "2024-01-01T10:00:00"}
    key1 = service._article_sort_key(item1)
    assert key1 == (10.0, datetime(2024, 1, 1, 10, 0, 0))

    # Case 2: No popularity
    item2 = {"published_at": "2024-01-01T10:00:00"}
    key2 = service._article_sort_key(item2)
    assert key2 == (0.0, datetime(2024, 1, 1, 10, 0, 0))

    # Case 3: Invalid Date
    item3 = {"popularity_score": 5.0, "published_at": "invalid"}
    key3 = service._article_sort_key(item3)
    assert key3 == (5.0, datetime.min)

    # Case 4: No Date
    item4 = {"popularity_score": 3.0}
    key4 = service._article_sort_key(item4)
    assert key4 == (3.0, datetime.min)


@pytest.mark.asyncio
async def test_store_summaries_merges_and_saves():
    service = DummyFeedService()
    service.TOTAL_LIMIT = 2
    # Given
    dt = datetime(2024, 1, 1)
    service._existing = [
        {
            "title": "old",
            "url": "https://example.com/old",
            "feed_name": "tech",
            "summary": "old summary",
            "popularity_score": 1,
            "published_at": dt.isoformat(),
            "category": "tech",
        }
    ]

    articles = [
        make_article("tech", "new1", popularity=3, published_at=dt, category="tech"),
        make_article("tech", "new2", popularity=2, published_at=dt, category="tech"),
    ]

    # When
    json_path, md_path = await service._store_summaries_for_date(articles, "2024-01-01")

    # Then
    assert Path(json_path).name == "2024-01-01.json"
    assert Path(md_path).name == "2024-01-01.md"
    saved = service._saved_json["data"]
    # TOTAL_LIMIT=2 なので popularity 上位2件が残る
    titles = [item["title"] for item in saved]
    # new1(3), new2(2), old(1) -> new1, new2
    assert "new1" in titles
    assert "new2" in titles
    assert "old" not in titles


@pytest.mark.asyncio
async def test_summarize_article_success():
    service = DummyFeedService()
    article = make_article("feed", "title")

    # When
    await service._summarize_article(article)

    # Then
    assert service.gpt_client.generate_content_called
    assert article.summary == "Generated Summary"


@pytest.mark.asyncio
async def test_summarize_article_failure():
    service = DummyFeedService()
    service.gpt_client.raise_error = Exception("API Error")
    article = make_article("feed", "title")

    # When
    await service._summarize_article(article)

    # Then
    assert "エラーが発生しました" in article.summary
    assert "API Error" in article.summary


def test_detect_japanese_content():
    service = DummyFeedService()

    # Mock Soup and Entry
    MockSoup = namedtuple("MockSoup", ["find", "find_all"])
    MockTag = namedtuple("MockTag", ["get", "get_text"])

    # helper to build soup mock
    def build_mock_soup(lang=None, meta_lang=None, meta_desc=None, paragraph_text=None):
        def find(name, attrs=None):
            if name == "html":
                return MockTag(
                    get=lambda k: lang if k == "lang" else None, get_text=lambda: ""
                )
            if name == "meta":
                if attrs == {"http-equiv": "content-language"}:
                    return MockTag(
                        get=lambda k: meta_lang if k == "content" else None,
                        get_text=lambda: "",
                    )
                if attrs == {"name": "description"}:
                    return MockTag(
                        get=lambda k: meta_desc if k == "content" else None,
                        get_text=lambda: "",
                    )
            return None

        def find_all(name):
            if name == "p" and paragraph_text:
                return [MockTag(get=lambda k: None, get_text=lambda: paragraph_text)]
            return []

        return MockSoup(find=find, find_all=find_all)

    # Case 1: HTML lang
    soup1 = build_mock_soup(lang="ja")
    assert service._detect_japanese_content(soup1, "title", {}) is True

    # Case 2: Meta Lang
    soup2 = build_mock_soup(meta_lang="ja-JP")
    assert service._detect_japanese_content(soup2, "title", {}) is True

    # Case 3: Title Characters (Kanji/Kana)
    soup3 = build_mock_soup()
    assert service._detect_japanese_content(soup3, "日本語のタイトル", {}) is True
    assert service._detect_japanese_content(soup3, "English Title", {}) is False

    # Case 4: Content (Summary/Description/Paragraph)
    soup4 = build_mock_soup(
        paragraph_text="これは本文のサンプルです。日本語が含まれています。"
    )
    entry4 = types.SimpleNamespace(summary="English Summary")
    assert service._detect_japanese_content(soup4, "English Title", entry4) is True

    # Case 5: Domain
    soup5 = build_mock_soup()
    entry5 = types.SimpleNamespace(link="https://diamond.jp/articles/123", summary="")
    assert service._detect_japanese_content(soup5, "English Title", entry5) is True

    # Case 6: Fallback to False
    soup6 = build_mock_soup()
    entry6 = types.SimpleNamespace(link="https://example.com", summary="")
    assert service._detect_japanese_content(soup6, "English Title", entry6) is False


@pytest.mark.asyncio
async def test_get_all_existing_dates_with_tmp_path(tmp_path):
    service = DummyFeedService()
    service.storage.base_dir = str(tmp_path)

    # Create dummy files
    (tmp_path / "2024-01-01.json").touch()
    (tmp_path / "2024-01-02.json").touch()
    (tmp_path / "invalid.json").touch()

    # When
    dates = await service._get_all_existing_dates()

    # Then
    assert date(2024, 1, 1) in dates
    assert date(2024, 1, 2) in dates
    assert len(dates) == 2
