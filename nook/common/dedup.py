"""互換性レイヤー: nook.common.dedup -> nook.core.utils.dedup"""
from nook.core.utils.dedup import *  # noqa: F401, F403
from nook.core.utils.dedup import (  # noqa: F401
    DedupTracker,
    TitleNormalizer,
    load_existing_titles_from_storage,
)

__all__ = ["DedupTracker", "TitleNormalizer", "load_existing_titles_from_storage"]
