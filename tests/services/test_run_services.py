import asyncio
import types
from datetime import date
from unittest.mock import MagicMock, AsyncMock

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
    runner.sync_services = {name: MagicMock() for name in service_names}
    runner.task_manager = None
    runner.running = False
    return runner


@pytest.mark.asyncio
async def test_run_all_invokes_each_service(monkeypatch):
    runner = _make_runner(["a", "b"])
    calls: list[tuple[str, object, int, list[int]]] = []

    # Given
    async def fake_run_sync(self, service_name, service, days, target_dates):
        calls.append((service_name, service, days, target_dates))

    async def fake_gather(*coros, task_names=None):
        # coros have already been awaited in run_all via gather_with_errors
        # But wait, gather_with_errors takes coroutines and runs them.
        # We need to execute them to trigger fake_run_sync
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

    # When
    await runner.run_all(days=3)

    # Then
    assert runner.running is False
    # target_dates should be sorted list [1,2] (Note: calling logic sorts it)
    assert calls == [
        ("a", runner.sync_services["a"], 3, [1, 2]),
        ("b", runner.sync_services["b"], 3, [1, 2]),
    ]
    assert close_called["flag"] is True


@pytest.mark.asyncio
async def test_run_service_single(monkeypatch):
    runner = _make_runner(["only"])
    calls: list[tuple[str, object, int, list[int]]] = []

    # Given
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

    # When
    await runner.run_service("only", days=2)

    # Then
    assert calls == [
        ("only", runner.sync_services["only"], 2, [1, 5]),
    ]


@pytest.mark.asyncio
async def test_run_service_unknown_raises():
    runner = _make_runner(["known"])

    with pytest.raises(ValueError):
        await runner.run_service("missing")


@pytest.mark.asyncio
async def test_run_sync_service_dispatch_logic():
    """Verify correct parameters are passed to service.collect based on service name"""

    # We test _run_sync_service directly

    # Setup mocks
    service_mock = AsyncMock()
    service_mock.collect.return_value = []

    runner = ServiceRunner.__new__(ServiceRunner)

    # --- Case 1: hacker_news ---
    # Expected: limit=15, target_dates=...
    dates = [date(2024, 1, 1)]
    await runner._run_sync_service(
        "hacker_news", service_mock, days=1, target_dates=dates
    )
    service_mock.collect.assert_awaited_with(limit=15, target_dates=dates)
    service_mock.collect.reset_mock()

    # --- Case 2: tech_news (or business_news) ---
    # Expected: days=..., limit=15, target_dates=...
    await runner._run_sync_service(
        "tech_news", service_mock, days=5, target_dates=dates
    )
    service_mock.collect.assert_awaited_with(days=5, limit=15, target_dates=dates)
    service_mock.collect.reset_mock()

    # --- Case 3: zenn (or qiita, note) ---
    # Expected: days=..., limit=15, target_dates=...
    await runner._run_sync_service("zenn", service_mock, days=3, target_dates=dates)
    service_mock.collect.assert_awaited_with(days=3, limit=15, target_dates=dates)
    service_mock.collect.reset_mock()

    # --- Case 4: reddit ---
    # Expected: limit=15, target_dates=...
    await runner._run_sync_service("reddit", service_mock, days=1, target_dates=dates)
    service_mock.collect.assert_awaited_with(limit=15, target_dates=dates)
    service_mock.collect.reset_mock()

    # --- Case 5: other (default) ---
    # Expected: target_dates=... (only)
    await runner._run_sync_service(
        "other_service", service_mock, days=1, target_dates=dates
    )
    service_mock.collect.assert_awaited_with(target_dates=dates)
    service_mock.collect.reset_mock()


@pytest.mark.asyncio
async def test_run_sync_service_handles_error(monkeypatch):
    """Verify exceptions are propagated/logged"""
    service_mock = AsyncMock()
    service_mock.collect.side_effect = Exception("Service Crash")

    runner = ServiceRunner.__new__(ServiceRunner)
    # The code uses global 'logger' from the module, not self.logger
    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.run_services.logger", mock_logger)

    # It should raise exception
    with pytest.raises(Exception) as excinfo:
        await runner._run_sync_service("fail_service", service_mock, days=1)

    assert "Service Crash" in str(excinfo.value)
    # verify logger.error was called
    assert mock_logger.error.called
    args, kwargs = mock_logger.error.call_args
    assert "fail_service failed" in args[0]


@pytest.mark.asyncio
async def test_run_continuous(monkeypatch):
    """Verify continuous execution loop"""
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.running = True

    # Mock run_all to eventually stop the runner
    run_count = 0

    async def fake_run_all(days):
        nonlocal run_count
        run_count += 1
        if run_count >= 2:
            runner.running = False

    monkeypatch.setattr(runner, "run_all", fake_run_all)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    # When
    await runner.run_continuous(interval_seconds=10, days=1)

    # Then
    assert run_count == 2
    assert asyncio.sleep.call_count == 2
    from unittest.mock import call

    asyncio.sleep.assert_has_calls([call(10), call(10)])
