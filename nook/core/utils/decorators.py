import asyncio
import functools
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar, cast

from nook.core.errors.exceptions import RetryException

T = TypeVar("T")


def handle_errors(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """エラーハンドリングとリトライのデコレータ"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None

            for attempt in range(retries):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded after {attempt} retries")
                    return result

                except Exception as e:
                    last_exception = e
                    wait_time = delay * (backoff**attempt)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{retries}): {type(e).__name__}: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": retries,
                            "error": str(e),
                            "wait_time": wait_time,
                        },
                    )

                    if attempt < retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Function {func.__name__} failed after {retries} attempts")
                        raise RetryException(f"Failed after {retries} attempts: {e}") from e

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None

            for attempt in range(retries):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded after {attempt} retries")
                    return result

                except Exception as e:
                    last_exception = e
                    wait_time = delay * (backoff**attempt)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{retries}): {type(e).__name__}: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}"
                    )

                    if attempt < retries - 1:
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Function {func.__name__} failed after {retries} attempts")
                        raise RetryException(f"Failed after {retries} attempts: {e}") from e

            raise last_exception

        # 非同期関数か同期関数かを判定
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """実行時間をログに記録するデコレータ"""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()

        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Function {func.__name__} completed",
                extra={"function": func.__name__, "execution_time": execution_time},
            )
            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"Function {func.__name__} failed",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                },
            )
            raise e  # トレースバック出力を抑制するために、raise eに変更

    if asyncio.iscoroutinefunction(func):
        return cast(Callable[..., T], async_wrapper)
    else:
        # 同期版も同様に実装（省略）
        return func
