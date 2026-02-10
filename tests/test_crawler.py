import time
import pytest
from crawler.crawler import AsyncCrawler
import aiohttp


@pytest.mark.asyncio
async def test_valid_urls(test_server):
    """
    ✅ Testing the successful loading of multiple valid URLs
    /
    ✅ Тест успешной загрузки нескольких валидных URL
    """
    crawler = AsyncCrawler()

    urls = [
        f"{test_server}/ok",
        f"{test_server}/ok2",
    ]

    results_list = await crawler.fetch_urls(urls)
    results = dict(results_list)  # превращаем список кортежей в словарь

    assert len(results) == 2
    assert results[f"{test_server}/ok"] == "OK"
    assert results[f"{test_server}/ok2"] == "OK2"

    await crawler.close()

    print('\n')


@pytest.mark.asyncio
async def test_404_url(test_server):
    """
    ❌ 404 processing test
    /
    ❌ Тест обработки 404
    """
    crawler = AsyncCrawler()
    url = f"{test_server}/not-exist"
    result = await crawler.fetch_url(url)

    assert "HTTP ERROR 404" in result

    await crawler.close()

    print('\n')


@pytest.mark.asyncio
async def test_timeout(test_server):
    """
    ⏰ Timeout handling test
    /
    ⏰ Тест обработки таймаута
    """
    # создаем Crawler с маленьким таймаутом чтения
    crawler = AsyncCrawler(timeout=aiohttp.ClientTimeout(sock_read=0.5))
    result = await crawler.fetch_url(f"{test_server}/slow")

    assert "TIMEOUT" in result

    await crawler.close()

    print('\n')


@pytest.mark.asyncio
async def test_parallel_vs_sequential(test_server):
    """
    ⚡️Checking that parallel loading is faster than sequential loading
    /
    ⚡️ Проверка, что параллельная загрузка быстрее последовательной
    """
    urls = [f"{test_server}/slow" for _ in range(5)]
    crawler = AsyncCrawler(max_concurrent=5)

    # последовательная
    start = time.perf_counter()
    for url in urls:
        await crawler.fetch_url(url)
    sequential_time = time.perf_counter() - start

    # параллельная
    start = time.perf_counter()
    await crawler.fetch_urls(urls)
    parallel_time = time.perf_counter() - start

    await crawler.close()

    print(f"\nSequential: {sequential_time:.2f}s")
    print(f"Parallel:   {parallel_time:.2f}s")

    assert parallel_time < sequential_time
