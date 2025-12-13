import asyncio
import types
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from nook.services.runner.run_services import ServiceRunner


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
        "nook.services.runner.run_services.gather_with_errors",
        fake_gather,
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.target_dates_set",
        fake_target_dates_set,
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.close_http_client",
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
        "nook.services.runner.run_services.target_dates_set",
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

    # --- Case 5: trendradar-zhihu ---
    # Expected: All dates are passed (Validation delegated to ZhihuExplorer)
    multi_dates = [date(2024, 1, 2), date(2024, 1, 1)]
    await runner._run_sync_service(
        "trendradar-zhihu", service_mock, days=2, target_dates=multi_dates
    )
    service_mock.collect.assert_awaited_with(target_dates=sorted(multi_dates))
    service_mock.collect.reset_mock()

    # --- Case 6: other (default) ---
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
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)

    # It should raise exception
    with pytest.raises(Exception) as excinfo:
        await runner._run_sync_service("fail_service", service_mock, days=1)

    assert "Service Crash" in str(excinfo.value)
    # verify logger.error was called
    assert mock_logger.error.called
    args, kwargs = mock_logger.error.call_args
    assert "Error executing fail_service" in args[0]


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


# --- Additional tests for coverage improvement ---


def test_service_runner_init_loads_service_classes():
    """Test that ServiceRunner.__init__ properly imports all service classes."""
    # This test actually creates a real ServiceRunner to cover lines 31-62
    runner = ServiceRunner()

    # Verify all service classes are loaded
    expected_services = [
        "github_trending",
        "hacker_news",
        "reddit",
        "zenn",
        "qiita",
        "note",
        "tech_news",
        "business_news",
        "arxiv",
        "4chan",
        "5chan",
        "trendradar-zhihu",
    ]
    for service in expected_services:
        assert service in runner.service_classes

    # Verify task_manager is created
    assert runner.task_manager is not None
    assert runner.running is False


@pytest.mark.asyncio
async def test__run_sync_service_multiple_dates_display(monkeypatch):
    """Test _run_sync_service (private method) displays date range when multiple dates (lines 84-86)."""
    service_mock = AsyncMock()
    service_mock.collect.return_value = []

    runner = ServiceRunner.__new__(ServiceRunner)
    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)

    # Multiple dates to trigger lines 84-86
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]

    await runner._run_sync_service(
        "test_service", service_mock, days=3, target_dates=dates
    )

    # Check that logger.info was called with date range info
    calls = [str(c) for c in mock_logger.info.call_args_list]
    date_range_logged = any("対象期間" in str(c) and "3日間" in str(c) for c in calls)
    assert date_range_logged, f"Expected date range log, got: {calls}"


@pytest.mark.asyncio
async def test_run_sync_service_with_saved_files(monkeypatch):
    """Test _run_sync_service displays file summary when files are saved (lines 126-133)."""
    service_mock = AsyncMock()
    # Return saved files to trigger lines 126-133
    service_mock.collect.return_value = [
        ("/path/to/file1.json", "/path/to/file1.md"),
        ("/path/to/file2.json", "/path/to/file2.md"),
    ]

    runner = ServiceRunner.__new__(ServiceRunner)
    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)

    dates = [date(2024, 1, 1)]
    await runner._run_sync_service(
        "test_service", service_mock, days=1, target_dates=dates
    )

    # Check that logger.info was called with file paths
    calls = [str(c) for c in mock_logger.info.call_args_list]
    file_logged = any("/path/to/file1.json" in str(c) for c in calls)
    assert file_logged, f"Expected file path log, got: {calls}"


@pytest.mark.asyncio
async def test_run_all_lazy_loading(monkeypatch):
    """Test that run_all lazy loads services (line 151)."""
    # Create a runner with mocked service_classes (avoiding real imports)
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.service_classes = {"svc_a": MagicMock, "svc_b": MagicMock}
    runner.sync_services = {}  # Empty to trigger lazy loading
    runner.task_manager = None
    runner.running = False

    # Mock the _run_sync_service to avoid actual service execution
    async def fake_run_sync(self, service_name, service, days, target_dates):
        pass

    async def fake_gather(*coros, task_names=None):
        await asyncio.gather(*coros)
        return [DummyTaskResult(name, True) for name in (task_names or [])]

    async def fake_close_http_client():
        pass

    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.gather_with_errors", fake_gather
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.close_http_client", fake_close_http_client
    )

    await runner.run_all(days=1)

    # After run_all, sync_services should be populated (lazy loading occurred)
    assert len(runner.sync_services) == len(runner.service_classes)


@pytest.mark.asyncio
async def test_run_all_with_failed_services(monkeypatch):
    """Test run_all logs errors for failed services (lines 188-195)."""
    runner = _make_runner(["success_svc", "fail_svc"])

    async def fake_run_sync(self, service_name, service, days, target_dates):
        if service_name == "fail_svc":
            raise ValueError("Service failed!")

    async def fake_gather(*coros, task_names=None):
        results = []
        for i, coro in enumerate(coros):
            name = task_names[i] if task_names else str(i)
            try:
                await coro
                results.append(DummyTaskResult(name, True))
            except Exception as e:
                results.append(DummyTaskResult(name, False, e))
        return results

    async def fake_close_http_client():
        pass

    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)
    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.gather_with_errors", fake_gather
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.close_http_client", fake_close_http_client
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.target_dates_set", lambda days: {1}
    )

    await runner.run_all(days=1)

    # Check that error was logged for failed service
    error_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("fail_svc" in str(c) for c in error_calls)


@pytest.mark.asyncio
async def test_run_service_lazy_loading(monkeypatch):
    """Test run_service lazy loads the service (line 208)."""
    # Create a runner without real imports
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.service_classes = {"github_trending": MagicMock}
    runner.sync_services = {}  # Empty to trigger lazy loading
    runner.task_manager = None
    runner.running = False

    async def fake_run_sync(self, service_name, service, days, target_dates):
        pass

    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )

    await runner.run_service("github_trending", days=1)

    # The service should be lazily loaded
    assert "github_trending" in runner.sync_services


@pytest.mark.asyncio
async def test_run_service_error_handling(monkeypatch):
    """Test run_service error handling (lines 223-225)."""
    # Create a runner without real imports
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.service_classes = {"github_trending": MagicMock}
    runner.sync_services = {}
    runner.task_manager = None
    runner.running = False

    async def fake_run_sync(self, service_name, service, days, target_dates):
        raise RuntimeError("Test error")

    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)
    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )

    with pytest.raises(RuntimeError):
        await runner.run_service("github_trending", days=1)

    # Check that error was logged
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_run_continuous_error_handling(monkeypatch):
    """Test run_continuous continues after errors (lines 236-237)."""
    runner = ServiceRunner.__new__(ServiceRunner)
    runner.running = True

    run_count = [0]

    async def fake_run_all(days):
        run_count[0] += 1
        if run_count[0] == 1:
            raise ValueError("First run failed!")
        elif run_count[0] >= 3:
            runner.running = False

    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)
    monkeypatch.setattr(runner, "run_all", fake_run_all)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await runner.run_continuous(interval_seconds=1, days=1)

    # Should have run 3 times (first failed, second succeeded, third stopped)
    assert run_count[0] == 3
    # Error should have been logged
    error_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("First run failed" in str(c) for c in error_calls)


def test_stop_method():
    """Test stop method (lines 245-246)."""
    runner = ServiceRunner()
    runner.running = True

    runner.stop()

    assert runner.running is False


def test_run_service_sync_success(monkeypatch, capsys):
    """Test run_service_sync successfully executes a service."""
    from nook.services.runner.run_services import run_service_sync

    # Mock the service class
    mock_service_class = MagicMock()
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance

    # Patch ServiceRunner to use our mock service
    def mock_init(self):
        self.service_classes = {"test_service": mock_service_class}
        self.sync_services = {}
        self.task_manager = None
        self.running = False

    monkeypatch.setattr(ServiceRunner, "__init__", mock_init)

    run_service_sync("test_service")

    captured = capsys.readouterr()
    assert "test_serviceを実行しています" in captured.out
    assert "完了しました" in captured.out
    mock_service_instance.run.assert_called_once()


def test_run_service_sync_with_error(monkeypatch, capsys):
    """Test run_service_sync error handling (lines 257-258)."""
    from nook.services.runner.run_services import run_service_sync

    # Mock the service class to raise an error
    mock_service_class = MagicMock()
    mock_service_instance = MagicMock()
    mock_service_instance.run.side_effect = RuntimeError("Service crashed")
    mock_service_class.return_value = mock_service_instance

    # Patch ServiceRunner to use our mock service
    def mock_init(self):
        self.service_classes = {"crash_service": mock_service_class}
        self.sync_services = {}
        self.task_manager = None
        self.running = False

    monkeypatch.setattr(ServiceRunner, "__init__", mock_init)

    run_service_sync("crash_service")

    captured = capsys.readouterr()
    assert "エラーが発生しました" in captured.out


def test_run_service_sync_not_found(capsys):
    """Test run_service_sync with unknown service name."""
    from nook.services.runner.run_services import run_service_sync

    run_service_sync("unknown_service")

    captured = capsys.readouterr()
    assert "見つかりません" in captured.out


def test_backward_compat_functions(monkeypatch, capsys):
    """Test backward compatibility functions (lines 329-374)."""
    from nook.services.runner import run_services

    # Mock run_service_sync
    called_services = []

    def mock_run_service_sync(service_name):
        called_services.append(service_name)

    monkeypatch.setattr(run_services, "run_service_sync", mock_run_service_sync)

    # Test each backward compat function
    run_services.run_github_trending()
    run_services.run_hacker_news()
    run_services.run_reddit_explorer()
    run_services.run_zenn_explorer()
    run_services.run_qiita_explorer()
    run_services.run_note_explorer()
    run_services.run_tech_feed()
    run_services.run_business_feed()
    run_services.run_arxiv_summarizer()
    run_services.run_fourchan_explorer()
    run_services.run_fivechan_explorer()

    assert called_services == [
        "github_trending",
        "hacker_news",
        "reddit",
        "zenn",
        "qiita",
        "note",
        "tech_news",
        "business_news",
        "arxiv",
        "4chan",
        "5chan",
    ]


def test_run_all_services(monkeypatch):
    """Test run_all_services backward compat function (line 374)."""
    from nook.services.runner import run_services

    run_all_called = {"flag": False}

    async def mock_run_all(self):
        run_all_called["flag"] = True

    # Mock ServiceRunner.run_all
    monkeypatch.setattr(ServiceRunner, "run_all", mock_run_all)

    run_services.run_all_services()

    assert run_all_called["flag"] is True


@pytest.mark.asyncio
async def test_run_all_exception_handling(monkeypatch):
    """Test run_all exception handling (lines 193-195)."""
    runner = _make_runner(["svc"])

    async def fake_run_sync(self, service_name, service, days, target_dates):
        pass

    async def fake_gather(*coros, task_names=None):
        # Close coroutines to avoid "coroutine was never awaited" warning
        for coro in coros:
            coro.close()
        raise RuntimeError("Gather failed!")

    async def fake_close_http_client():
        pass

    mock_logger = MagicMock()
    monkeypatch.setattr("nook.services.runner.run_services.logger", mock_logger)
    monkeypatch.setattr(
        runner,
        "_run_sync_service",
        types.MethodType(fake_run_sync, runner),
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.gather_with_errors", fake_gather
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.close_http_client", fake_close_http_client
    )
    monkeypatch.setattr(
        "nook.services.runner.run_services.target_dates_set", lambda days: {1}
    )

    with pytest.raises(RuntimeError, match="Gather failed"):
        await runner.run_all(days=1)

    # Verify error was logged
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_main_run_all(monkeypatch):
    """Test main function with default args (run all services)."""
    from nook.services.runner import run_services

    run_all_called = {"days": None}

    async def mock_run_all(self, days):
        run_all_called["days"] = days

    def mock_init(self):
        self.running = False

    def mock_stop(self):
        pass

    # Mock argparse to return default args
    mock_args = MagicMock()
    mock_args.service = "all"
    mock_args.continuous = False
    mock_args.interval = 3600
    mock_args.days = 2

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: mock_args)
    monkeypatch.setattr(ServiceRunner, "__init__", mock_init)
    monkeypatch.setattr(ServiceRunner, "run_all", mock_run_all)
    monkeypatch.setattr(ServiceRunner, "stop", mock_stop)

    await run_services.main()

    assert run_all_called["days"] == 2


@pytest.mark.asyncio
async def test_main_run_single_service(monkeypatch):
    """Test main function with single service."""
    from nook.services.runner import run_services

    run_service_called = {"service": None, "days": None}

    async def mock_run_service(self, service_name, days):
        run_service_called["service"] = service_name
        run_service_called["days"] = days

    def mock_init(self):
        self.running = False

    mock_args = MagicMock()
    mock_args.service = "github_trending"
    mock_args.continuous = False
    mock_args.interval = 3600
    mock_args.days = 3

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: mock_args)
    monkeypatch.setattr(ServiceRunner, "__init__", mock_init)
    monkeypatch.setattr(ServiceRunner, "run_service", mock_run_service)

    await run_services.main()

    assert run_service_called["service"] == "github_trending"
    assert run_service_called["days"] == 3


@pytest.mark.asyncio
async def test_main_continuous_mode(monkeypatch):
    """Test main function in continuous mode."""
    from nook.services.runner import run_services

    run_continuous_called = {"interval": None, "days": None}

    async def mock_run_continuous(self, interval_seconds, days):
        run_continuous_called["interval"] = interval_seconds
        run_continuous_called["days"] = days

    def mock_init(self):
        self.running = False

    mock_args = MagicMock()
    mock_args.service = "all"
    mock_args.continuous = True
    mock_args.interval = 1800
    mock_args.days = 1

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", lambda self: mock_args)
    monkeypatch.setattr(ServiceRunner, "__init__", mock_init)
    monkeypatch.setattr(ServiceRunner, "run_continuous", mock_run_continuous)

    await run_services.main()

    assert run_continuous_called["interval"] == 1800
    assert run_continuous_called["days"] == 1
