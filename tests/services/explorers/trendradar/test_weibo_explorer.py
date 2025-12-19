"""WeiboExplorerのテストモジュール."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.weibo_explorer import WeiboExplorer


@pytest.fixture
def mock_trendradar_client():
    with patch("nook.services.explorers.trendradar.base.TrendRadarClient") as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value = client_instance
        yield client_instance


@pytest.fixture
def explorer(mock_trendradar_client):
    return WeiboExplorer(storage_dir="test_data")


@pytest.mark.asyncio
async def test_initialization(explorer):
    """初期化のテスト."""
    assert explorer.service_name == "trendradar-weibo"
    assert explorer.PLATFORM_NAME == "weibo"
    assert explorer.FEED_NAME == "weibo"
    assert explorer.MARKDOWN_HEADER == "微博ホットサーチ"


@pytest.mark.asyncio
async def test_get_summary_prompt(explorer):
    """プロンプト生成のテスト."""
    article = Article(
        feed_name="weibo",
        title="Test Title",
        url="http://example.com",
        text="Test Description",
        soup=None,
        published_at=datetime.now(timezone.utc),
    )

    prompt = explorer._get_summary_prompt(article)

    assert "微博（Weibo）ホットサーチ" in prompt
    assert "Test Title" in prompt
    assert "Test Description" in prompt
    assert "トレンドの概要" in prompt
    assert "3. 世論の傾向" in prompt
    assert "4. 文化的背景" in prompt


@pytest.mark.asyncio
async def test_get_system_instruction(explorer):
    """システム指示取得のテスト."""
    instruction = explorer._get_system_instruction()

    assert "微博" in instruction
    assert "Weibo" in instruction
    assert "日本のユーザーに向けて" in instruction
    assert "文化的コンテキスト" in instruction


@pytest.mark.asyncio
async def test_collect_success(explorer, mock_trendradar_client):
    """収集処理の成功ケース."""
    # Mock data
    mock_trendradar_client.get_latest_news.return_value = [
        {
            "title": "Article 1",
            "url": "http://example.com/1",
            "desc": "Desc 1",
            "hot": "100万",
            "time": "2024-03-20 10:00:00",
        }
    ]

    # Mocking _summarize_article to avoid GPT calls and complexity
    with patch.object(explorer, "_summarize_article", new_callable=AsyncMock) as mock_summarize:
        with patch.object(explorer, "_store_articles", new_callable=AsyncMock) as mock_store:
            mock_store.return_value = [("path/to.json", "path/to.md")]

            result = await explorer.collect(days=1, limit=5)

            assert len(result) == 1
            mock_trendradar_client.get_latest_news.assert_called_once_with(platform="weibo", limit=5)
            mock_summarize.assert_called_once()
            mock_store.assert_called_once()


@pytest.mark.asyncio
async def test_transform_to_article_valid(explorer):
    """_transform_to_article: 正常な変換のテスト."""
    item = {
        "title": "Valid Title",
        "url": "http://example.com/valid",
        "desc": "Valid Description",
        "hot": "150万",
        "time": "2024-03-20 10:30:00",
    }

    article = explorer._transform_to_article(item)

    assert article.title == "Valid Title"
    assert article.url == "http://example.com/valid"
    assert article.text == "Valid Description"
    assert article.published_at.year == 2024
    assert article.published_at.month == 3
    assert article.published_at.day == 20
    assert article.popularity_score == 1500000


@pytest.mark.asyncio
async def test_transform_to_article_null_fields(explorer):
    """_transform_to_article: 必須フィールド欠落やnullのハンドリング."""
    # desc is None
    item = {
        "title": "Title",
        "url": "http://example.com",
        "desc": None,
        "hot": None,
        "time": "2024-03-20 10:00:00",
    }

    article = explorer._transform_to_article(item)

    assert article.text == ""  # Empty description handled
    assert article.popularity_score == 0


@pytest.mark.asyncio
async def test_transform_to_article_hot_parsing(explorer):
    """_transform_to_article: hotフィールドのパーステスト."""

    # integer string
    item_int = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "12345",
        "time": "2024-01-01 00:00:00",
    }
    article_int = explorer._transform_to_article(item_int)
    assert article_int.popularity_score == 12345

    # w suffix
    item_w = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "1.5万",
        "time": "2024-01-01 00:00:00",
    }
    article_w = explorer._transform_to_article(item_w)
    assert article_w.popularity_score == 15000

    # 億 suffix
    item_oku = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "1.2億",
        "time": "2024-01-01 00:00:00",
    }
    article_oku = explorer._transform_to_article(item_oku)
    assert article_oku.popularity_score == 120000000

    # invalid
    item_invalid = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "invalid",
        "time": "2024-01-01 00:00:00",
    }
    article_invalid = explorer._transform_to_article(item_invalid)
    assert article_invalid.popularity_score == 0


@pytest.mark.asyncio
async def test_transform_to_article_time_parsing(explorer):
    """_transform_to_article: timeフィールドのパーステスト."""

    # specific format YYYY-MM-DD HH:MM
    item_fmt = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "0",
        "time": "2024-12-31 23:59:00",
    }
    article_fmt = explorer._transform_to_article(item_fmt)
    assert article_fmt.published_at.year == 2024
    assert article_fmt.published_at.month == 12
    assert article_fmt.published_at.day == 31

    # timestamp (int/str)
    ts = 1704067200  # 2024-01-01 00:00:00 UTC
    item_ts = {"title": "T", "url": "U", "desc": "D", "hot": "0", "time": str(ts)}
    article_ts = explorer._transform_to_article(item_ts)
    assert article_ts.published_at.year == 2024

    # timestamp (ms epoch)
    ts_ms = 1704067200000  # 2024-01-01 00:00:00 UTC in milliseconds
    item_ts_ms = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "0",
        "time": str(ts_ms),
    }
    article_ts_ms = explorer._transform_to_article(item_ts_ms)
    assert article_ts_ms.published_at.year == 2024

    # invalid time -> fallback to current time (mock datetime.now if strict, but here just check it defaults)
    item_bad = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "0",
        "time": "invalid-time",
    }
    article_bad = explorer._transform_to_article(item_bad)
    assert isinstance(article_bad.published_at, datetime)

    # huge epoch should not crash and should fallback
    item_huge = {
        "title": "T",
        "url": "U",
        "desc": "D",
        "hot": "0",
        "time": "9999999999999999",
    }
    article_huge = explorer._transform_to_article(item_huge)
    assert isinstance(article_huge.published_at, datetime)


@pytest.mark.asyncio
async def test_collect_client_error(explorer, mock_trendradar_client):
    """collect: クライアントエラー時のハンドリング."""
    mock_trendradar_client.get_latest_news.side_effect = ValueError("API Error")

    # If exception handles internally -> Assert empty list or behavior
    # If exception raises -> Use pytest.raises
    with pytest.raises(ValueError):
        await explorer.collect(days=1, limit=5)
