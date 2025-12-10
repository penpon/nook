# 互換性レイヤー設計書

## 概要

このドキュメントは、`nook/common/` から `nook/core/` への大規模リファクタリングにおける互換性レイヤーの設計を定義します。

**目的:**
- 既存の `from nook.common.xxx import yyy` パターンが引き続き動作すること
- 新しいコードは `from nook.core.xxx.yyy import zzz` を使用すること
- 段階的な移行を可能にすること

## 現状分析

### 現在のディレクトリ構造

```
nook/common/
├── __init__.py (ほぼ空)
├── async_utils.py
├── base_service.py
├── config.py
├── daily_merge.py
├── daily_snapshot.py
├── date_utils.py
├── decorators.py
├── dedup.py
├── error_metrics.py
├── exceptions.py
├── feed_utils.py
├── gpt_client.py
├── http_client.py
├── logging.py
├── logging_utils.py
├── rate_limiter.py
├── service_errors.py
└── storage.py
```

**ファイル数:** 19個

### 使用されている import パターン

#### nook/ 内での使用

```python
from nook.common.async_utils import AsyncTaskManager, gather_with_errors
from nook.common.base_service import BaseService
from nook.common.config import BaseConfig
from nook.common.daily_merge import merge_records
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.date_utils import is_within_target_dates, normalize_datetime_to_local, target_dates_set
from nook.common.decorators import handle_errors
from nook.common.dedup import DedupTracker, load_existing_titles_from_storage
from nook.common.error_metrics import error_metrics
from nook.common.exceptions import APIException, RetryException, ServiceException
from nook.common.feed_utils import parse_entry_datetime
from nook.common.gpt_client import GPTClient
from nook.common.http_client import AsyncHTTPClient, close_http_client, get_http_client
from nook.common.logging import setup_logger
from nook.common.logging_utils import (複数のユーティリティ関数)
from nook.common.storage import LocalStorage
```

#### tests/ 内での使用

```python
from nook.common import date_utils  # モジュール全体のインポート
from nook.common.async_utils import (複数)
from nook.common.base_service import BaseService
from nook.common.config import BaseConfig
from nook.common.daily_merge import merge_grouped_records, merge_records
from nook.common.daily_snapshot import (複数)
from nook.common.decorators import handle_errors, log_execution_time
from nook.common.dedup import DedupTracker, load_existing_titles_from_storage
from nook.common.error_metrics import ErrorMetrics, error_metrics
from nook.common.exceptions import APIException, RetryException, ServiceException
from nook.common.feed_utils import (複数)
from nook.common.gpt_client import GPTClient
from nook.common.http_client import AsyncHTTPClient
from nook.common.logging_utils import (複数)
from nook.common.rate_limiter import RateLimitedHTTPClient, RateLimiter
from nook.common.service_errors import ServiceErrorHandler
from nook.common.storage import LocalStorage
```

## 新しいディレクトリ構造

```
nook/core/
├── __init__.py
├── config.py (ルートレベル)
├── clients/
│   ├── __init__.py
│   ├── gpt_client.py
│   ├── http_client.py
│   └── rate_limiter.py
├── utils/
│   ├── __init__.py
│   ├── async_utils.py
│   ├── date_utils.py
│   ├── decorators.py
│   └── dedup.py
├── storage/
│   ├── __init__.py
│   ├── storage.py
│   ├── daily_merge.py
│   └── daily_snapshot.py
├── errors/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── service_errors.py
│   └── error_metrics.py
└── logging/
    ├── __init__.py
    ├── logging.py
    └── logging_utils.py

nook/services/base/
├── __init__.py
├── base_service.py (common から移動)
└── feed_utils.py (common から移動)
```

## モジュールマッピング

### logging サブパッケージ

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.logging` | `nook.core.logging.logging` | `setup_logger` |
| `nook.common.logging_utils` | `nook.core.logging.logging_utils` | 複数のユーティリティ関数 |

### clients サブパッケージ

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.gpt_client` | `nook.core.clients.gpt_client` | `GPTClient` |
| `nook.common.http_client` | `nook.core.clients.http_client` | `AsyncHTTPClient`, `get_http_client`, `close_http_client` |
| `nook.common.rate_limiter` | `nook.core.clients.rate_limiter` | `RateLimiter`, `RateLimitedHTTPClient` |

### utils サブパッケージ

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.async_utils` | `nook.core.utils.async_utils` | `AsyncTaskManager`, `gather_with_errors` |
| `nook.common.date_utils` | `nook.core.utils.date_utils` | `is_within_target_dates`, `normalize_datetime_to_local`, `target_dates_set` |
| `nook.common.decorators` | `nook.core.utils.decorators` | `handle_errors`, `log_execution_time` |
| `nook.common.dedup` | `nook.core.utils.dedup` | `DedupTracker`, `TitleNormalizer`, `load_existing_titles_from_storage` |

### storage サブパッケージ

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.storage` | `nook.core.storage.storage` | `LocalStorage` |
| `nook.common.daily_merge` | `nook.core.storage.daily_merge` | `merge_records`, `merge_grouped_records` |
| `nook.common.daily_snapshot` | `nook.core.storage.daily_snapshot` | `group_records_by_date`, `store_daily_snapshots` |

### errors サブパッケージ

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.exceptions` | `nook.core.errors.exceptions` | `APIException`, `ServiceException`, `RetryException` |
| `nook.common.service_errors` | `nook.core.errors.service_errors` | `ServiceErrorHandler` |
| `nook.common.error_metrics` | `nook.core.errors.error_metrics` | `ErrorMetrics`, `error_metrics` |

### config (ルートレベル)

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.config` | `nook.core.config` | `BaseConfig` |

### services/base へ移動

| 旧パス | 新パス | 主要エクスポート |
|--------|--------|------------------|
| `nook.common.base_service` | `nook.services.base.base_service` | `BaseService` |
| `nook.common.feed_utils` | `nook.services.base.feed_utils` | `parse_entry_datetime` 等 |

## 互換性レイヤー実装戦略

### 1. nook/core/ 各サブパッケージの __init__.py

各サブパッケージの `__init__.py` で主要なシンボルをエクスポートします。

#### nook/core/clients/__init__.py

```python
"""クライアント関連モジュール。"""

from nook.core.clients.gpt_client import GPTClient
from nook.core.clients.http_client import (
    AsyncHTTPClient,
    close_http_client,
    get_http_client,
)
from nook.core.clients.rate_limiter import RateLimitedHTTPClient, RateLimiter

__all__ = [
    "GPTClient",
    "AsyncHTTPClient",
    "get_http_client",
    "close_http_client",
    "RateLimiter",
    "RateLimitedHTTPClient",
]
```

#### nook/core/utils/__init__.py

```python
"""汎用ユーティリティモジュール。"""

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

__all__ = [
    "AsyncTaskManager",
    "gather_with_errors",
    "is_within_target_dates",
    "normalize_datetime_to_local",
    "target_dates_set",
    "handle_errors",
    "log_execution_time",
    "DedupTracker",
    "TitleNormalizer",
    "load_existing_titles_from_storage",
]
```

#### nook/core/storage/__init__.py

```python
"""ストレージ関連モジュール。"""

from nook.core.storage.daily_merge import merge_grouped_records, merge_records
from nook.core.storage.daily_snapshot import (
    group_records_by_date,
    store_daily_snapshots,
)
from nook.core.storage.storage import LocalStorage

__all__ = [
    "LocalStorage",
    "merge_records",
    "merge_grouped_records",
    "group_records_by_date",
    "store_daily_snapshots",
]
```

#### nook/core/errors/__init__.py

```python
"""エラー処理関連モジュール。"""

from nook.core.errors.error_metrics import ErrorMetrics, error_metrics
from nook.core.errors.exceptions import APIException, RetryException, ServiceException
from nook.core.errors.service_errors import ServiceErrorHandler

__all__ = [
    "APIException",
    "ServiceException",
    "RetryException",
    "ServiceErrorHandler",
    "ErrorMetrics",
    "error_metrics",
]
```

#### nook/core/logging/__init__.py

```python
"""ロギング関連モジュール。"""

from nook.core.logging.logging import setup_logger
from nook.core.logging.logging_utils import *  # noqa: F403

__all__ = ["setup_logger"]
```

### 2. nook/core/__init__.py

```python
"""Nook コアパッケージ。

このパッケージは、Nookプロジェクトの基盤となる機能を提供します。
"""

# サブパッケージのエクスポート
from nook.core import clients, errors, logging, storage, utils
from nook.core.config import BaseConfig

__all__ = [
    "clients",
    "utils",
    "storage",
    "errors",
    "logging",
    "BaseConfig",
]
```

### 3. nook/common/__init__.py (互換性レイヤー)

```python
"""共通ユーティリティパッケージ (互換性レイヤー)。

このモジュールは後方互換性のために残されています。
新しいコードでは nook.core を使用してください。
"""

import warnings

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
from nook.core.logging.logging import setup_logger
from nook.core.storage.daily_merge import merge_grouped_records, merge_records
from nook.core.storage.daily_snapshot import (
    group_records_by_date,
    store_daily_snapshots,
)
from nook.core.storage.storage import LocalStorage
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

# logging_utils は個別関数が多いため、モジュールとして re-export
from nook.core.logging import logging_utils
from nook.core.utils import date_utils

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


def _show_deprecation_warning():
    """互換性レイヤー使用時の警告を表示。"""
    warnings.warn(
        "nook.common is deprecated. Please use nook.core instead.",
        DeprecationWarning,
        stacklevel=3,
    )


# 初回インポート時に警告を表示（オプション）
# _show_deprecation_warning()
```

### 4. nook/services/base/__init__.py

```python
"""サービス基盤モジュール。"""

from nook.services.base.base_service import BaseService
from nook.services.base.feed_utils import parse_entry_datetime

__all__ = [
    "BaseService",
    "parse_entry_datetime",
]
```

## 移行戦略

### Phase 1: 構造作成 (Phase B)
1. `nook/core/` ディレクトリと各サブディレクトリを作成
2. 空の `__init__.py` を配置

### Phase 2: ファイル移動 (Phase C, D)
1. `git mv` でファイルを新しい場所に移動
2. 移動したファイル内の相対 import を修正
3. 各サブパッケージの `__init__.py` を実装

### Phase 3: 互換性レイヤー実装 (Phase E)
1. `nook/common/__init__.py` に re-export を追加
2. `nook/core/__init__.py` を実装
3. 全テストを実行して互換性を確認

### Phase 4: 段階的移行 (Phase E 以降)
1. 新しいコードは `nook.core` を使用
2. 既存コードは徐々に `nook.core` に移行
3. テストコードも新パスに更新

## 検証方法

### 1. 互換性テスト

```python
# tests/test_backward_compatibility.py

def test_common_imports():
    """旧パスからの import が動作することを確認"""
    # clients
    from nook.common.gpt_client import GPTClient
    from nook.common.http_client import AsyncHTTPClient
    
    # utils
    from nook.common.dedup import DedupTracker
    from nook.common.date_utils import target_dates_set
    
    # storage
    from nook.common.storage import LocalStorage
    
    # errors
    from nook.common.exceptions import APIException
    
    # services
    from nook.common.base_service import BaseService
    
    assert GPTClient is not None
    assert AsyncHTTPClient is not None
    assert DedupTracker is not None
    assert LocalStorage is not None
    assert APIException is not None
    assert BaseService is not None
```

### 2. 新パステスト

```python
def test_new_imports():
    """新パスからの import が動作することを確認"""
    from nook.core.clients import GPTClient
    from nook.core.utils import DedupTracker
    from nook.core.storage import LocalStorage
    
    assert GPTClient is not None
    assert DedupTracker is not None
    assert LocalStorage is not None
```

### 3. 同一性テスト

```python
def test_import_identity():
    """旧パスと新パスで同じオブジェクトを参照することを確認"""
    from nook.common.gpt_client import GPTClient as OldGPTClient
    from nook.core.clients import GPTClient as NewGPTClient
    
    assert OldGPTClient is NewGPTClient
```

## リスク分析

### 高リスク

1. **循環参照の可能性**
   - `nook/common/__init__.py` が `nook.core` と `nook.services` の両方を import
   - 対策: import 順序を慎重に設計

2. **モジュール全体の import**
   - `from nook.common import date_utils` のようなパターン
   - 対策: `nook/common/__init__.py` でモジュールも re-export

### 中リスク

1. **テストの更新漏れ**
   - 対策: grep で全 import を洗い出し、チェックリスト化

2. **相対 import の修正漏れ**
   - 対策: 各ファイル移動後に即座にテスト実行

### 低リスク

1. **パフォーマンスへの影響**
   - re-export による若干のオーバーヘッド
   - 影響: 無視できるレベル

## まとめ

この設計により、以下が実現されます:

1. ✅ 既存の `from nook.common.xxx import yyy` が引き続き動作
2. ✅ 新しいコードは `from nook.core.xxx.yyy import zzz` を使用可能
3. ✅ 段階的な移行が可能
4. ✅ テストカバレッジ 93% を維持
5. ✅ 後方互換性を保ちながら、将来的に `nook.common` を deprecate 可能

次のステップ: Phase B (core/ 構造作成) に進む
