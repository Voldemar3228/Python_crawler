# src/benchmark/async_crawler.py
import asyncio
from crawler.async_crawler import AsyncCrawler
from tqdm import tqdm

START_URLS = ["https://www.wikipedia.org/"]

async def crawl_async(max_pages: int):
    """
    Асинхронный краулер для бенчмарка.
    - Возвращает список результатов и их количество
    - Использует tqdm для прогресса
    """
    crawler = AsyncCrawler(
        max_concurrent=10,   # можно увеличивать для тестов
        max_depth=2,
        respect_robots=False,
        requests_per_second=5,
    )

    results = []

    async with crawler:
        # crawl() уже сам управляет очередью и прогрессом
        all_results = await crawler.crawl(
            start_urls=START_URLS,
            max_pages=max_pages,
            progress_interval=1.0  # лог каждые 1 сек
        )

        # tqdm просто для визуального прогресса в конце (после завершения)
        for _ in tqdm(all_results[:max_pages], desc="ASYNC crawl"):
            results.append(_)  # копируем в локальный results

    return results[:max_pages], len(results[:max_pages])
