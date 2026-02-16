
import asyncio
import time
import random


class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0, per_domain: bool = True, min_delay: float = 0.0, jitter: float = 0.0):
        self.requests_per_second = requests_per_second
        self.per_domain = per_domain
        self.min_delay = min_delay
        self.jitter = jitter

        self._locks: dict[str, asyncio.Lock] = {}
        self._last_call: dict[str, float] = {}
        self.domain_delays: dict[str, list[float]] = {}  # для статистики задержек

    async def acquire(self, domain: str = "global"):
        if self.per_domain:
            lock = self._locks.setdefault(domain, asyncio.Lock())
        else:
            domain = "global"
            lock = self._locks.setdefault("global", asyncio.Lock())

        async with lock:
            now = time.time()
            last = self._last_call.get(domain, 0)
            wait_time = max(0, 1 / self.requests_per_second - (now - last))
            wait_time = max(wait_time, self.min_delay)

            # jitter для имитации "человеческой" задержки
            if self.jitter > 0:
                wait_time += random.uniform(0, self.jitter)

            if wait_time > 0:
                start = time.time()
                await asyncio.sleep(wait_time)
                end = time.time()

                # сохраняем задержку для статистики
                if domain not in self.domain_delays:
                    self.domain_delays[domain] = []
                self.domain_delays[domain].append(end - start)

            self._last_call[domain] = time.time()
