import asyncio
import types

import pytest

from nook.services.run_services import ServiceRunner


class DummyTaskResult:
    def __init__(self, name: str, success: bool, error: Exception | None = None):
        self.name = name
        self.success = success
        self.error = error


def _make_runner(service_names: list[str]) -> ServiceRunner:
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.service_classes = {name: object for name in service_names}
    runner.sync_services = {name: object() for name in service_names}
    runner.task_manager = None
    runner.running = False
    return runner


@pytest.mark.asyncio
async def test_run_all_invokes_each_service(monkeypatch):
    runner = _make_runner(["a", "b"])
    calls: list[tuple[str, object, int, list[int]]] = []

    async def fake_run_sync(self, service_name, service, days, target_dates):
        calls.append((service_name, service, days, target_dates))

    async def fake_gather(*coros, task_names=None):
        # coros have already been awaited in run_all via gather_with_errors
        await asyncio.gather(*coros)
        return [DummyTaskResult(name, True) for name in (task_names or [])]

    close_called = {"flag": False}

    def fake_target_dates_set(days: int):
        return {2, 1}

    async def fake_close_http_client():
        close_called["flag"] = True

    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )
    monkeypatch.setattr(
        "nook.services.run_services.gather_with_errors",
        fake_gather,
    )
    monkeypatch.setattr(
        "nook.services.run_services.target_dates_set",
        fake_target_dates_set,
    )
    monkeypatch.setattr(
        "nook.services.run_services.close_http_client",
        fake_close_http_client,
    )

    await runner.run_all(days=3)

    assert runner.running is False
    # target_dates should be sorted list [1,2]
    assert calls == [
        ("a", runner.sync_services["a"], 3, [1, 2]),
        ("b", runner.sync_services["b"], 3, [1, 2]),
    ]
    assert close_called["flag"] is True


@pytest.mark.asyncio
async def test_run_service_single(monkeypatch):
    runner = _make_runner(["only"])
    calls: list[tuple[str, object, int, list[int]]] = []

    async def fake_run_sync(self, service_name, service, days, target_dates):
        calls.append((service_name, service, days, target_dates))

    def fake_target_dates_set(days: int):
        return {5, 1}

    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )
    monkeypatch.setattr(
        "nook.services.run_services.target_dates_set",
        fake_target_dates_set,
    )

    await runner.run_service("only", days=2)

    assert calls == [
        ("only", runner.sync_services["only"], 2, [1, 5]),
    ]


@pytest.mark.asyncio
async def test_run_service_unknown_raises():
    runner = _make_runner(["known"])

    with pytest.raises(ValueError):
        await runner.run_service("missing")
