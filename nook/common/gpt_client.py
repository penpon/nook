"""互換性レイヤー: nook.common.gpt_client -> nook.core.clients.gpt_client"""
from nook.core.clients.gpt_client import *  # noqa: F401, F403
from nook.core.clients.gpt_client import GPTClient  # noqa: F401

__all__ = ["GPTClient"]
