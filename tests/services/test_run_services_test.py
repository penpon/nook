"""Tests for run_services_test module.

This module tests the ServiceRunnerTest class and its methods:
- ServiceRunnerTest initialization
- Service registration and management
- Individual service execution
- Async service execution with limits
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import os
import sys
import asyncio

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nook.services.run_services_test import ServiceRunnerTest


class TestServiceRunnerTest:
    """Tests for ServiceRunnerTest class."""

    def test_init(self) -> None:
        """
        Given: No arguments.
        When: ServiceRunnerTest is instantiated.
        Then: All service classes are registered and attributes are set.
        """
        runner = ServiceRunnerTest()

        # Check that service classes are registered
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
        ]

        for service in expected_services:
            assert service in runner.service_classes
            assert callable(runner.service_classes[service])

        # Check initial state
        assert runner.sync_services == {}
        assert runner.task_manager is not None
        assert runner.running is False
        assert hasattr(runner.task_manager, "max_concurrent")
        assert runner.task_manager.max_concurrent == 5

    @patch("nook.services.run_services_test.GithubTrending")
    def test_run_sync_service_success(self, mock_github_class) -> None:
        """
        Given: A valid service name and mock service.
        When: _run_sync_service is called.
        Then: Service is created and collect is called with limit=1.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        runner._run_sync_service("github_trending")

        mock_github_class.assert_called_once()
        mock_service.collect.assert_called_once_with(limit=1)

    @patch("nook.services.run_services_test.GithubTrending")
    def test_run_sync_service_exception(self, mock_github_class) -> None:
        """
        Given: A service that raises an exception.
        When: _run_sync_service is called.
        Then: Exception is caught and service is not stored.
        """
        mock_service = MagicMock()
        mock_service.collect.side_effect = Exception("Test error")
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        runner._run_sync_service("github_trending")

        # Service should not be stored due to exception
        assert "github_trending" not in runner.sync_services

    @patch("nook.services.run_services_test.GithubTrending")
    def test_run_sync_service_caches_service(self, mock_github_class) -> None:
        """
        Given: A valid service.
        When: _run_sync_service is called twice.
        Then: Service is cached after first call.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()

        # First call should create the service
        runner._run_sync_service("github_trending")
        assert "github_trending" in runner.sync_services

        # Second call should use cached service
        runner._run_sync_service("github_trending")

        # Service class should only be instantiated once
        mock_github_class.assert_called_once()
        # collect should be called twice
        assert mock_service.collect.call_count == 2

    @patch("nook.services.run_services_test.GithubTrending")
    @patch("nook.services.run_services_test.AsyncTaskManager")
    def test_run_service_async_success(
        self, mock_task_manager_class, mock_github_class
    ) -> None:
        """
        Given: A valid service and mocked task manager.
        When: run_service is called.
        Then: Service is run asynchronously through task manager.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service
        mock_task_manager = MagicMock()
        mock_task_manager_class.return_value = mock_task_manager

        runner = ServiceRunnerTest()
        runner.run_service("github_trending")

        mock_task_manager.add_task.assert_called_once()
        # Verify the task function is correct
        args, kwargs = mock_task_manager.add_task.call_args
        assert callable(args[0])

    @patch("nook.services.run_services_test.GithubTrending")
    @patch("nook.services.run_services_test.AsyncTaskManager")
    def test_run_service_sync_fallback(
        self, mock_task_manager_class, mock_github_class
    ) -> None:
        """
        Given: Task manager raises an exception.
        When: run_service is called.
        Then: Service falls back to sync execution.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service
        mock_task_manager = MagicMock()
        mock_task_manager.add_task.side_effect = Exception("Task manager error")
        mock_task_manager_class.return_value = mock_task_manager

        runner = ServiceRunnerTest()

        with patch.object(runner, "_run_sync_service") as mock_sync:
            runner.run_service("github_trending")
            mock_sync.assert_called_once_with("github_trending")

    def test_run_service_invalid_name(self) -> None:
        """
        Given: Invalid service name.
        When: run_service is called.
        Then: ValueError is raised.
        """
        runner = ServiceRunnerTest()

        with pytest.raises(ValueError, match="Unknown service: invalid_service"):
            runner.run_service("invalid_service")

    @patch.multiple(
        "nook.services.run_services_test",
        GithubTrending=MagicMock(),
        HackerNewsRetriever=MagicMock(),
        RedditExplorer=MagicMock(),
        ZennExplorer=MagicMock(),
        QiitaExplorer=MagicMock(),
        NoteExplorer=MagicMock(),
        TechFeed=MagicMock(),
        BusinessFeed=MagicMock(),
        ArxivSummarizer=MagicMock(),
        FourChanExplorer=MagicMock(),
        FiveChanExplorer=MagicMock(),
    )
    @patch("nook.services.run_services_test.AsyncTaskManager")
    def test_run_all_services(self, mock_task_manager_class) -> None:
        """
        Given: All services mocked.
        When: _run_all_services is called.
        Then: All services are added to task manager.
        """
        mock_task_manager = MagicMock()
        mock_task_manager_class.return_value = mock_task_manager

        runner = ServiceRunnerTest()
        runner._run_all_services()

        # Should add all 11 services to task manager
        assert mock_task_manager.add_task.call_count == 11

    @patch("nook.services.run_services_test.GithubTrending")
    def test_get_service_instance_new(self, mock_github_class) -> None:
        """
        Given: Service not yet instantiated.
        When: _get_service_instance is called.
        Then: New service instance is created and returned.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        result = runner._get_service_instance("github_trending")

        assert result == mock_service
        mock_github_class.assert_called_once()

    @patch("nook.services.run_services_test.GithubTrending")
    def test_get_service_instance_cached(self, mock_github_class) -> None:
        """
        Given: Service already instantiated.
        When: _get_service_instance is called.
        Then: Cached instance is returned.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()

        # First call creates and caches
        instance1 = runner._get_service_instance("github_trending")
        assert "github_trending" in runner.sync_services

        # Second call returns cached instance
        instance2 = runner._get_service_instance("github_trending")

        assert instance1 is instance2
        assert instance1 is runner.sync_services["github_trending"]
        # Service class should only be instantiated once
        mock_github_class.assert_called_once()

    def test_get_service_instance_invalid(self) -> None:
        """
        Given: Invalid service name.
        When: _get_service_instance is called.
        Then: ValueError is raised.
        """
        runner = ServiceRunnerTest()

        with pytest.raises(ValueError, match="Unknown service: invalid"):
            runner._get_service_instance("invalid")

    @patch("nook.services.run_services_test.GithubTrending")
    @patch("asyncio.sleep", new_callable=MagicMock)
    def test_create_service_task_function(self, mock_sleep, mock_github_class) -> None:
        """
        Given: A service class.
        When: _create_service_task is called.
        Then: Async task function is returned.
        """
        mock_service = MagicMock()
        mock_service.collect = AsyncMock(return_value="test_result")
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        task_func = runner._create_service_task("github_trending")

        # Verify it's async
        assert asyncio.iscoroutinefunction(task_func)

        # Run the task
        result = asyncio.run(task_func())

        mock_service.collect.assert_called_once_with(limit=1)
        assert result == "test_result"

    @patch("nook.services.run_services_test.GithubTrending")
    @patch("asyncio.sleep", new_callable=MagicMock)
    def test_create_service_task_with_exception(
        self, mock_sleep, mock_github_class
    ) -> None:
        """
        Given: A service that raises an exception.
        When: The task function is executed.
        Then: Exception is handled gracefully.
        """
        mock_service = MagicMock()
        mock_service.collect = AsyncMock(side_effect=Exception("Service error"))
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        task_func = runner._create_service_task("github_trending")

        # Should not raise exception
        result = asyncio.run(task_func())

        # Result should be None due to exception
        assert result is None

    @patch("nook.services.run_services_test.GithubTrending")
    @patch("asyncio.sleep", new_callable=MagicMock)
    def test_create_service_task_with_delay(
        self, mock_sleep, mock_github_class
    ) -> None:
        """
        Given: A service with delay parameter.
        When: The task function is executed.
        Then: Sleep is called before execution.
        """
        mock_service = MagicMock()
        mock_service.collect = AsyncMock(return_value="test_result")
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()
        task_func = runner._create_service_task("github_trending", delay=2.0)

        asyncio.run(task_func())

        # Verify sleep was called with correct delay
        mock_sleep.assert_called_once_with(2.0)

    @patch.multiple(
        "nook.services.run_services_test",
        GithubTrending=MagicMock(),
        HackerNewsRetriever=MagicMock(),
    )
    @patch("nook.services.run_services_test.AsyncTaskManager")
    def test_run_selected_services(self, mock_task_manager_class) -> None:
        """
        Given: Selected services.
        When: run_selected_services is called.
        Then: Only selected services are added to task manager.
        """
        mock_task_manager = MagicMock()
        mock_task_manager_class.return_value = mock_task_manager

        runner = ServiceRunnerTest()
        runner.run_selected_services(["github_trending", "hacker_news"])

        # Should add only 2 services to task manager
        assert mock_task_manager.add_task.call_count == 2

    def test_list_available_services(self) -> None:
        """
        Given: ServiceRunnerTest instance.
        When: list_available_services is called.
        Then: List of available services is returned.
        """
        runner = ServiceRunnerTest()
        services = runner.list_available_services()

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
        ]

        assert set(services) == set(expected_services)
        assert len(services) == 11

    @patch("nook.services.run_services_test.GithubTrending")
    def test_clear_service_cache(self, mock_github_class) -> None:
        """
        Given: Cached service instances.
        When: clear_service_cache is called.
        Then: Cache is cleared.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()

        # Create cached service
        runner._get_service_instance("github_trending")
        assert "github_trending" in runner.sync_services

        # Clear cache
        runner.clear_service_cache()

        # Cache should be empty
        assert runner.sync_services == {}

    @patch("nook.services.run_services_test.GithubTrending")
    def test_get_service_status(self, mock_github_class) -> None:
        """
        Given: Service instances.
        When: get_service_status is called.
        Then: Status of all services is returned.
        """
        mock_service = MagicMock()
        mock_github_class.return_value = mock_service

        runner = ServiceRunnerTest()

        # Create one cached service
        runner._get_service_instance("github_trending")

        status = runner.get_service_status()

        # Should have status for all services
        assert len(status) == 11
        assert "github_trending" in status
        assert status["github_trending"]["cached"] is True
        assert status["reddit"]["cached"] is False
