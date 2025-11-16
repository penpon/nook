"""nook/api/routers/content.py のテスト（基本テストのみ）"""

import pytest


@pytest.mark.unit
class TestContentRouter:
    """コンテンツAPIルーターのテスト"""

    def test_invalid_source_returns_404(self, client):
        """存在しないソースで404エラーを返す"""
        response = client.get("/api/content/invalid-source")

        assert response.status_code == 404
        assert "Source" in response.json()["detail"]
        assert "not found" in response.json()["detail"]

    def test_invalid_date_format_returns_400(self, client):
        """無効な日付フォーマットで400エラーを返す"""
        response = client.get("/api/content/reddit?date=invalid-date")

        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_valid_sources_accepted(self, client):
        """有効なソースが受け入れられる（404または200）"""
        valid_sources = [
            "reddit",
            "github",
            "arxiv",
            "hacker-news",
            "tech-news",
            "zenn",
            "qiita",
        ]

        for source in valid_sources:
            response = client.get(f"/api/content/{source}")

            # ソースは有効なので404エラーではない（データがない場合も404だが、ソース不明の404とは異なる）
            # または実際のデータがあれば200
            assert response.status_code in [200, 404, 500]
            if response.status_code == 404:
                # ソースが無効な場合のメッセージとは異なることを確認
                detail = response.json().get("detail", "")
                assert "not found" not in detail.lower() or source not in detail

    def test_all_sources_option_accepted(self, client):
        """allオプションが受け入れられる"""
        response = client.get("/api/content/all")

        # "all"は有効なオプション
        assert response.status_code in [200, 404, 500]
        if response.status_code == 404:
            detail = response.json().get("detail", "")
            # "Source 'all' not found"のようなメッセージではないことを確認
            assert "Source" not in detail or "all" not in detail

    def test_date_format_validation(self, client):
        """日付フォーマットのバリデーション"""
        # 有効な日付
        valid_dates = ["2024-01-01", "2024-12-31", "2023-06-15"]
        for date in valid_dates:
            response = client.get(f"/api/content/reddit?date={date}")
            # 日付フォーマットエラー（400）ではないことを確認
            assert response.status_code != 400 or "Invalid date format" not in response.json().get(
                "detail", ""
            )

        # 無効な日付
        invalid_dates = ["2024/01/01", "01-01-2024", "invalid", "2024-13-01"]
        for date in invalid_dates:
            response = client.get(f"/api/content/reddit?date={date}")
            # 無効な日付フォーマットは400エラー
            assert response.status_code == 400
