"""互換性レイヤー: nook.common.daily_merge -> nook.core.storage.daily_merge"""
from nook.core.storage.daily_merge import *  # noqa: F401, F403
from nook.core.storage.daily_merge import merge_grouped_records, merge_records  # noqa: F401

__all__ = ["merge_grouped_records", "merge_records"]
