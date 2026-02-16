import asyncio
from urllib.parse import urlparse
from contextlib import asynccontextmanager


class SemaphoreManager:
    def __init__(self, global_limit: int = 20, per_domain_limit: int = 5):
        self._global_semaphore = asyncio.Semaphore(global_limit)
        self._domain_limit = per_domain_limit
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()
        self._active_tasks = 0
        self._active_lock = asyncio.Lock()

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    async def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        async with self._lock:
            if domain not in self._domain_semaphores:
                self._domain_semaphores[domain] = asyncio.Semaphore(self._domain_limit)
            return self._domain_semaphores[domain]

    @asynccontextmanager
    async def limit(self, url: str):
        domain = self._get_domain(url)
        domain_semaphore = await self._get_domain_semaphore(domain)

        await self._global_semaphore.acquire()
        await domain_semaphore.acquire()

        async with self._active_lock:
            self._active_tasks += 1

        try:
            yield
        finally:
            domain_semaphore.release()
            self._global_semaphore.release()
            async with self._active_lock:
                self._active_tasks -= 1

    def get_stats(self) -> dict:
        return {
            "global_available": self._global_semaphore._value,
            "domain_limit": self._domain_limit,
            "domains_tracked": len(self._domain_semaphores),
            "active_tasks": self._active_tasks,
        }
