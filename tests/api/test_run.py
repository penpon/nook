"""Tests for API run module.

This module tests the API server startup script:
- Argument parsing for host, port, and reload options
- uvicorn.run() calls with correct parameters
- Default values and command line argument handling
"""

from unittest.mock import MagicMock, patch
import pytest
import os
import sys

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nook.api.run import main


class TestMain:
    """Tests for main function in api/run.py."""

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_default_arguments(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: No command line arguments.
        When: main is called.
        Then: uvicorn.run is called with default parameters.
        """
        # Mock sys.argv to simulate no arguments
        with patch("sys.argv", ["run.py"]):
            main()

        # Verify uvicorn.run was called with correct defaults
        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="127.0.0.1", port=8000, reload=False
        )

        # Verify startup message
        mock_print.assert_any_call(
            "Nook APIサーバーを起動しています... http://127.0.0.1:8000"
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_custom_host(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Custom host argument.
        When: main is called.
        Then: uvicorn.run is called with custom host.
        """
        with patch("sys.argv", ["run.py", "--host", "127.0.0.1"]):
            main()

        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="127.0.0.1", port=8000, reload=False
        )

        mock_print.assert_any_call(
            "Nook APIサーバーを起動しています... http://127.0.0.1:8000"
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_custom_port(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Custom port argument.
        When: main is called.
        Then: uvicorn.run is called with custom port.
        """
        with patch("sys.argv", ["run.py", "--port", "9000"]):
            main()

        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="127.0.0.1", port=9000, reload=False
        )

        mock_print.assert_any_call(
            "Nook APIサーバーを起動しています... http://127.0.0.1:9000"
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_reload_enabled(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: --reload flag.
        When: main is called.
        Then: uvicorn.run is called with reload=True.
        """
        with patch("sys.argv", ["run.py", "--reload"]):
            main()

        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="127.0.0.1", port=8000, reload=True
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_all_arguments(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: All custom arguments.
        When: main is called.
        Then: uvicorn.run is called with all custom parameters.
        """
        with patch(
            "sys.argv",
            ["run.py", "--host", "192.168.1.100", "--port", "8080", "--reload"],
        ):
            main()

        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="192.168.1.100", port=8080, reload=True
        )

        mock_print.assert_any_call(
            "Nook APIサーバーを起動しています... http://192.168.1.100:8080"
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_port_as_string(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Port argument as string (should be converted to int).
        When: main is called.
        Then: uvicorn.run is called with port as int.
        """
        with patch("sys.argv", ["run.py", "--port", "3000"]):
            main()

        # Verify port was converted to int
        args, kwargs = mock_uvicorn_run.call_args
        assert kwargs["port"] == 3000
        assert isinstance(kwargs["port"], int)

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_argument_parser_description(
        self, mock_print, mock_uvicorn_run
    ) -> None:
        """
        Given: ArgumentParser is created.
        When: main is called.
        Then: Parser has correct description.
        """
        with patch("nook.api.run.ArgumentParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser_class.return_value = mock_parser
            mock_parser.parse_args.return_value = MagicMock(
                host="127.0.0.1", port=8000, reload=False
            )

            with patch("sys.argv", ["run.py"]):
                main()

            # Verify ArgumentParser was created with correct description
            mock_parser_class.assert_called_once_with(
                description="Nook APIサーバーを起動します"
            )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_help_argument(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: --help argument.
        When: main is called.
        Then: ArgumentParser help is shown.
        """
        mock_parser = MagicMock()
        mock_parser.parse_args.side_effect = SystemExit  # Help causes SystemExit

        with patch("nook.api.run.ArgumentParser", return_value=mock_parser):
            with patch("sys.argv", ["run.py", "--help"]):
                with pytest.raises(SystemExit):
                    main()

            mock_parser.add_argument.assert_called()

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_invalid_port(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Invalid port argument.
        When: main is called.
        Then: ArgumentParser raises error.
        """
        mock_parser = MagicMock()
        mock_parser.parse_args.side_effect = SystemExit

        with patch("nook.api.run.ArgumentParser", return_value=mock_parser):
            with patch("sys.argv", ["run.py", "--port", "invalid"]):
                with pytest.raises(SystemExit):
                    main()

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_negative_port(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Negative port argument.
        When: main is called.
        Then: ArgumentParser raises error.
        """
        mock_parser = MagicMock()
        mock_parser.parse_args.side_effect = SystemExit

        with patch("nook.api.run.ArgumentParser", return_value=mock_parser):
            with patch("sys.argv", ["run.py", "--port", "-1"]):
                with pytest.raises(SystemExit):
                    main()

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_uvicorn_exception(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: uvicorn.run raises an exception.
        When: main is called.
        Then: Exception is propagated.
        """
        mock_uvicorn_run.side_effect = Exception("Uvicorn error")

        with patch("sys.argv", ["run.py"]):
            with pytest.raises(Exception, match="Uvicorn error"):
                main()

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_app_module_path(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: main is called.
        When: uvicorn.run is called.
        Then: Correct app module path is used.
        """
        with patch("sys.argv", ["run.py"]):
            main()

        # Verify the app module path is correct
        args, kwargs = mock_uvicorn_run.call_args
        assert args[0] == "nook.api.main:app"

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_startup_message_format(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Custom host and port.
        When: main is called.
        Then: Startup message contains correct URL format.
        """
        with patch("sys.argv", ["run.py", "--host", "localhost", "--port", "5000"]):
            main()

        # Verify startup message format
        mock_print.assert_any_call(
            "Nook APIサーバーを起動しています... http://localhost:5000"
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_long_arguments(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Long form arguments.
        When: main is called.
        Then: Arguments are parsed correctly.
        """
        with patch("sys.argv", ["run.py", "--host", "127.0.0.1", "--port", "8080"]):
            main()

        mock_uvicorn_run.assert_called_once_with(
            "nook.api.main:app", host="127.0.0.1", port=8080, reload=False
        )

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_multiple_calls(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: main is called multiple times.
        When: Each call is made.
        Then: uvicorn.run is called each time with correct parameters.
        """
        with patch("sys.argv", ["run.py"]):
            main()
            main()

        # Verify uvicorn.run was called twice
        assert mock_uvicorn_run.call_count == 2

        # Both calls should have same parameters
        for call in mock_uvicorn_run.call_args_list:
            args, kwargs = call
            assert args[0] == "nook.api.main:app"
            assert kwargs["host"] == "127.0.0.1"
            assert kwargs["port"] == 8000
            assert kwargs["reload"] is False

    @patch("nook.api.run.uvicorn.run")
    @patch("builtins.print")
    def test_main_large_port_number(self, mock_print, mock_uvicorn_run) -> None:
        """
        Given: Large port number.
        When: main is called.
        Then: Port is handled correctly.
        """
        with patch("sys.argv", ["run.py", "--port", "65535"]):  # Maximum valid port
            main()

        args, kwargs = mock_uvicorn_run.call_args
        assert kwargs["port"] == 65535
