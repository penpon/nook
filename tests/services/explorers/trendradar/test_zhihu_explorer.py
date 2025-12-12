"""Tests for ZhihuExplorer service.

This module tests the ZhihuExplorer class that retrieves hot topics
from Zhihu via the TrendRadar MCP server.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer


class TestZhihuExplorerInitialization:
    """ZhihuExplorerの初期化テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_explorer_initialization(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Default initialization parameters.
        When: ZhihuExplorer is instantiated.
        Then: The explorer has correct service name and TrendRadarClient.
        """
        assert explorer.service_name == "trendradar-zhihu"
        assert explorer.client is not None

    def test_explorer_with_custom_storage_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Given: Custom storage directory.
        When: ZhihuExplorer is instantiated.
        Then: The storage path is configured correctly.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir="custom_data")
        assert "custom_data" in str(explorer.storage.base_dir)


class TestZhihuExplorerTransform:
    """TrendRadarからArticleへの変換テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_transform_trendradar_to_article(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar news item dict.
        When: _transform_to_article is called.
        Then: An Article object is returned with correct attributes.
        """
        trendradar_item = {
            "title": "测试热门话题",
            "url": "https://www.zhihu.com/question/123456",
            "hot": 1500000,
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.title == "测试热门话题"
        assert article.url == "https://www.zhihu.com/question/123456"
        assert article.popularity_score == 1500000
        assert article.feed_name == "zhihu"
        assert article.category == "hot"

    def test_transform_handles_missing_hot(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item without hot field.
        When: _transform_to_article is called.
        Then: popularity_score defaults to 0.
        """
        trendradar_item = {
            "title": "话题没有热度",
            "url": "https://www.zhihu.com/question/789",
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.popularity_score == 0

    def test_transform_parses_published_at(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with timestamp.
        When: _transform_to_article is called.
        Then: published_at is parsed correctly.
        """
        # Test with ISO string
        item_iso = {
            "title": "Article",
            "url": "http://test",
            "published_at": "2023-01-01T12:00:00",
        }
        article_iso = explorer._transform_to_article(item_iso)
        assert article_iso.published_at.year == 2023
        assert article_iso.published_at.month == 1

        # Test with timestamp (epoch)
        item_epoch = {
            "title": "Article Epoch",
            "url": "http://test-epoch",
            "timestamp": 1672531200,  # 2023-01-01 00:00:00 UTC
        }
        article_epoch = explorer._transform_to_article(item_epoch)
        assert article_epoch.published_at.year == 2023

    def test_transform_parses_epoch_zero(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with epoch timestamp 0.
        When: _transform_to_article is called.
        Then: published_at is 1970-01-01T00:00:00Z.

        Note: epoch=0 は TrendRadar 側でデフォルト値として返されることがあり、
        パーサ回帰防止のためにこのエッジケースをテストしています。
        """
        item = {
            "title": "Epoch Zero Article",
            "url": "http://test-epoch-zero",
            "timestamp": 0,
        }
        article = explorer._transform_to_article(item)
        assert article.published_at.year == 1970
        assert article.published_at.month == 1
        assert article.published_at.day == 1

    def test_transform_handles_malformed_hot(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A TrendRadar item with malformed hot field.
        When: _transform_to_article is called.
        Then: popularity_score defaults to 0.0 without raising exception.
        """
        item = {
            "title": "Malformed Hot",
            "url": "http://test-malformed",
            "hot": "N/A",
        }
        article = explorer._transform_to_article(item)
        assert article.popularity_score == 0.0


class TestZhihuExplorerCollect:
    """ZhihuExplorer.collectメソッドのテスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer()
        # Mock storage to prevent disk I/O
        explorer.storage = AsyncMock()

        # Mock save methods to return dummy paths containing filename
        async def save_side_effect(data, filename):
            return f"mock/{filename}"

        explorer.storage.save.side_effect = save_side_effect
        return explorer

    @pytest.mark.asyncio
    async def test_collect_returns_file_paths(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Mock TrendRadarClient returning news items.
        When: collect is called.
        Then: Returns list of (json_path, md_path) tuples.
        """
        mock_news = [
            {"title": "热门话题1", "url": "https://zhihu.com/q/1", "hot": 1000000},
            {"title": "热门话题2", "url": "https://zhihu.com/q/2", "hot": 500000},
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock GPT client to avoid actual API calls
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                return_value=(
                    "このトピックは中国の技術コミュニティで活発に議論されており、"
                    "多くのエンジニアが関心を寄せています。"
                )
            )

            result = await explorer.collect(days=1, limit=10)

            mock_get.assert_called_once_with(platform="zhihu", limit=10)
            # Result should be non-empty list of 2-tuples
            assert result
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    @pytest.mark.asyncio
    async def test_collect_handles_null_fields_from_trendradar(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: TrendRadar returns items with null fields (e.g., desc/title/url).
        When: collect is called.
        Then: It does not crash while building the prompt and completes.
        """
        mock_news = [
            {
                "title": None,
                "url": None,
                "desc": None,
                "hot": 100,
            }
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            result = await explorer.collect(days=1, limit=10)

            assert isinstance(result, list)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_collect_propagates_errors(self, explorer: ZhihuExplorer) -> None:
        """
        Given: TrendRadarClient raises an exception.
        When: collect is called.
        Then: The exception is propagated.
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await explorer.collect(days=1, limit=10)

    @pytest.mark.asyncio
    async def test_collect_raises_error_for_multi_day_with_days_param(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: days param != 1 and target_dates is None.
        When: collect is called.
        Then: Raises NotImplementedError.
        """
        with pytest.raises(NotImplementedError, match="Multi-day collection"):
            await explorer.collect(days=2)

    @pytest.mark.asyncio
    async def test_collect_validates_limit(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Invalid limit values.
        When: collect is called.
        Then: Raises ValueError.
        """
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=0)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=101)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=-5)

    @pytest.mark.asyncio
    async def test_collect_rejects_bool_limit(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Boolean value for limit parameter.
        When: collect is called.
        Then: Raises ValueError (bool is subclass of int in Python).
        """
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=True)
        with pytest.raises(ValueError, match="limit must be an integer"):
            await explorer.collect(days=1, limit=False)

    @pytest.mark.asyncio
    async def test_collect_with_single_target_date(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Single date in target_dates parameter.
        When: collect is called.
        Then: Accepts the date and uses it for filename.
        """
        from datetime import date

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            target_date = date(2024, 1, 15)
            result = await explorer.collect(target_dates=[target_date])

            assert len(result) == 1
            json_path, md_path = result[0]
            assert "2024-01-15" in json_path
            assert "2024-01-15" in md_path

    @pytest.mark.asyncio
    async def test_collect_rejects_empty_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Empty target_dates list.
        When: collect is called.
        Then: Raises ValueError.
        """
        with pytest.raises(
            ValueError, match="target_dates must contain at least one date"
        ):
            await explorer.collect(target_dates=[])

    @pytest.mark.asyncio
    async def test_collect_with_multiple_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Multiple dates in target_dates parameter.
        When: collect is called.
        Then: Raises NotImplementedError.
        """
        from datetime import date

        target_dates = [date(2024, 1, 15), date(2024, 1, 16)]
        with pytest.raises(NotImplementedError, match="Multi-day collection"):
            await explorer.collect(target_dates=target_dates)

    @pytest.mark.asyncio
    async def test_collect_with_none_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: target_dates is None.
        When: collect is called.
        Then: Uses today's date for filename.
        """
        from datetime import datetime, timezone

        # UTC日付境界でのフレークを防ぐため、呼び出し前に期待値を確定
        expected_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            result = await explorer.collect(target_dates=None)

            assert len(result) == 1
            json_path, md_path = result[0]
            assert expected_date_str in json_path
            assert expected_date_str in md_path

    @pytest.mark.asyncio
    async def test_collect_returns_empty_for_no_news(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: TrendRadarClient returns empty list.
        When: collect is called.
        Then: Returns empty list.
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            result = await explorer.collect(days=1, limit=10)

            assert result == []

    @pytest.mark.asyncio
    async def test_collect_handles_gpt_error(self, explorer: ZhihuExplorer) -> None:
        """
        Given: GPT client raises exception during summarization.
        When: collect is called.
        Then: Article summary contains error message and collect completes.
        """
        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock gpt_client.generate_async to raise exception
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                side_effect=Exception("GPT Error")
            )

            # Patch _store_articles to capture articles without real I/O
            captured_articles = []

            async def capture_store(articles, date_str):
                captured_articles.extend(articles)
                # Return mock paths without calling real storage
                return [(f"mock/{date_str}.json", f"mock/{date_str}.md")]

            with patch.object(explorer, "_store_articles", side_effect=capture_store):
                result = await explorer.collect(days=1, limit=10)

            # Should complete and return file paths
            assert isinstance(result, list)
            # Verify error message is set in article summary (fixed message, no exception details)
            assert len(captured_articles) == 1
            assert (
                captured_articles[0].summary
                == ZhihuExplorer.ERROR_MSG_GENERATION_FAILED
            )
            # Ensure no exception details are leaked
            assert "GPT Error" not in captured_articles[0].summary


class TestZhihuExplorerRun:
    """ZhihuExplorer.runメソッドのテスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer()
        # Mock storage to prevent disk I/O (though run() mocks collect, it's safer)
        explorer.storage = AsyncMock()
        return explorer

    def test_run_calls_run_with_cleanup(self, explorer: ZhihuExplorer) -> None:
        """
        Given: A ZhihuExplorer instance.
        When: run is called.
        Then: _run_with_cleanup is invoked via asyncio.run.
        """
        with patch.object(
            explorer, "_run_with_cleanup", new_callable=AsyncMock
        ) as mock_cleanup:
            explorer.run(days=1, limit=20)

            mock_cleanup.assert_called_once_with(days=1, limit=20)

    @pytest.mark.asyncio
    async def test_run_with_cleanup_calls_collect_and_close(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: A ZhihuExplorer instance.
        When: _run_with_cleanup is called.
        Then: collect is called and client.close() is ensured.
        """
        with patch.object(explorer, "collect", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []
            with patch.object(
                explorer.client, "close", new_callable=AsyncMock
            ) as mock_close:
                await explorer._run_with_cleanup(days=1, limit=20)

                mock_collect.assert_called_once_with(days=1, limit=20)
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_base_service_cleanup_on_error(self, explorer: ZhihuExplorer) -> None:
        """
        Given: collect raises an exception.
        When: _run_with_cleanup is called.
        Then: close is still called.
        """
        with patch.object(explorer, "collect", side_effect=ValueError("Test Error")):
            with patch.object(
                explorer.client, "close", new_callable=AsyncMock
            ) as mock_close:
                with pytest.raises(ValueError):
                    await explorer._run_with_cleanup()
                mock_close.assert_called_once()


class TestZhihuExplorerContextManager:
    """ZhihuExplorerのコンテキストマネージャーメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, explorer: ZhihuExplorer) -> None:
        """
        Given: ZhihuExplorer used in async with statement.
        When: The block is entered and exited.
        Then: close() is called on exit.
        """
        with patch.object(
            explorer.client, "close", new_callable=AsyncMock
        ) as mock_close:
            async with explorer as e:
                assert e is explorer
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_error(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Exception occurs within async with block.
        When: The block exits.
        Then: close() is still called.
        """
        with patch.object(
            explorer.client, "close", new_callable=AsyncMock
        ) as mock_close:
            with pytest.raises(ValueError):
                async with explorer:
                    raise ValueError("Test Error")
            mock_close.assert_called_once()


class TestZhihuExplorerRenderMarkdown:
    """ZhihuExplorer._render_markdownメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_render_markdown_with_normal_records(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Normal records without special characters.
        When: _render_markdown is called.
        Then: Markdown is correctly generated.
        """
        records = [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "summary": "Test summary",
                "popularity_score": 1000,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "# 知乎ホットトピック (2024-01-15)" in result
        assert "[Test Title](https://example.com)" in result
        assert "**人気度**: 1,000" in result
        assert "**要約**: Test summary" in result

    def test_render_markdown_escapes_title_brackets(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Record with brackets in title.
        When: _render_markdown is called.
        Then: Brackets are escaped to prevent Markdown link breakage.
        """
        records = [
            {
                "title": "[Important] Test Topic",
                "url": "https://example.com",
                "summary": "Summary",
                "popularity_score": 500,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Brackets should be escaped
        assert "\\[Important\\]" in result

    def test_render_markdown_escapes_url_parentheses(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Record with parentheses in URL.
        When: _render_markdown is called.
        Then: Both opening and closing parentheses are escaped.
        """
        records = [
            {
                "title": "Test",
                "url": "https://example.com/path(with)parens",
                "summary": "Summary",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Both opening and closing parentheses should be escaped
        assert "path\\(with\\)parens" in result

    def test_render_markdown_escapes_summary_with_brackets(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Record with Markdown characters in summary.
        When: _render_markdown is called.
        Then: Summary is escaped to prevent rendering issues.
        """
        records = [
            {
                "title": "Test",
                "url": "https://example.com",
                "summary": "See [this link](url) for details",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Brackets in summary should be escaped
        assert "\\[this link\\]" in result

    def test_render_markdown_escapes_html_characters(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Record with HTML special characters.
        When: _render_markdown is called.
        Then: HTML characters are escaped.
        """
        records = [
            {
                "title": "Test <script>alert('xss')</script>",
                "url": "https://example.com",
                "summary": "<b>Bold</b> text",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # HTML should be escaped
        assert "&lt;script&gt;" in result
        assert "&lt;b&gt;" in result


class TestZhihuExplorerParsePopularityScore:
    """ZhihuExplorer._parse_popularity_scoreメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_parse_popularity_score_with_int(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Integer value.
        When: _parse_popularity_score is called.
        Then: Returns float of the value.
        """
        assert explorer._parse_popularity_score(1000) == 1000.0

    def test_parse_popularity_score_with_float(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Float value.
        When: _parse_popularity_score is called.
        Then: Returns the float as-is.
        """
        assert explorer._parse_popularity_score(1234.5) == 1234.5

    def test_parse_popularity_score_with_string_number(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: String representation of a number.
        When: _parse_popularity_score is called.
        Then: Returns float of the parsed value.
        """
        assert explorer._parse_popularity_score("1500") == 1500.0

    def test_parse_popularity_score_with_none(self, explorer: ZhihuExplorer) -> None:
        """
        Given: None value.
        When: _parse_popularity_score is called.
        Then: Returns 0.0.
        """
        assert explorer._parse_popularity_score(None) == 0.0

    def test_parse_popularity_score_with_invalid_string(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Non-numeric string.
        When: _parse_popularity_score is called.
        Then: Returns 0.0.
        """
        assert explorer._parse_popularity_score("N/A") == 0.0
        assert explorer._parse_popularity_score("invalid") == 0.0

    def test_parse_popularity_score_with_negative(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Negative number.
        When: _parse_popularity_score is called.
        Then: Returns the negative float (no validation).
        """
        assert explorer._parse_popularity_score(-100) == -100.0

    def test_parse_popularity_score_with_zero(self, explorer: ZhihuExplorer) -> None:
        """
        Given: Zero value.
        When: _parse_popularity_score is called.
        Then: Returns 0.0.
        """
        assert explorer._parse_popularity_score(0) == 0.0


class TestZhihuExplorerTargetDatesValidation:
    """target_datesとdaysパラメータのバリデーションテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """Create a ZhihuExplorer instance for testing."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir=str(tmp_path))
        explorer.storage = AsyncMock()
        return explorer

    @pytest.mark.asyncio
    async def test_collect_rejects_target_dates_with_days_not_one(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: target_dates provided and days != 1.
        When: collect is called.
        Then: Raises ValueError explaining the conflict.
        """
        from datetime import date

        with pytest.raises(ValueError, match="days parameter must be 1"):
            await explorer.collect(target_dates=[date(2024, 1, 15)], days=2)
