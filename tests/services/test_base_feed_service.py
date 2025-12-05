import sys
import types
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr


# bs4 が無くても動かせるように簡易スタブを注入
class _DummyBS4Module(types.SimpleNamespace):
    def __init__(self):
        super().__init__(BeautifulSoup=object)


_ORIGINAL_BS4 = sys.modules.get("bs4")
# Baseクラスimport時にbs4が必要になるため、一時的にスタブを差し込む
sys.modules["bs4"] = _DummyBS4Module()

from nook.common.config import BaseConfig
from nook.services.base_feed_service import Article, BaseFeedService

# import 完了後は元の状態に戻す
if _ORIGINAL_BS4 is not None:
    sys.modules["bs4"] = _ORIGINAL_BS4
else:
    sys.modules.pop("bs4", None)


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


class DummyFeedService(BaseFeedService):
    TOTAL_LIMIT = 2

    def __init__(self):
        super().__init__("dummy", config=DummyConfig())
        # データディレクトリをテスト用に差し替える（各テストで上書き可）
        self.storage = types.SimpleNamespace(
            save=lambda data, filename: Path(filename),
            load=lambda filename: None,
            exists=lambda filename: False,
            rename=lambda old, new: None,
        )
        self._existing: list[dict] = []

    async def collect(self):  # pragma: no cover - テストでは直接呼ばない
        return []

    # 抽象メソッドの最小実装
    def _extract_popularity(self, _, __) -> float:  # pragma: no cover
        return 0.0

    def _get_markdown_header(self) -> str:
        return "Dummy Header"

    def _get_summary_system_instruction(self) -> str:  # pragma: no cover
        return ""

    def _get_summary_prompt_template(self, _) -> str:  # pragma: no cover
        return ""

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
    ]
    targets = [date(2024, 1, 1)]

    # When
    filtered = service._filter_entries(entries, targets, limit=1)

    # Then
    assert filtered == [entries[0]]


def test_safe_parse_int_variants():
    service = DummyFeedService()
    # Given
    targets = [3.5, "1,234", "abc", None]

    # When & Then
    assert service._safe_parse_int(targets[0]) == 3
    assert service._safe_parse_int(targets[1]) == 1234
    assert service._safe_parse_int(targets[2]) is None
    assert service._safe_parse_int(targets[3]) is None


def test_parse_markdown_extracts_articles():
    service = DummyFeedService()
    # Given
    md = (
        "## Tech\n\n"
        "### [Title](https://example.com)\n\n"
        "**フィード**: tech\n\n"
        "**要約**:\nSummary\n\n"
        "---\n"
    )

    # When
    articles = service._parse_markdown(md)

    # Then
    assert articles == [
        {
            "title": "Title",
            "url": "https://example.com",
            "feed_name": "tech",
            "summary": "Summary",
            "popularity_score": 0.0,
            "published_at": None,
            "category": "tech",
        }
    ]


def test_select_top_articles_limits_per_day():
    service = DummyFeedService()
    service.TOTAL_LIMIT = 1
    # Given
    dt = datetime(2024, 1, 1)
    articles = [
        make_article("a", "low", popularity=1, published_at=dt),
        make_article("a", "high", popularity=5, published_at=dt),
    ]

    # When
    selected = service._select_top_articles(articles)

    # Then
    assert len(selected) == 1
    assert selected[0].title == "high"


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
    assert titles == ["new1", "new2"]
