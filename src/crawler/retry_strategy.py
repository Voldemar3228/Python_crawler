# src/crawler/retry_strategy.py
import asyncio
import random
from typing import Callable, Dict, Type, Optional


class RetryStrategy:
    """
    RetryStrategy с поддержкой:
    - разных стратегий для разных типов ошибок,
    - callback на каждую попытку,
    - экспоненциального backoff с jitter,
    - фиксированных таймаутов (не меняем ClientSession).
    """

    def __init__(
        self,
        strategy: Dict[Type[Exception], Dict],
        on_retry: Optional[Callable[[Exception, int, Type[Exception], float, str], None]] = None,
    ):
        """
        :param strategy: словарь вида
            {
                TransientError: {"max_retries": 3, "backoff_factor": 2.0},
                NetworkError: {"max_retries": 2, "backoff_factor": 1.5},
            }
        :param on_retry: callback(exc, attempt, exc_type, delay, url)
        """
        self.strategy = strategy
        self.on_retry = on_retry

    async def execute_with_retry(
            self,
            coro: Callable,
            *args,
            on_retry: Optional[Callable] = None,
            **kwargs
    ):
        attempt_counts = {err: 0 for err in self.strategy}
        url = kwargs.get("url", "unknown")

        callback = on_retry or self.on_retry

        while True:
            try:
                return await coro(*args, **kwargs)

            except Exception as exc:
                exc_type = type(exc)

                if exc_type in self.strategy:
                    cfg = self.strategy[exc_type]
                    attempt_counts[exc_type] += 1
                    attempt = attempt_counts[exc_type]

                    if attempt > cfg.get("max_retries", 0):
                        if callback:
                            callback(exc, attempt, exc_type, delay=None, url=url)
                        raise

                    delay = cfg.get("backoff_factor", 1.0) ** (attempt - 1)
                    jitter = random.random() * 0.5
                    total_delay = delay + jitter

                    if callback:
                        callback(exc, attempt, exc_type, delay=total_delay, url=url)

                    await asyncio.sleep(total_delay)

                else:
                    raise

