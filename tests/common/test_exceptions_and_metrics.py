from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.exceptions import APIException, ServiceException
from nook.common.error_metrics import ErrorMetrics
from nook.common.logging_utils import (
    log_article_counts,
    log_multiple_dates_processing,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summary_candidates,
    log_summarization_progress,
    log_summarization_start,
)
from nook.common.rate_limiter import RateLimiter
from nook.common.service_errors import ServiceErrorHandler


def _run(coro):
    import asyncio

    return asyncio.run(coro)


class DummyLogger:
    def __init__(self):
        self.messages: list[str] = []

    def info(self, message: str, *args, **kwargs):
        if args:
            message = message % args
        self.messages.append(message)

    def error(self, message: str, *args, **kwargs):
        self.messages.append(message)


def test_service_error_handler_converts_api_errors(monkeypatch):
    handler = ServiceErrorHandler("sample")
    handler.logger = DummyLogger()

    class HTTPError(Exception):
        def __init__(self):
            self.response = SimpleNamespace(status_code=429, text="rate limit")

    @handler.handle_api_error("external")
    async def failing_call():
        raise HTTPError()

    async def main():
        with pytest.raises(APIException) as excinfo:
            await failing_call()
        return excinfo

    excinfo = _run(main())
    assert excinfo.value.status_code == 429
    assert "external" in str(excinfo.value)


def test_service_error_handler_wraps_data_processing(monkeypatch):
    handler = ServiceErrorHandler("svc")
    handler.logger = DummyLogger()

    @handler.handle_data_processing("transform data")
    async def failing_process():
        raise RuntimeError("boom")

    async def main():
        with pytest.raises(ServiceException) as excinfo:
            await failing_process()
        return excinfo

    excinfo = _run(main())
    assert "transform data" in str(excinfo.value)


def test_api_exception_fields_preserved():
    exc = APIException("oops", status_code=500, response_body="body")
    assert exc.status_code == 500
    assert exc.response_body == "body"


def test_error_metrics_tracks_recent_errors():
    metrics = ErrorMetrics(window_minutes=1)
    metrics.record_error("api", {"detail": "x"})

    stats = metrics.get_error_stats()
    assert stats["api"]["count"] == 1

    report = metrics.get_error_report()
    assert "api" in report

    # 古いエラーは集計から除外される
    old_time = datetime.utcnow() - timedelta(minutes=5)
    metrics.errors["api"].append((old_time, {}))
    stats_after = metrics.get_error_stats()
    assert stats_after["api"]["count"] == 1


def test_error_metrics_empty_report_message():
    metrics = ErrorMetrics(window_minutes=1)
    assert metrics.get_error_report().startswith("No errors")


def test_rate_limiter_waits_when_tokens_insufficient(monkeypatch):
    limiter = RateLimiter(rate=10, per=timedelta(milliseconds=1), burst=2)
    limiter.allowance = 0.0
    limiter.last_check = datetime.utcnow()

    sleep_calls: list[float] = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)
        # simulate elapsed time so that allowance recovers
        limiter.last_check -= timedelta(seconds=duration)

    monkeypatch.setattr("nook.common.rate_limiter.asyncio.sleep", fake_sleep)

    async def main():
        await limiter.acquire(tokens=3)

    _run(main())

    assert sleep_calls, "should wait when allowance is insufficient"
    assert limiter.allowance <= limiter.burst


def test_logging_utils_emit_messages():
    logger = DummyLogger()
    log_processing_start(logger, "2024-11-01")
    log_article_counts(logger, 1, 2)
    log_summary_candidates(
        logger,
        candidates=[SimpleNamespace(title="Sample", popularity_score=1)],
    )
    log_summarization_start(logger)
    log_summarization_progress(logger, 1, 2, "Article")
    log_storage_complete(logger, "a.json", "a.md")
    log_no_new_articles(logger)
    log_multiple_dates_processing(
        logger, [date(2024, 11, 1), date(2024, 11, 2)]
    )

    assert len(logger.messages) >= 7
    assert any("保存完了" in message for message in logger.messages)

*** End Patch
