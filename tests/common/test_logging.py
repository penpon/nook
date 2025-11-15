"""nook/common/logging.py のテスト"""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.logging import JSONFormatter, SimpleConsoleFormatter, setup_logger

# ================================================================================
# 1. SimpleConsoleFormatter のテスト
# ================================================================================


@pytest.mark.unit
def test_simple_console_formatter_normal_message():
    """
    Given: 通常のLogRecord
    When: formatを呼び出す
    Then: メッセージのみが返る
    """
    formatter = SimpleConsoleFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)
    assert result == "test message"


@pytest.mark.unit
def test_simple_console_formatter_empty_message():
    """
    Given: 空メッセージのLogRecord
    When: formatを呼び出す
    Then: 空文字列が返る
    """
    formatter = SimpleConsoleFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="",
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)
    assert result == ""


@pytest.mark.unit
def test_simple_console_formatter_long_message():
    """
    Given: 1000文字のメッセージ
    When: formatを呼び出す
    Then: 全文字列が返る
    """
    formatter = SimpleConsoleFormatter()
    long_msg = "x" * 1000
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=long_msg,
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)
    assert result == long_msg


# ================================================================================
# 2. JSONFormatter のテスト
# ================================================================================


@pytest.mark.unit
def test_json_formatter_basic_fields():
    """
    Given: 基本的なLogRecord
    When: formatを呼び出す
    Then: 必須フィールドを含むJSON文字列が返る
    """
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.module = "test_module"
    record.funcName = "test_function"

    result = formatter.format(record)
    log_obj = json.loads(result)

    assert "timestamp" in log_obj
    assert log_obj["level"] == "INFO"
    assert log_obj["logger"] == "test_logger"
    assert log_obj["message"] == "test message"
    assert log_obj["module"] == "test_module"
    assert log_obj["function"] == "test_function"
    assert log_obj["line"] == 42


@pytest.mark.unit
def test_json_formatter_with_exception():
    """
    Given: exc_info付きLogRecord
    When: formatを呼び出す
    Then: exceptionフィールドが含まれる
    """
    formatter = JSONFormatter()

    try:
        raise ValueError("test exception")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="error occurred",
        args=(),
        exc_info=exc_info,
    )
    record.module = "test"
    record.funcName = "test_func"

    result = formatter.format(record)
    log_obj = json.loads(result)

    assert "exception" in log_obj
    assert "ValueError" in log_obj["exception"]


@pytest.mark.unit
def test_json_formatter_with_custom_fields():
    """
    Given: extraパラメータ付きLogRecord
    When: formatを呼び出す
    Then: カスタムフィールドが含まれる
    """
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.module = "test"
    record.funcName = "test_func"
    # カスタムフィールドを追加
    record.custom_field = "custom_value"
    record.request_id = "12345"

    result = formatter.format(record)
    log_obj = json.loads(result)

    assert log_obj["custom_field"] == "custom_value"
    assert log_obj["request_id"] == "12345"


@pytest.mark.unit
def test_json_formatter_non_ascii_message():
    """
    Given: 日本語メッセージのLogRecord
    When: formatを呼び出す
    Then: ensure_ascii=FalseでUTF-8エンコードされる
    """
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="テストメッセージ",
        args=(),
        exc_info=None,
    )
    record.module = "test"
    record.funcName = "test_func"

    result = formatter.format(record)
    log_obj = json.loads(result)

    assert log_obj["message"] == "テストメッセージ"


@pytest.mark.unit
def test_json_formatter_excludes_standard_fields():
    """
    Given: LogRecord
    When: formatを呼び出す
    Then: 除外リストのフィールドは含まれない
    """
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.module = "test"
    record.funcName = "test_func"

    result = formatter.format(record)
    log_obj = json.loads(result)

    # 除外されるフィールド
    assert "created" not in log_obj
    assert "msecs" not in log_obj
    assert "relativeCreated" not in log_obj
    assert "thread" not in log_obj
    assert "processName" not in log_obj


# ================================================================================
# 3. setup_logger のテスト
# ================================================================================


@pytest.mark.unit
def test_setup_logger_default_settings():
    """
    Given: デフォルト設定
    When: setup_loggerを呼び出す
    Then: INFO、JSON、logs/test.logとなる
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir)

        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 2  # console + file


@pytest.mark.unit
def test_setup_logger_custom_level():
    """
    Given: level="DEBUG"
    When: setup_loggerを呼び出す
    Then: DEBUGレベルが設定される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", level="DEBUG", log_dir=tmpdir)
        assert logger.level == logging.DEBUG


@pytest.mark.unit
def test_setup_logger_custom_directory():
    """
    Given: log_dir="custom_logs"
    When: setup_loggerを呼び出す
    Then: custom_logs/test_logger.logが作成される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dir = Path(tmpdir) / "custom_logs"
        setup_logger("test_logger", log_dir=str(custom_dir))

        assert custom_dir.exists()
        assert (custom_dir / "test_logger.log").exists()


@pytest.mark.unit
def test_setup_logger_use_json_false():
    """
    Given: use_json=False
    When: setup_loggerを呼び出す
    Then: ファイルハンドラーが標準フォーマット
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir, use_json=False)

        file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
        assert len(file_handlers) == 1
        file_handler = file_handlers[0]
        assert not isinstance(file_handler.formatter, JSONFormatter)


@pytest.mark.unit
def test_setup_logger_use_json_true():
    """
    Given: use_json=True
    When: setup_loggerを呼び出す
    Then: ファイルハンドラーがJSONフォーマット
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir, use_json=True)

        file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
        assert len(file_handlers) == 1
        file_handler = file_handlers[0]
        assert isinstance(file_handler.formatter, JSONFormatter)


@pytest.mark.unit
def test_setup_logger_console_handler():
    """
    Given: 任意の設定
    When: setup_loggerを呼び出す
    Then: StreamHandlerが追加される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir)

        stream_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename")
        ]
        assert len(stream_handlers) == 1
        console_handler = stream_handlers[0]
        assert isinstance(console_handler.formatter, SimpleConsoleFormatter)


@pytest.mark.unit
def test_setup_logger_clears_existing_handlers():
    """
    Given: 既存ハンドラーあり
    When: setup_loggerを呼び出す
    Then: 既存ハンドラーが削除される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = logging.getLogger("test_logger_clear")
        logger.addHandler(logging.NullHandler())
        assert len(logger.handlers) == 1

        setup_logger("test_logger_clear", log_dir=tmpdir)
        # 新しいハンドラーのみ（console + file）
        assert len(logger.handlers) == 2


@pytest.mark.unit
def test_setup_logger_creates_directory():
    """
    Given: ディレクトリ不存在
    When: setup_loggerを呼び出す
    Then: ディレクトリが作成される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = Path(tmpdir) / "new_logs"
        assert not new_dir.exists()

        setup_logger("test_logger", log_dir=str(new_dir))

        assert new_dir.exists()


@pytest.mark.unit
def test_setup_logger_directory_already_exists():
    """
    Given: ディレクトリ既存
    When: setup_loggerを呼び出す
    Then: エラーなし
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # 既存ディレクトリ
        setup_logger("test_logger", log_dir=tmpdir)
        # 再度呼び出してもエラーなし
        setup_logger("test_logger2", log_dir=tmpdir)


@pytest.mark.unit
def test_setup_logger_invalid_level():
    """
    Given: level="INVALID"
    When: setup_loggerを呼び出す
    Then: AttributeErrorが発生
    """
    with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(AttributeError):
        setup_logger("test_logger", level="INVALID", log_dir=tmpdir)


@pytest.mark.unit
def test_setup_logger_all_levels():
    """
    Given: 各ログレベル
    When: setup_loggerを呼び出す
    Then: 全レベルが設定可能
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            logger = setup_logger(f"test_{level}", level=level, log_dir=tmpdir)
            assert logger.level == getattr(logging, level)


@pytest.mark.unit
def test_setup_logger_file_handler_rotation():
    """
    Given: デフォルト設定
    When: setup_loggerを呼び出す
    Then: RotatingFileHandlerでmaxBytes=10MB, backupCount=5
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir)

        file_handler = [h for h in logger.handlers if hasattr(h, "maxBytes")][0]
        assert file_handler.maxBytes == 10 * 1024 * 1024
        assert file_handler.backupCount == 5


@pytest.mark.unit
def test_setup_logger_file_handler_encoding():
    """
    Given: デフォルト設定
    When: setup_loggerを呼び出す
    Then: エンコーディングがutf-8
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logger("test_logger", log_dir=tmpdir)

        file_handler = [h for h in logger.handlers if hasattr(h, "encoding")][0]
        assert file_handler.encoding == "utf-8"


@pytest.mark.unit
def test_setup_logger_log_file_created():
    """
    Given: name="test", log_dir="logs"
    When: setup_loggerを呼び出す
    Then: logs/test.logが作成される
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_logger("test", log_dir=tmpdir)

        log_file = Path(tmpdir) / "test.log"
        assert log_file.exists()
