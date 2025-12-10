"""共通ユーティリティパッケージ (互換性レイヤー)。

このモジュールは後方互換性のために残されています。
新しいコードでは nook.core を使用してください。
"""

# 互換性のための re-export
from nook.core.clients.gpt_client import GPTClient
from nook.core.clients.http_client import (
    AsyncHTTPClient,
    close_http_client,
    get_http_client,
)
from nook.core.clients.rate_limiter import RateLimitedHTTPClient, RateLimiter
from nook.core.config import BaseConfig
from nook.core.errors.error_metrics import ErrorMetrics, error_metrics
from nook.core.errors.exceptions import APIException, RetryException, ServiceException
from nook.core.errors.service_errors import ServiceErrorHandler

# logging_utils は個別関数が多いため、モジュールとして re-export
from nook.core.logging import logging_utils
from nook.core.logging.logging import setup_logger
from nook.core.storage.daily_merge import merge_grouped_records, merge_records
from nook.core.storage.daily_snapshot import (
    group_records_by_date,
    store_daily_snapshots,
)
from nook.core.storage.storage import LocalStorage
from nook.core.utils import date_utils
from nook.core.utils.async_utils import AsyncTaskManager, gather_with_errors
from nook.core.utils.date_utils import (
    is_within_target_dates,
    normalize_datetime_to_local,
    target_dates_set,
)
from nook.core.utils.decorators import handle_errors, log_execution_time
from nook.core.utils.dedup import (
    DedupTracker,
    TitleNormalizer,
    load_existing_titles_from_storage,
)
from nook.services.base.base_service import BaseService
from nook.services.base.feed_utils import parse_entry_datetime

__all__ = [
    # clients
    "GPTClient",
    "AsyncHTTPClient",
    "get_http_client",
    "close_http_client",
    "RateLimiter",
    "RateLimitedHTTPClient",
    # config
    "BaseConfig",
    # errors
    "APIException",
    "ServiceException",
    "RetryException",
    "ServiceErrorHandler",
    "ErrorMetrics",
    "error_metrics",
    # logging
    "setup_logger",
    "logging_utils",
    # storage
    "LocalStorage",
    "merge_records",
    "merge_grouped_records",
    "group_records_by_date",
    "store_daily_snapshots",
    # utils
    "AsyncTaskManager",
    "gather_with_errors",
    "is_within_target_dates",
    "normalize_datetime_to_local",
    "target_dates_set",
    "date_utils",
    "handle_errors",
    "log_execution_time",
    "DedupTracker",
    "TitleNormalizer",
    "load_existing_titles_from_storage",
    # services
    "BaseService",
    "parse_entry_datetime",
]
