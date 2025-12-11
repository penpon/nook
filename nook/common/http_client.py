"""互換性レイヤー: nook.common.http_client -> nook.core.clients.http_client"""
from nook.core.clients.http_client import (  # noqa: F401
    AsyncHTTPClient,
    close_http_client,
    get_http_client,
)

# 内部変数とロガーも export（テスト用）
from nook.core.clients import http_client as _http_client_module

# ロガーを re-export
logger = _http_client_module.logger


# モジュールレベルの _global_client を同期させるため
def __getattr__(name):
    if name == "_global_client":
        return _http_client_module._global_client
    raise AttributeError(f"module 'nook.common.http_client' has no attribute '{name}'")


def __setattr__(name, value):
    if name == "_global_client":
        _http_client_module._global_client = value
    else:
        globals()[name] = value


__all__ = [
    "AsyncHTTPClient",
    "close_http_client",
    "get_http_client",
    "_global_client",
    "logger",
]
