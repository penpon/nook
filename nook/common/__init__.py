"""共通ユーティリティパッケージ - 互換性レイヤー。

このモジュールは後方互換性のために存在します。
新しいコードでは nook.core からインポートしてください。

Note:
    nook.common.* は nook.core.* への re-export として機能します。
    将来のバージョンでは非推奨になる可能性があります。
"""

# Configuration
from nook.core.config import BaseConfig  # noqa: F401

# Exceptions
from nook.core.errors.exceptions import (  # noqa: F401
    APIException,
    RetryException,
    ServiceException,
)

# Error handling
from nook.core.errors.error_metrics import ErrorMetrics  # noqa: F401
from nook.core.errors.service_errors import ServiceErrorHandler  # noqa: F401

# Logging
from nook.core.logging.logging import setup_logger  # noqa: F401
from nook.core.logging.logging_utils import (  # noqa: F401
    log_article_counts,
    log_multiple_dates_processing,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)

# Decorators
from nook.core.utils.decorators import (  # noqa: F401
    handle_errors,
    log_execution_time,
)

# Async utilities
from nook.core.utils.async_utils import (  # noqa: F401
    AsyncTaskManager,
    TaskResult,
    batch_process,
    gather_with_errors,
    run_sync_in_thread,
    run_with_semaphore,
)

# Date utilities
from nook.core.utils.date_utils import (  # noqa: F401
    compute_target_dates,
    is_within_target_dates,
    normalize_datetime_to_local,
    target_dates_set,
)

# Deduplication
from nook.core.utils.dedup import (  # noqa: F401
    DedupTracker,
    TitleNormalizer,
    load_existing_titles_from_storage,
)

# Storage
from nook.core.storage.storage import LocalStorage  # noqa: F401
from nook.core.storage.daily_merge import (  # noqa: F401
    merge_grouped_records,
    merge_records,
)
from nook.core.storage.daily_snapshot import (  # noqa: F401
    group_records_by_date,
    store_daily_snapshots,
)

# Clients
from nook.core.clients.http_client import (  # noqa: F401
    AsyncHTTPClient,
    close_http_client,
    get_http_client,
)
from nook.core.clients.gpt_client import GPTClient  # noqa: F401
from nook.core.clients.rate_limiter import (  # noqa: F401
    RateLimitedHTTPClient,
    RateLimiter,
)
