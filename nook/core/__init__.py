# noqa: D104
"""Core package - configuration and base components.

This package contains the core infrastructure modules:
- config: Base configuration
- clients: HTTP clients (AsyncHTTPClient, GPTClient, RateLimiter)
- errors: Exception classes and error handling
- logging: Logging utilities
- storage: Storage and snapshot utilities
- utils: Async utilities, decorators, date utilities, deduplication
"""

from nook.core.config import BaseConfig

__all__ = [
    "BaseConfig",
]
