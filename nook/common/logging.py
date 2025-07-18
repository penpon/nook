import json
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッタ"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # カスタムフィールドの追加
        for key, value in record.__dict__.items():
            if key not in [
                "message",
                "levelname",
                "name",
                "module",
                "funcName",
                "lineno",
                "exc_info",
                "exc_text",
                "stack_info",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            ]:
                log_obj[key] = value

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(
    name: str, level: str = "INFO", log_dir: str = "logs", use_json: bool = True
) -> logging.Logger:
    """ロガーのセットアップ"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 既存のハンドラーをクリア
    logger.handlers.clear()

    # ログディレクトリの作成
    os.makedirs(log_dir, exist_ok=True)

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    if use_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    logger.addHandler(console_handler)

    # ファイルハンドラー（ローテーション付き）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f"{name}.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        JSONFormatter()
        if use_json
        else logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    return logger
