"""互換性レイヤー: nook.core.clients.http_client への転送"""

from nook.core.clients.http_client import *  # noqa: F403, F401
from nook.core.clients.http_client import (  # noqa: F401
    _global_client,
    close_http_client,
    get_http_client,
)
