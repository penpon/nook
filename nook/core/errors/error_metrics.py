import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta


class ErrorMetrics:
    """エラーメトリクスの収集と集約"""

    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.errors: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)
        self.lock = threading.Lock()

    def record_error(self, error_type: str, details: dict):
        """エラーを記録"""
        with self.lock:
            now = datetime.now(UTC)
            self.errors[error_type].append((now, details))

            # 古いエラーを削除
            cutoff = now - timedelta(minutes=self.window_minutes)
            self.errors[error_type] = [(ts, d) for ts, d in self.errors[error_type] if ts > cutoff]

    def get_error_stats(self) -> dict[str, dict]:
        """エラー統計を取得"""
        with self.lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(minutes=self.window_minutes)

            stats = {}
            for error_type, error_list in self.errors.items():
                recent_errors = [(ts, d) for ts, d in error_list if ts > cutoff]

                if recent_errors:
                    stats[error_type] = {
                        "count": len(recent_errors),
                        "first_occurrence": recent_errors[0][0].isoformat(),
                        "last_occurrence": recent_errors[-1][0].isoformat(),
                        "rate_per_minute": len(recent_errors) / self.window_minutes,
                    }

            return stats

    def get_error_report(self) -> str:
        """エラーレポートを生成"""
        stats = self.get_error_stats()

        if not stats:
            return f"No errors in the last {self.window_minutes} minutes"

        report_lines = [f"Error Report (last {self.window_minutes} minutes)", "=" * 50]

        for error_type, stat in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
            report_lines.extend(
                [
                    f"\nError Type: {error_type}",
                    f"Count: {stat['count']}",
                    f"Rate: {stat['rate_per_minute']:.2f} errors/minute",
                    f"First: {stat['first_occurrence']}",
                    f"Last: {stat['last_occurrence']}",
                ]
            )

        return "\n".join(report_lines)


# グローバルインスタンス
error_metrics = ErrorMetrics()
