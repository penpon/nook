import json
from datetime import datetime
from pathlib import Path

import pytest

from nook.common.storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(str(tmp_path))


def test_init_creates_dir(tmp_path):
    sub = tmp_path / "sub"
    assert not sub.exists()
    LocalStorage(str(sub))
    assert sub.exists()


def test_save_markdown_defaults(storage):
    content = "md content"
    service = "myservice"
    path = storage.save_markdown(content, service)

    today_str = datetime.now().strftime("%Y-%m-%d")
    assert path.name == f"{today_str}.md"
    assert path.read_text(encoding="utf-8") == content


def test_load_markdown_defaults(storage):
    service = "myservice"
    content = "default date content"
    storage.save_markdown(content, service)
    loaded = storage.load_markdown(service)
    assert loaded == content


def test_load_markdown_missing(storage):
    assert storage.load_markdown("unknown_service") is None


def test_list_dates_missing_dir(storage):
    assert storage.list_dates("non_existent") == []


def test_list_dates_invalid_files(storage, tmp_path):
    service = "mixed_files"
    (tmp_path / service).mkdir()
    (tmp_path / service / "2025-01-01.md").touch()
    (tmp_path / service / "not_a_date.md").touch()
    (tmp_path / service / "junk.txt").touch()

    dates = storage.list_dates(service)
    assert len(dates) == 1
    assert dates[0] == datetime(2025, 1, 1)


@pytest.mark.asyncio
async def test_async_save_text(storage):
    await storage.save("simple text", "test.txt")
    path = Path(storage.base_dir) / "test.txt"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "simple text"


@pytest.mark.asyncio
async def test_async_save_json(storage):
    data = {"k": "v"}
    await storage.save(data, "test.json")
    path = Path(storage.base_dir) / "test.json"
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == data


@pytest.mark.asyncio
async def test_async_load_exists_rename(storage):
    data = {"val": 123}
    await storage.save(data, "a.json")

    assert await storage.exists("a.json")
    assert not await storage.exists("b.json")

    loaded = await storage.load("a.json")
    assert json.loads(loaded) == data

    await storage.rename("a.json", "b.json")
    assert not await storage.exists("a.json")
    assert await storage.exists("b.json")

    # Safe rename non-exists
    await storage.rename("phantom.json", "phantom2.json")


@pytest.mark.asyncio
async def test_load_missing(storage):
    assert await storage.load("missing.txt") is None


def test_load_json_methods(storage):
    service = "jsonsvc"
    data = {"key": "val"}

    test_date = datetime(2025, 1, 15)
    today_str = test_date.strftime("%Y-%m-%d")
    s_dir = Path(storage.base_dir) / service
    s_dir.mkdir()
    with open(s_dir / f"{today_str}.json", "w", encoding="utf-8") as f:
        json.dump(data, f)

    loaded = storage.load_json(service, date=test_date)
    assert loaded == data

    assert storage.load_json("unknown") is None
