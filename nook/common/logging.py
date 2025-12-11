"""互換性レイヤー: nook.common.logging -> nook.core.logging.logging"""
from nook.core.logging.logging import *  # noqa: F401, F403
from nook.core.logging.logging import setup_logger  # noqa: F401

__all__ = ["setup_logger"]
