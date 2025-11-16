"""nook/api/models/schemas.py のテスト"""

import pytest
from pydantic import ValidationError

from nook.api.models.schemas import (
    ContentItem,
    ContentRequest,
    ContentResponse,
    WeatherResponse,
)


@pytest.mark.unit
class TestContentRequest:
    """ContentRequestのテスト"""

    def test_valid_content_request_with_date(self):
        """有効な日付付きリクエストの作成"""
        request = ContentRequest(date="2024-01-15")
        assert request.date == "2024-01-15"

    def test_valid_content_request_without_date(self):
        """日付なしリクエストの作成（Noneがデフォルト）"""
        request = ContentRequest()
        assert request.date is None

    def test_content_request_with_none_date(self):
        """date=Noneを明示的に指定"""
        request = ContentRequest(date=None)
        assert request.date is None


@pytest.mark.unit
class TestContentItem:
    """ContentItemのテスト"""

    def test_valid_content_item_with_all_fields(self):
        """全フィールドを含む有効なContentItem"""
        item = ContentItem(
            title="Test Title",
            content="Test content body",
            url="https://example.com",
            source="reddit",
        )
        assert item.title == "Test Title"
        assert item.content == "Test content body"
        assert item.url == "https://example.com"
        assert item.source == "reddit"

    def test_valid_content_item_without_url(self):
        """URL なしのContentItem"""
        item = ContentItem(
            title="Test Title", content="Test content", url=None, source="hackernews"
        )
        assert item.title == "Test Title"
        assert item.url is None

    def test_content_item_missing_required_field(self):
        """必須フィールド欠落時にバリデーションエラー"""
        with pytest.raises(ValidationError) as exc_info:
            ContentItem(title="Test", content="Content")  # sourceが欠落

        assert "source" in str(exc_info.value)

    def test_content_item_various_sources(self):
        """様々なソースタイプの受け入れ"""
        sources = [
            "reddit",
            "hackernews",
            "github",
            "techfeed",
            "paper",
            "zenn",
            "qiita",
        ]
        for source in sources:
            item = ContentItem(title="Title", content="Content", url=None, source=source)
            assert item.source == source


@pytest.mark.unit
class TestContentResponse:
    """ContentResponseのテスト"""

    def test_valid_content_response_with_items(self):
        """アイテムを含む有効なContentResponse"""
        items = [
            ContentItem(title="Item 1", content="Content 1", url=None, source="reddit"),
            ContentItem(title="Item 2", content="Content 2", url=None, source="github"),
        ]
        response = ContentResponse(items=items)
        assert len(response.items) == 2
        assert response.items[0].title == "Item 1"

    def test_valid_content_response_empty_items(self):
        """空のアイテムリスト"""
        response = ContentResponse(items=[])
        assert response.items == []
        assert isinstance(response.items, list)

    def test_content_response_missing_items_field(self):
        """itemsフィールド欠落時にバリデーションエラー"""
        with pytest.raises(ValidationError) as exc_info:
            ContentResponse()

        assert "items" in str(exc_info.value)


@pytest.mark.unit
class TestWeatherResponse:
    """WeatherResponseのテスト"""

    def test_valid_weather_response(self):
        """有効な天気レスポンス"""
        weather = WeatherResponse(temperature=25.5, icon="01d")
        assert weather.temperature == 25.5
        assert weather.icon == "01d"

    def test_weather_response_negative_temperature(self):
        """負の気温も許可"""
        weather = WeatherResponse(temperature=-10.0, icon="13d")
        assert weather.temperature == -10.0

    def test_weather_response_zero_temperature(self):
        """0度の気温"""
        weather = WeatherResponse(temperature=0.0, icon="50d")
        assert weather.temperature == 0.0

    def test_weather_response_missing_temperature(self):
        """temperature欠落時にバリデーションエラー"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherResponse(icon="01d")

        assert "temperature" in str(exc_info.value)

    def test_weather_response_missing_icon(self):
        """icon欠落時にバリデーションエラー"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherResponse(temperature=25.0)

        assert "icon" in str(exc_info.value)

    def test_weather_response_invalid_temperature_type(self):
        """無効な型のtemperature"""
        with pytest.raises(ValidationError):
            WeatherResponse(temperature="hot", icon="01d")
