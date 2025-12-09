from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.storage import LocalStorage  # noqa: E402


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def test_save_and_load_markdown(tmp_path):
    storage = LocalStorage(str(tmp_path))
    date = datetime(2024, 11, 1)

    path = storage.save_markdown("content", "service", date=date)
    assert path.exists()

    loaded = storage.load_markdown("service", date=date)
    assert loaded == "content"


def test_list_dates_returns_sorted_desc(tmp_path):
    storage = LocalStorage(str(tmp_path))

    storage.save_markdown("a", "svc", date=datetime(2024, 11, 1))
    storage.save_markdown("b", "svc", date=datetime(2024, 10, 30))

    dates = storage.list_dates("svc")
    assert [d.date() for d in dates] == [
        datetime(2024, 11, 1).date(),
        datetime(2024, 10, 30).date(),
    ]


def test_async_save_load_exists_and_rename(tmp_path):
    storage = LocalStorage(str(tmp_path))

    async def main():
        await storage.save({"hello": "world"}, "data.json")
        assert await storage.exists("data.json") is True

        content = await storage.load("data.json")
        assert "hello" in content

        await storage.rename("data.json", "renamed.json")
        assert await storage.exists("data.json") is False
        assert await storage.exists("renamed.json") is True

    _run(main())


def test_load_returns_none_when_missing(tmp_path):
    storage = LocalStorage(str(tmp_path))

    async def main():
        assert await storage.load("nothing.json") is None

    _run(main())
