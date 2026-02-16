import asyncio
from typing import Optional, Tuple


class CrawlerQueue:
    """
    Очередь URL с приоритетом = depth.
    Меньший depth = выше приоритет.
    """

    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._seen = set()
        self._processed = set()
        self._failed = {}
        self._lock = asyncio.Lock()
        self._added_count = 0

    async def add_url(self, url: str, depth: int = 0, priority: int = None):
        """
        Добавляем URL.
        Можно передать depth или priority (для совместимости с тестами).
        Если указан priority — используем его.
        """

        if priority is not None:
            depth = priority  # для тестов

        async with self._lock:
            if url in self._seen:
                return

            await self._queue.put((depth, url))
            self._seen.add(url)
            self._added_count += 1

    async def get_next(self) -> Optional[Tuple[str, int]]:
        """
        Возвращает (url, depth)
        """
        if self._queue.empty():
            return None

        depth, url = await self._queue.get()
        return url, depth

    def mark_processed(self, url: str):
        self._processed.add(url)

    def mark_failed(self, url: str, error: str):
        self._failed[url] = error

    def get_stats(self) -> dict:
        return {
            "total_added": self._added_count,
            "in_queue": self._queue.qsize(),
            "processed": len(self._processed),
            "failed": len(self._failed),
            "unique_seen": len(self._seen),
        }
