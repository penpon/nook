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
