"""互換性レイヤー: nook.common.date_utils -> nook.core.utils.date_utils"""
from nook.core.utils.date_utils import (  # noqa: F401
    compute_target_dates,
    is_within_target_dates,
    normalize_datetime_to_local,
    target_dates_set,
)

# 内部関数も export（テスト用）
from nook.core.utils.date_utils import _local_timezone  # noqa: F401

__all__ = [
    "_local_timezone",
    "compute_target_dates",
    "is_within_target_dates",
    "normalize_datetime_to_local",
    "target_dates_set",
]
