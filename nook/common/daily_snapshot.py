"""互換性レイヤー: nook.common.daily_snapshot -> nook.core.storage.daily_snapshot"""
from nook.core.storage.daily_snapshot import *  # noqa: F401, F403
from nook.core.storage.daily_snapshot import (  # noqa: F401
    group_records_by_date,
    store_daily_snapshots,
)

__all__ = ["group_records_by_date", "store_daily_snapshots"]
