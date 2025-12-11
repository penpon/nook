"""互換性レイヤー: nook.common.config -> nook.core.config"""
from nook.core.config import *  # noqa: F401, F403
from nook.core.config import BaseConfig  # noqa: F401

__all__ = ["BaseConfig"]
