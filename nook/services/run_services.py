"""互換性レイヤー: nook.services.run_services への参照を維持.

このモジュールは後方互換性のために存在します。
新しいコードでは nook.services.runner.run_services を使用してください。
"""

# 新しいモジュールから全てを再エクスポート
from nook.services.runner.run_services import *  # noqa: F401, F403
from nook.services.runner.run_services import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
