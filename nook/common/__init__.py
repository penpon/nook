"""Compatibility layer for nook.common.

This package is deprecated. Please use ``nook.core`` instead. 既存の
``nook.common`` 参照が壊れないよう、対応する新モジュールへリダイレクトする。
"""

from __future__ import annotations

import importlib
import sys
import warnings

_MODULE_MAP: dict[str, str] = {
    "config": "nook.core.config",
    "gpt_client": "nook.core.clients.gpt_client",
    "http_client": "nook.core.clients.http_client",
    "rate_limiter": "nook.core.clients.rate_limiter",
    "error_metrics": "nook.core.errors.error_metrics",
    "exceptions": "nook.core.errors.exceptions",
    "service_errors": "nook.core.errors.service_errors",
    "logging": "nook.core.logging.logging",
    "logging_utils": "nook.core.logging.logging_utils",
    "storage": "nook.core.storage.storage",
    "daily_merge": "nook.core.storage.daily_merge",
    "daily_snapshot": "nook.core.storage.daily_snapshot",
    "async_utils": "nook.core.utils.async_utils",
    "date_utils": "nook.core.utils.date_utils",
    "decorators": "nook.core.utils.decorators",
    "dedup": "nook.core.utils.dedup",
    "base_service": "nook.services.base.base_service",
    "feed_utils": "nook.services.base.feed_utils",
    "base_feed_service": "nook.services.base.base_feed_service",
}


def _redirect_module(name: str, target: str) -> None:
    module_name = f"{__name__}.{name}"
    try:
        module = importlib.import_module(target)
    except Exception as exc:  # pragma: no cover - 保護的フェール
        warnings.warn(
            f"Failed to import compatibility module '{module_name}' -> '{target}': {exc}",
            ImportWarning,
            stacklevel=2,
        )
        return

    sys.modules[module_name] = module


for _name, _target in _MODULE_MAP.items():
    _redirect_module(_name, _target)

warnings.warn(
    "nook.common is deprecated. Use nook.core instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = list(_MODULE_MAP.keys())
