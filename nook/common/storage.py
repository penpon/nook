"""互換性レイヤー: nook.common.storage -> nook.core.storage.storage"""
from nook.core.storage.storage import *  # noqa: F401, F403
from nook.core.storage.storage import LocalStorage  # noqa: F401

__all__ = ["LocalStorage"]
