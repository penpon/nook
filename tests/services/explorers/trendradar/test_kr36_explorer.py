"""Kr36Explorerのテストモジュール."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.kr36_explorer import Kr36Explorer


@pytest.fixture
def mock_trendradar_client():
    with patch(
        "nook.services.explorers.trendradar.base.TrendRadarClient"
    ) as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value = client_instance
        yield client_instance


@pytest.fixture
def explorer(mock_trendradar_client):
    return Kr36Explorer(storage_dir="test_data")


@pytest.mark.asyncio
async def test_initialization(explorer):
    """初期化のテスト."""
    assert explorer.service_name == "trendradar-36kr"
    assert explorer.PLATFORM_NAME == "36kr"
    assert explorer.FEED_NAME == "36kr"
    assert explorer.MARKDOWN_HEADER == "36氪ホットトピック"


@pytest.mark.asyncio
async def test_get_summary_prompt(explorer):
    """プロンプト生成のテスト."""
    article = Article(
        feed_name="36kr",
        title="Test Title",
        url="http://example.com",
        text="Test Description",
        soup=None,
        published_at=datetime.now(timezone.utc),
    )

    prompt = explorer._get_summary_prompt(article)

    assert "36氪（36Kr）ホットトピック" in prompt
    assert "Test Title" in prompt
    assert "Test Description" in prompt
    assert "ビジネスニュースの概要" in prompt
    assert "3. 業界構造・競争環境" in prompt


@pytest.mark.asyncio
async def test_get_system_instruction(explorer):
    """システム指示取得のテスト."""
    instruction = explorer._get_system_instruction()

    assert "36氪" in instruction
    assert "36Kr" in instruction
    assert "ビジネスパーソンに向けて" in instruction
    assert "投資規模" in instruction


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
            "time": "2024-03-20 10:00",
        }
    ]

    # Mock GPT client logic which is initialized in BaseService
    # Since we can't easily mock the parent class attribute initialization in this test setup without more complex patching,
    # we'll focus on the parts specific to Kr36Explorer or rely on BaseService mocking if needed.
    # However, BaseService initializes gpt_client. We need to mock that if we want _summarize_article to succeed.

    # Mocking _summarize_article to avoid GPT calls and complexity
    with patch.object(
        explorer, "_summarize_article", new_callable=AsyncMock
    ) as mock_summarize:
        with patch.object(
            explorer, "_store_articles", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = [("path/to.json", "path/to.md")]

            result = await explorer.collect(days=1, limit=5)

            assert len(result) == 1
            mock_trendradar_client.get_latest_news.assert_called_once_with(
                platform="36kr", limit=5
            )
            mock_summarize.assert_called_once()
            mock_store.assert_called_once()
