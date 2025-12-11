"""互換性レイヤー: nook.common.base_service -> nook.services.base.base_service"""
from nook.services.base.base_service import *  # noqa: F401, F403
from nook.services.base.base_service import BaseService  # noqa: F401

__all__ = ["BaseService"]
