"""互換性レイヤー: nook.services.base_feed_service への参照を維持.

このモジュールは後方互換性のために存在します。
新しいコードでは nook.services.base.base_feed_service を使用してください。
"""

# 新しいモジュールから全てを再エクスポート
from nook.services.base.base_feed_service import *  # noqa: F401, F403
