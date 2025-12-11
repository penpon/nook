from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.api.main import app  # noqa: E402
from nook.api.routers import content as content_module  # noqa: E402
from nook.core.storage import LocalStorage  # noqa: E402


def _make_client() -> TestClient:
    """Create a test client for content router tests."""

    return TestClient(app)


def _patch_storage_to_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalStorage:
    """Patch content router storage to use a temporary directory."""

    storage = LocalStorage(str(tmp_path))
    monkeypatch.setattr(content_module, "storage", storage)
    return storage


def test_get_content_invalid_source_returns_404() -> None:
    """Test content endpoint returns 404 for unknown source."""

    # Given
    client = _make_client()

    # When
    resp = client.get("/api/content/unknown-source")

    # Then
    assert resp.status_code == 404


def test_get_content_invalid_date_returns_400() -> None:
    """Test hacker-news endpoint returns 400 for invalid date format."""

    # Given
    client = _make_client()

    # When
    resp = client.get("/api/content/hacker-news?date=invalid-date")

    # Then
    assert resp.status_code == 400


def test_get_content_hacker_news_returns_items_from_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test hacker-news endpoint loads stories from JSON storage."""

    # Given
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    date_str = "2024-01-01"
    datetime.strptime(date_str, "%Y-%m-%d")

    service_dir = storage.base_dir / "hacker_news"
    service_dir.mkdir(parents=True, exist_ok=True)
    stories: list[dict[str, Any]] = [
        {"title": "Top", "summary": "summary text", "score": 10, "url": "u1"},
        {"title": "Second", "text": "body", "score": 5, "url": "u2"},
    ]
    (service_dir / f"{date_str}.json").write_text(json.dumps(stories), encoding="utf-8")

    # When
    resp = client.get(f"/api/content/hacker-news?date={date_str}")

    # Then
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2

    first = data["items"][0]
    assert first["source"] == "hacker-news"
    assert first["title"] == "Top"
    assert "スコア" in first["content"]


def test_get_content_arxiv_converts_paper_summary_titles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test arxiv endpoint converts paper summary titles to emoji format."""

    # Given
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    date_str = "2024-01-01"
    service_dir = storage.base_dir / "arxiv_summarizer"
    service_dir.mkdir(parents=True, exist_ok=True)
    raw = "1. 既存研究では何ができなかったのか\n\n本文..."
    (service_dir / f"{date_str}.md").write_text(raw, encoding="utf-8")

    # When
    resp = client.get(f"/api/content/arxiv?date={date_str}")

    # Then
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert "🔍 研究背景と課題" in item["content"]
    assert item["title"].startswith("arxiv - ")


def test_get_content_all_aggregates_multiple_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test all endpoint aggregates from hacker-news and github sources."""

    # Given
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    date_str = "2024-01-01"

    hn_dir = storage.base_dir / "hacker_news"
    hn_dir.mkdir(parents=True, exist_ok=True)
    hn_stories = [{"title": "Top", "summary": "sum", "score": 10, "url": "u1"}]
    (hn_dir / f"{date_str}.json").write_text(json.dumps(hn_stories), encoding="utf-8")

    gh_dir = storage.base_dir / "github_trending"
    gh_dir.mkdir(parents=True, exist_ok=True)
    (gh_dir / f"{date_str}.md").write_text("GitHub content", encoding="utf-8")

    # Add Arxiv for coverage in "all" loop
    arxiv_dir = storage.base_dir / "arxiv_summarizer"
    arxiv_dir.mkdir(parents=True, exist_ok=True)
    (arxiv_dir / f"{date_str}.md").write_text("Arxiv content", encoding="utf-8")

    # When
    resp = client.get(f"/api/content/all?date={date_str}")

    # Then
    assert resp.status_code == 200
    data = resp.json()

    sources = {item["source"] for item in data["items"]}
    assert "hacker-news" in sources
    assert "github" in sources
    assert "arxiv" in sources


def test_get_content_explicit_date_empty_returns_empty_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test requesting a specific date with no content returns empty list, not 404."""
    client = _make_client()
    _patch_storage_to_tmp(tmp_path, monkeypatch)

    # Request future date with no data
    resp = client.get("/api/content/hacker-news?date=2099-01-01")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


def test_get_content_response_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test response headers for cache control."""
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    # Need data to return 200 OK
    date_str = "2024-01-01"
    service_dir = storage.base_dir / "hacker_news"
    service_dir.mkdir(parents=True, exist_ok=True)
    stories = [{"title": "T", "score": 1, "url": "u"}]
    (service_dir / f"{date_str}.json").write_text(json.dumps(stories), encoding="utf-8")

    resp = client.get(f"/api/content/hacker-news?date={date_str}")
    assert resp.status_code == 200
    assert (
        resp.headers["Cache-Control"]
        == "no-store, no-cache, must-revalidate, max-age=0"
    )
    assert resp.headers["Pragma"] == "no-cache"
    assert resp.headers["Expires"] == "0"


def test_get_content_fallback_to_latest_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fallback to latest available date when no date provided."""
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    # Prepare data for an old date
    old_date = "2023-01-01"
    service_dir = storage.base_dir / "hacker_news"
    service_dir.mkdir(parents=True, exist_ok=True)
    # Create dummy .md because storage.list_dates only checks for .md files
    (service_dir / f"{old_date}.md").write_text("", encoding="utf-8")

    # We need valid data to return something
    stories = [{"title": "Old", "summary": "sum", "score": 1, "url": "u"}]
    (service_dir / f"{old_date}.json").write_text(json.dumps(stories), encoding="utf-8")

    # Request without date (triggers fallback logic)
    resp = client.get("/api/content/hacker-news")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Old"


def test_get_content_github_empty_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GitHub source items result in an empty title field after aggregation logic."""
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    date_str = "2024-01-01"
    service_dir = storage.base_dir / "github_trending"
    service_dir.mkdir(parents=True, exist_ok=True)
    (service_dir / f"{date_str}.md").write_text("content", encoding="utf-8")

    resp = client.get(f"/api/content/github?date={date_str}")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    # In content.py: title = "" if source == "github" else ...
    assert item["title"] == ""


def test_get_content_hacker_news_text_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test hacker news uses text preview if summary is missing."""
    client = _make_client()
    storage = _patch_storage_to_tmp(tmp_path, monkeypatch)

    date_str = "2024-01-01"
    service_dir = storage.base_dir / "hacker_news"
    service_dir.mkdir(parents=True, exist_ok=True)

    long_text = "a" * 1200
    stories = [
        {"title": "No Sum", "text": long_text, "score": 10, "url": "u"},
    ]
    (service_dir / f"{date_str}.json").write_text(json.dumps(stories), encoding="utf-8")

    resp = client.get(f"/api/content/hacker-news?date={date_str}")
    item = resp.json()["items"][0]
    # Check truncation
    assert len(item["content"]) < 1200
    assert "..." in item["content"]
    assert "スコア: 10" in item["content"]


def test_get_content_no_content_raises_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 404 raised when absolutely no content available."""
    client = _make_client()
    _patch_storage_to_tmp(tmp_path, monkeypatch)
    # No files created

    resp = client.get("/api/content/hacker-news")
    assert resp.status_code == 404
    assert "No content available" in resp.json()["detail"]
