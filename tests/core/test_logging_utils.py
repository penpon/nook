from datetime import date
from unittest.mock import MagicMock

from nook.core.logging.logging_utils import (
    log_article_counts,
    log_multiple_dates_processing,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)


class MockItem:
    def __init__(self, title=None, name=None, score=None):
        if title:
            self.title = title
        if name:
            self.name = name
        if score is not None:
            self.popularity_score = score


def test_log_processing_start():
    logger = MagicMock()
    log_processing_start(logger, "2025-01-01")
    logger.info.assert_called_once()
    assert "2025-01-01" in logger.info.call_args[0][0]


def test_log_article_counts():
    logger = MagicMock()
    log_article_counts(logger, 10, 5)
    logger.info.assert_called_once()
    msg = logger.info.call_args[0][0]
    assert "既存: 10" in msg
    assert "新規: 5" in msg


def test_log_summary_candidates_empty():
    logger = MagicMock()
    log_summary_candidates(logger, [])
    logger.info.assert_not_called()


class ItemWithStrMethod:
    def __str__(self):
        return "Simple String"


def test_log_summary_candidates_items():
    logger = MagicMock()
    items = [
        MockItem(title="Title A", score=100),
        MockItem(name="Name B", score=50.5),  # float score
        ItemWithStrMethod(),
    ]

    log_summary_candidates(logger, items)

    # Expected calls: 1 (header) + 3 (items)
    assert logger.info.call_count == 4

    calls = [args[0] for args, _ in logger.info.call_args_list]
    assert "要約対象: 3件" in calls[0]
    assert "Title A" in calls[1]
    assert "100" in calls[1]
    assert "Name B" in calls[2]
    assert "50" in calls[2]  # 50.5 -> 50 format is {:.0f}
    assert "Simple String" in calls[3]


def test_log_summarization_start():
    logger = MagicMock()
    log_summarization_start(logger)
    logger.info.assert_called_once()
    assert "要約生成中" in logger.info.call_args[0][0]


def test_log_summarization_progress():
    logger = MagicMock()
    # Test title truncation
    long_title = "A" * 60
    log_summarization_progress(logger, 1, 10, long_title)

    msg = logger.info.call_args[0][0]
    assert "1/10" in msg
    assert "AAAA..." in msg
    assert len(msg) < 100  # Rough check

    # Short title
    log_summarization_progress(logger, 2, 10, "Short")
    assert "Short" in logger.info.call_args_list[1][0][0]


def test_log_storage_complete():
    logger = MagicMock()
    log_storage_complete(logger, "a.json", "a.md")
    logger.info.assert_called_once()
    msg = logger.info.call_args[0][0]
    assert "a.json" in msg
    assert "a.md" in msg


def test_log_no_new_articles():
    logger = MagicMock()
    log_no_new_articles(logger)
    logger.info.assert_called()
    assert "新規記事がありません" in logger.info.call_args[0][0]


def test_log_multiple_dates_processing():
    logger = MagicMock()

    # 1 date case
    dates = [date(2025, 1, 1)]
    log_multiple_dates_processing(logger, dates)
    args = logger.info.call_args[0]
    assert "2025-01-01" in args[0]
    assert "記事を処理中" in args[0]

    # Many dates case
    dates = [date(2025, 1, 1), date(2025, 1, 5)]
    log_multiple_dates_processing(logger, dates)

    # Check second call
    args = logger.info.call_args_list[1][0]
    assert "対象期間: %s 〜 %s" in args[0]
    assert args[1] == "2025-01-01"
    assert args[2] == "2025-01-05"
