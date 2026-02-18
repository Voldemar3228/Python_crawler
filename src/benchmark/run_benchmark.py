# src/benchmark/run_benchmark.py
import asyncio
import time
import tracemalloc
from tqdm import tqdm

from benchmark.sync_crawler import crawl_sync
from crawler.async_crawler import AsyncCrawler

START_URLS = ["https://www.wikipedia.org/"]


# =========================
# Асинхронный краулер
# =========================
async def crawl_async(max_pages: int):
    crawler = AsyncCrawler(
        max_concurrent=10,
        max_depth=2,
        respect_robots=False,
        requests_per_second=5,
    )

    async with crawler:
        # crawl() сам управляет очередью и воркерами
        results = await crawler.crawl(
            start_urls=START_URLS,
            max_pages=max_pages,
            progress_interval=1.0  # обновление логов каждые 1 сек
        )

    return results, len(results)


# =========================
# Функция для измерения памяти и времени
# =========================
def measure_memory(func, *args, **kwargs):
    tracemalloc.start()
    t0 = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / (1024 * 1024)
    return result, elapsed, peak_mb


# =========================
# Основной benchmark
# =========================
def run_benchmark():
    pages_list = [1, 2, 10]  # можно увеличить до 100/500/1000 для тестов
    print(f"{'Pages':>6} | {'SYNC Time (s)':>12} | {'SYNC Mem (MB)':>13} | {'ASYNC Time (s)':>14} | {'ASYNC Mem (MB)':>13}")
    print("-"*75)

    for max_pages in pages_list:
        # --- SYNC crawl ---
        (sync_results, sync_count), sync_time, sync_mem = measure_memory(crawl_sync, START_URLS, max_pages)

        # --- ASYNC crawl ---
        tracemalloc.start()
        t0 = time.time()
        async_results, async_count = asyncio.run(crawl_async(max_pages))
        async_time = time.time() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        async_mem = peak / (1024 * 1024)

        # --- Вывод результатов ---
        print(f"{max_pages:>6} | {sync_time:>12.2f} | {sync_mem:>13.2f} | {async_time:>14.2f} | {async_mem:>13.2f}")


if __name__ == "__main__":
    run_benchmark()
