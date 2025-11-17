"""nook/api/routers/content.py のテストカバレッジ向上のための包括的なテスト"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from nook.api.main import app

client = TestClient(app)


@pytest.mark.unit
class TestContentRouterComprehensive:
    """コンテンツAPIルーターの包括的なテスト"""

    # ===== 正常系テスト (8ケース) =====

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_single_source_success(self, mock_load_markdown, mock_load_json):
        """単一ソース（reddit）のコンテンツを正常に取得"""
        mock_load_markdown.return_value = "# Reddit Content\n\nTest content"
        mock_load_json.return_value = None

        response = client.get("/api/content/reddit?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["source"] == "reddit"
        assert "Reddit Content" in data["items"][0]["content"]

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_hacker_news_individual_stories(self, mock_load_markdown, mock_load_json):
        """Hacker Newsソース指定で個別記事をスコア降順で返す"""
        mock_stories = [
            {"title": "Story 1", "score": 100, "url": "http://example.com/1"},
            {"title": "Story 2", "score": 200, "url": "http://example.com/2"},
            {"title": "Story 3", "score": 150, "url": "http://example.com/3"},
        ]
        mock_load_json.return_value = mock_stories
        mock_load_markdown.return_value = None

        response = client.get("/api/content/hacker-news?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # スコア降順でソートされていることを確認
        assert data["items"][0]["title"] == "Story 2"  # score: 200
        assert data["items"][1]["title"] == "Story 3"  # score: 150
        assert data["items"][2]["title"] == "Story 1"  # score: 100

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_hacker_news_with_summary(self, mock_load_markdown, mock_load_json):
        """Hacker Newsで要約がある場合、要約が表示される"""
        mock_stories = [
            {
                "title": "Test Story",
                "score": 100,
                "url": "http://example.com",
                "summary": "This is a test summary",
            }
        ]
        mock_load_json.return_value = mock_stories
        mock_load_markdown.return_value = None

        response = client.get("/api/content/hacker-news?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        assert "要約" in data["items"][0]["content"]
        assert "This is a test summary" in data["items"][0]["content"]

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_hacker_news_long_text_truncated(self, mock_load_markdown, mock_load_json):
        """Hacker Newsで長い本文が1000文字で省略される"""
        long_text = "a" * 1500
        mock_stories = [
            {
                "title": "Long Story",
                "score": 50,
                "url": "http://example.com",
                "text": long_text,
            }
        ]
        mock_load_json.return_value = mock_stories
        mock_load_markdown.return_value = None

        response = client.get("/api/content/hacker-news?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        content = data["items"][0]["content"]
        # 1000文字 + "..." が含まれることを確認
        assert "..." in content
        # 本文が1003文字（1000 + "..."）以下であることを確認（スコア表示を除く）
        text_part = content.split("スコア:")[0].strip()
        assert len(text_part) <= 1003

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_arxiv_title_conversion(self, mock_load_markdown, mock_load_json):
        """ArXivソース指定でタイトルが変換される"""
        content_with_original_title = (
            "1. 既存研究では何ができなかったのか\n\n" "テスト内容\n\n" "8. この論文を140字以内で要約するとどうなりますか？\n\n" "要約テスト"
        )
        mock_load_markdown.return_value = content_with_original_title
        mock_load_json.return_value = None

        response = client.get("/api/content/arxiv?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        content = data["items"][0]["content"]
        # タイトルが変換されていることを確認
        assert "🔍 研究背景と課題" in content
        assert "📝 140字要約" in content
        assert "1. 既存研究では何ができなかったのか" not in content

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_with_explicit_date(self, mock_load_markdown, mock_load_json):
        """明示的な日付指定で正常にコンテンツを取得"""
        mock_load_markdown.return_value = "Test content for specific date"
        mock_load_json.return_value = None

        response = client.get("/api/content/zenn?date=2024-10-01")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "2024-10-01" in data["items"][0]["title"]

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_all_sources_success(self, mock_load_markdown, mock_load_json):
        """全ソースのコンテンツを正常に取得"""

        def mock_markdown_side_effect(service_name, date):
            return f"Content from {service_name}"

        mock_load_markdown.side_effect = mock_markdown_side_effect
        mock_load_json.return_value = None

        response = client.get("/api/content/all?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        # 全ソース（Hacker News以外）からデータが取得される
        assert len(data["items"]) > 0
        sources = {item["source"] for item in data["items"]}
        assert "reddit" in sources
        assert "github" in sources

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_all_sources_hacker_news_truncation(self, mock_load_markdown, mock_load_json):
        """全ソース取得時のHacker Newsで長いテキストが500文字で省略される"""
        long_text = "b" * 800
        mock_stories = [
            {
                "title": "Long Story in All",
                "score": 75,
                "url": "http://example.com",
                "text": long_text,
            }
        ]

        def json_side_effect(service_name, date):
            if service_name == "hacker_news":
                return mock_stories
            return None

        mock_load_json.side_effect = json_side_effect
        mock_load_markdown.return_value = None

        response = client.get("/api/content/all?date=2024-11-17")

        assert response.status_code == 200
        data = response.json()
        hn_items = [item for item in data["items"] if item["source"] == "hacker-news"]
        assert len(hn_items) == 1
        content = hn_items[0]["content"]
        # 500文字 + "..." が含まれることを確認
        assert "..." in content
        text_part = content.split("スコア:")[0].strip()
        assert len(text_part) <= 503  # 500 + "..."

    # ===== 異常系テスト (7ケース) =====

    def test_get_content_invalid_date_format(self):
        """無効な日付形式で400エラーを返す"""
        response = client.get("/api/content/reddit?date=invalid-date")

        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_get_content_invalid_source(self):
        """存在しないsource名で404エラーを返す"""
        response = client.get("/api/content/invalid-source?date=2024-11-17")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("nook.api.routers.content.storage.list_dates")
    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_no_data_found_explicit_date(
        self, mock_load_markdown, mock_load_json, mock_list_dates
    ):
        """データが存在しない日付（明示的指定）で200レスポンスと空配列を返す"""
        mock_load_markdown.return_value = None
        mock_load_json.return_value = None
        mock_list_dates.return_value = []

        response = client.get("/api/content/reddit?date=2024-01-01")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_storage_markdown_exception(self, mock_load_markdown, mock_load_json):
        """Storage.load_markdownが例外をスローで500エラーを返す"""
        mock_load_markdown.side_effect = Exception("Storage error")
        mock_load_json.return_value = None

        response = client.get("/api/content/reddit?date=2024-11-17")

        assert response.status_code == 500
        response_data = response.json()
        assert "error" in response_data
        assert response_data["error"]["type"] == "internal_error"
        assert "unexpected error" in response_data["error"]["message"].lower()

    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_storage_json_exception(self, mock_load_markdown, mock_load_json):
        """Storage.load_jsonが例外をスローで500エラーを返す"""
        mock_load_json.side_effect = Exception("JSON load error")
        mock_load_markdown.return_value = None

        response = client.get("/api/content/hacker-news?date=2024-11-17")

        assert response.status_code == 500
        response_data = response.json()
        assert "error" in response_data
        assert response_data["error"]["type"] == "internal_error"
        assert "unexpected error" in response_data["error"]["message"].lower()

    @patch("nook.api.routers.content.storage.list_dates")
    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_fallback_to_latest(self, mock_load_markdown, mock_load_json, mock_list_dates):
        """データがない場合に最新の日付にフォールバックする"""
        # 最初の呼び出し（今日の日付）ではデータなし
        # 2回目の呼び出し（最新日付）でデータあり
        call_count = {"count": 0}

        def markdown_side_effect(service_name, date):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return None  # 今日のデータなし
            return "Latest available content"  # 最新日付のデータ

        mock_load_markdown.side_effect = markdown_side_effect
        mock_load_json.return_value = None
        mock_list_dates.return_value = [datetime(2024, 11, 15)]

        response = client.get("/api/content/reddit")  # 日付指定なし

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "Latest available content" in data["items"][0]["content"]

    @patch("nook.api.routers.content.storage.list_dates")
    @patch("nook.api.routers.content.storage.load_json")
    @patch("nook.api.routers.content.storage.load_markdown")
    def test_get_content_no_available_dates(self, mock_load_markdown, mock_load_json, mock_list_dates):
        """利用可能な日付が全くない場合に404エラーを返す"""
        mock_load_markdown.return_value = None
        mock_load_json.return_value = None
        mock_list_dates.return_value = []

        response = client.get("/api/content/reddit")  # 日付指定なし

        assert response.status_code == 404
        assert "No content available" in response.json()["detail"]
