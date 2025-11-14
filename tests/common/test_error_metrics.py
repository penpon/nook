"""nook/common/error_metrics.py のテスト"""

from __future__ import annotations

import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.error_metrics import ErrorMetrics, error_metrics


# ================================================================================
# 1. ErrorMetrics.__init__ のテスト
# ================================================================================


@pytest.mark.unit
def test_error_metrics_init_default():
    """
    Given: デフォルトパラメータ
    When: ErrorMetricsを初期化
    Then: window_minutes=60となる
    """
    metrics = ErrorMetrics()
    assert metrics.window_minutes == 60
    assert metrics.errors == {}


@pytest.mark.unit
def test_error_metrics_init_custom_window():
    """
    Given: window_minutes=30
    When: ErrorMetricsを初期化
    Then: 30分ウィンドウとなる
    """
    metrics = ErrorMetrics(window_minutes=30)
    assert metrics.window_minutes == 30


@pytest.mark.unit
def test_error_metrics_init_minimum_window():
    """
    Given: window_minutes=1（最小）
    When: ErrorMetricsを初期化
    Then: 正常に初期化される
    """
    metrics = ErrorMetrics(window_minutes=1)
    assert metrics.window_minutes == 1


@pytest.mark.unit
def test_error_metrics_init_large_window():
    """
    Given: window_minutes=1440（24時間）
    When: ErrorMetricsを初期化
    Then: 正常に初期化される
    """
    metrics = ErrorMetrics(window_minutes=1440)
    assert metrics.window_minutes == 1440


# ================================================================================
# 2. ErrorMetrics.record_error のテスト
# ================================================================================


@pytest.mark.unit
def test_record_error_first_error():
    """
    Given: 初期状態のErrorMetrics
    When: 初回エラーを記録
    Then: エラーが記録される
    """
    metrics = ErrorMetrics()

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "test error"})

        assert "ValueError" in metrics.errors
        assert len(metrics.errors["ValueError"]) == 1
        assert metrics.errors["ValueError"][0][1] == {"msg": "test error"}


@pytest.mark.unit
def test_record_error_multiple_same_type():
    """
    Given: ErrorMetrics
    When: 同じerror_typeを複数回記録
    Then: リストに追加される
    """
    metrics = ErrorMetrics()

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error1"})
        metrics.record_error("ValueError", {"msg": "error2"})

        assert len(metrics.errors["ValueError"]) == 2


@pytest.mark.unit
def test_record_error_different_types():
    """
    Given: ErrorMetrics
    When: 異なるerror_typeを記録
    Then: 各タイプで管理される
    """
    metrics = ErrorMetrics()

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error1"})
        metrics.record_error("KeyError", {"msg": "error2"})

        assert "ValueError" in metrics.errors
        assert "KeyError" in metrics.errors
        assert len(metrics.errors["ValueError"]) == 1
        assert len(metrics.errors["KeyError"]) == 1


@pytest.mark.unit
def test_record_error_auto_cleanup_old_errors():
    """
    Given: window_minutes=60のErrorMetrics
    When: ウィンドウ外のエラーを記録後、新しいエラーを記録
    Then: 古いエラーが自動削除される
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        old_time = datetime(2025, 1, 1, 10, 0, 0)
        recent_time = datetime(2025, 1, 1, 12, 0, 0)

        # 古いエラーを記録
        mock_dt.utcnow.return_value = old_time
        metrics.record_error("ValueError", {"msg": "old error"})

        # 2時間後（ウィンドウ外）に新しいエラーを記録
        mock_dt.utcnow.return_value = recent_time
        metrics.record_error("ValueError", {"msg": "new error"})

        # 古いエラーは削除される
        assert len(metrics.errors["ValueError"]) == 1
        assert metrics.errors["ValueError"][0][1] == {"msg": "new error"}


@pytest.mark.unit
def test_record_error_within_window():
    """
    Given: window_minutes=60のErrorMetrics
    When: ウィンドウ内のエラーを記録
    Then: 全て保持される
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        base_time = datetime(2025, 1, 1, 12, 0, 0)

        # 30分前のエラー
        mock_dt.utcnow.return_value = base_time - timedelta(minutes=30)
        metrics.record_error("ValueError", {"msg": "error1"})

        # 現在のエラー
        mock_dt.utcnow.return_value = base_time
        metrics.record_error("ValueError", {"msg": "error2"})

        # 両方保持される
        assert len(metrics.errors["ValueError"]) == 2


@pytest.mark.unit
def test_record_error_boundary_exactly_cutoff():
    """
    Given: ErrorMetrics
    When: ちょうどcutoff時刻のエラー
    Then: 削除される
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        cutoff_time = datetime(2025, 1, 1, 11, 0, 0)
        now = datetime(2025, 1, 1, 12, 0, 0)

        # cutoff時刻ちょうどのエラー
        mock_dt.utcnow.return_value = cutoff_time
        metrics.record_error("ValueError", {"msg": "cutoff error"})

        # 現在時刻で新規エラー記録（cleanup発生）
        mock_dt.utcnow.return_value = now
        metrics.record_error("ValueError", {"msg": "new error"})

        # cutoff時刻のエラーは削除される（> cutoff判定）
        assert len(metrics.errors["ValueError"]) == 1
        assert metrics.errors["ValueError"][0][1] == {"msg": "new error"}


# ================================================================================
# 3. ErrorMetrics.get_error_stats のテスト
# ================================================================================


@pytest.mark.unit
def test_get_error_stats_with_errors():
    """
    Given: エラーが記録されているErrorMetrics
    When: get_error_statsを呼び出す
    Then: 統計dictが返る
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error1"})
        metrics.record_error("ValueError", {"msg": "error2"})

        stats = metrics.get_error_stats()

        assert "ValueError" in stats
        assert stats["ValueError"]["count"] == 2
        assert "first_occurrence" in stats["ValueError"]
        assert "last_occurrence" in stats["ValueError"]
        assert "rate_per_minute" in stats["ValueError"]


@pytest.mark.unit
def test_get_error_stats_no_errors():
    """
    Given: エラーが記録されていないErrorMetrics
    When: get_error_statsを呼び出す
    Then: 空のdictが返る
    """
    metrics = ErrorMetrics()
    stats = metrics.get_error_stats()
    assert stats == {}


@pytest.mark.unit
def test_get_error_stats_multiple_types():
    """
    Given: 複数タイプのエラーが記録されている
    When: get_error_statsを呼び出す
    Then: 各タイプの統計が含まれる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error1"})
        metrics.record_error("KeyError", {"msg": "error2"})

        stats = metrics.get_error_stats()

        assert "ValueError" in stats
        assert "KeyError" in stats


@pytest.mark.unit
def test_get_error_stats_count_calculation():
    """
    Given: N個のエラーが記録されている
    When: get_error_statsを呼び出す
    Then: count=Nとなる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        for i in range(5):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

        stats = metrics.get_error_stats()
        assert stats["ValueError"]["count"] == 5


@pytest.mark.unit
def test_get_error_stats_rate_calculation():
    """
    Given: 60分で60エラー
    When: get_error_statsを呼び出す
    Then: rate_per_minute=1.0となる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        for i in range(60):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

        stats = metrics.get_error_stats()
        assert stats["ValueError"]["rate_per_minute"] == 1.0


@pytest.mark.unit
def test_get_error_stats_first_last_occurrence():
    """
    Given: 複数エラーが記録されている
    When: get_error_statsを呼び出す
    Then: first/last_occurrenceがISO形式で返る
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        first_time = datetime(2025, 1, 1, 11, 30, 0)
        last_time = datetime(2025, 1, 1, 12, 0, 0)

        mock_dt.utcnow.return_value = first_time
        metrics.record_error("ValueError", {"msg": "first"})

        mock_dt.utcnow.return_value = last_time
        metrics.record_error("ValueError", {"msg": "last"})

        stats = metrics.get_error_stats()

        assert stats["ValueError"]["first_occurrence"] == first_time.isoformat()
        assert stats["ValueError"]["last_occurrence"] == last_time.isoformat()


@pytest.mark.unit
def test_get_error_stats_old_errors_excluded():
    """
    Given: ウィンドウ外の古いエラーのみ
    When: get_error_statsを呼び出す
    Then: 空のdictが返る
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        old_time = datetime(2025, 1, 1, 10, 0, 0)
        now = datetime(2025, 1, 1, 12, 0, 0)

        # 古いエラーを記録
        mock_dt.utcnow.return_value = old_time
        metrics.record_error("ValueError", {"msg": "old"})

        # 現在時刻で統計取得
        mock_dt.utcnow.return_value = now
        stats = metrics.get_error_stats()

        # ウィンドウ外なので空
        assert stats == {}


# ================================================================================
# 4. ErrorMetrics.get_error_report のテスト
# ================================================================================


@pytest.mark.unit
def test_get_error_report_with_errors():
    """
    Given: エラーが記録されている
    When: get_error_reportを呼び出す
    Then: フォーマット済みレポート文字列が返る
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error1"})

        report = metrics.get_error_report()

        assert "Error Report" in report
        assert "ValueError" in report


@pytest.mark.unit
def test_get_error_report_no_errors():
    """
    Given: エラーなし
    When: get_error_reportを呼び出す
    Then: "No errors in the last N minutes"が返る
    """
    metrics = ErrorMetrics(window_minutes=60)
    report = metrics.get_error_report()
    assert "No errors in the last 60 minutes" in report


@pytest.mark.unit
def test_get_error_report_header():
    """
    Given: エラーあり
    When: get_error_reportを呼び出す
    Then: ヘッダー行が含まれる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error"})
        report = metrics.get_error_report()

        assert "Error Report (last 60 minutes)" in report
        assert "=" * 50 in report


@pytest.mark.unit
def test_get_error_report_content():
    """
    Given: エラーあり
    When: get_error_reportを呼び出す
    Then: Error Type, Count, Rate, First, Lastが含まれる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        metrics.record_error("ValueError", {"msg": "error"})
        report = metrics.get_error_report()

        assert "Error Type: ValueError" in report
        assert "Count:" in report
        assert "Rate:" in report
        assert "First:" in report
        assert "Last:" in report


@pytest.mark.unit
def test_get_error_report_rate_format():
    """
    Given: エラーあり
    When: get_error_reportを呼び出す
    Then: Rateが小数点2桁で表示される
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        for i in range(150):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

        report = metrics.get_error_report()

        # 150 / 60 = 2.50
        assert "2.50 errors/minute" in report


@pytest.mark.unit
def test_get_error_report_sorted_by_count():
    """
    Given: 複数タイプのエラー
    When: get_error_reportを呼び出す
    Then: count降順でソートされる
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        # ValueErrorを10回
        for i in range(10):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

        # KeyErrorを5回
        for i in range(5):
            metrics.record_error("KeyError", {"msg": f"error{i}"})

        report = metrics.get_error_report()

        # ValueErrorがKeyErrorより先に表示される
        value_error_pos = report.index("ValueError")
        key_error_pos = report.index("KeyError")
        assert value_error_pos < key_error_pos


# ================================================================================
# 5. グローバルインスタンスのテスト
# ================================================================================


@pytest.mark.unit
def test_global_error_metrics_exists():
    """
    Given: モジュールインポート
    When: error_metricsにアクセス
    Then: ErrorMetricsインスタンスが存在する
    """
    assert isinstance(error_metrics, ErrorMetrics)
    assert error_metrics.window_minutes == 60


# ================================================================================
# 6. スレッドセーフのテスト
# ================================================================================


@pytest.mark.unit
def test_record_error_thread_safe():
    """
    Given: ErrorMetrics
    When: 複数スレッドから同時に記録
    Then: データ競合が発生しない
    """
    metrics = ErrorMetrics(window_minutes=60)

    def record_errors(count):
        for i in range(count):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

    threads = []
    for _ in range(10):
        thread = threading.Thread(target=record_errors, args=(10,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # 10スレッド × 10エラー = 100エラー
    assert len(metrics.errors["ValueError"]) == 100


@pytest.mark.unit
def test_get_error_stats_thread_safe():
    """
    Given: エラーが記録されているErrorMetrics
    When: 複数スレッドから同時に取得
    Then: 一貫性のあるデータが返る
    """
    metrics = ErrorMetrics(window_minutes=60)

    with patch("nook.common.error_metrics.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        for i in range(10):
            metrics.record_error("ValueError", {"msg": f"error{i}"})

    results = []

    def get_stats():
        stats = metrics.get_error_stats()
        results.append(stats["ValueError"]["count"] if "ValueError" in stats else 0)

    threads = []
    for _ in range(10):
        thread = threading.Thread(target=get_stats)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # 全てのスレッドが同じ結果を取得
    assert all(count == 10 for count in results)
