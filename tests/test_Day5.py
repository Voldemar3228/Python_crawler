# test_async_crawler.py
import asyncio
import pytest
from aiohttp import web
from crawler.async_crawler import AsyncCrawler

# ------------------------
# Fixture: локальный сервер
# ------------------------
@pytest.fixture
async def test_server(aiohttp_server):
    call_counts = {"timeout": 0, "503": 0, "404": 0, "200": 0}

    async def handler(request):
        path = request.path
        if path == "/200":
            call_counts["200"] += 1
            return web.Response(text="OK", status=200)
        elif path == "/503":
            call_counts["503"] += 1
            return web.Response(text="Service Unavailable", status=503)
        elif path == "/404":
            call_counts["404"] += 1
            return web.Response(text="Not Found", status=404)
        elif path == "/timeout":
            call_counts["timeout"] += 1
            await asyncio.sleep(0.2)  # минимальный sleep
            return web.Response(text="Timeout", status=200)
        return web.Response(text="Unknown", status=500)

    app = web.Application()
    app.router.add_get("/{tail:.*}", handler)
    server = await aiohttp_server(app)
    server.call_counts = call_counts  # прикрепляем к серверу
    return server

# ------------------------
# Тест повторов на таймаут
# ------------------------
@pytest.mark.asyncio
async def test_retry_on_timeout(test_server):
    async with AsyncCrawler(
        respect_robots=False,
        total_timeout=0.1,  # увеличенный таймаут для надёжности
        max_concurrent=1
    ) as crawler:
        url = f"http://{test_server.host}:{test_server.port}/timeout"
        result = await crawler.fetch_url(url)
        assert result == ""
        assert "TransientError" in crawler.stats["errors"]
        # Проверяем, что произошло несколько попыток
        assert test_server.call_counts["timeout"] >= 2


# ------------------------
# Тест повторов на 503
# ------------------------
@pytest.mark.asyncio
async def test_retry_on_503(test_server):
    async with AsyncCrawler(
        respect_robots=False,
        max_concurrent=1
    ) as crawler:
        url = f"http://{test_server.host}:{test_server.port}/503"
        result = await crawler.fetch_url(url)
        assert result == ""
        assert "TransientError" in crawler.stats["errors"]
        # Проверяем, что было несколько попыток
        assert test_server.call_counts["503"] > 1

# ------------------------
# Тест отсутствия повторов на 404
# ------------------------
@pytest.mark.asyncio
async def test_no_retry_on_404(test_server):
    async with AsyncCrawler(
        respect_robots=False,
        max_concurrent=1
    ) as crawler:
        url = f"http://{test_server.host}:{test_server.port}/404"
        result = await crawler.fetch_url(url)
        assert result == ""
        # PermanentError → retries не происходит
        assert "PermanentError" in crawler.stats["errors"]
        # Проверяем, что была только одна попытка
        assert test_server.call_counts["404"] == 1

# ------------------------
# Тест экспоненциального backoff
# ------------------------
@pytest.mark.asyncio
async def test_exponential_backoff(test_server):
    delays = []
    async with AsyncCrawler(
        respect_robots=False,
        max_concurrent=1
    ) as crawler:
        # capture delays
        def capture_delay(exc, attempt, exc_type, delay=None, url=None):
            if delay:
                delays.append(delay)
        crawler.retry_strategy.on_retry = capture_delay

        url = f"http://{test_server.host}:{test_server.port}/503"
        await crawler.fetch_url(url)

    # Проверяем, что каждый следующий delay >= предыдущего (exp backoff)
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i - 1]

# ------------------------
# Тест статистики ошибок
# ------------------------
@pytest.mark.asyncio
async def test_error_stats(test_server):
    async with AsyncCrawler(
        respect_robots=False,
        max_concurrent=1,
        total_timeout=2.0
    ) as crawler:
        urls = [
            f"http://{test_server.host}:{test_server.port}/404",
            f"http://{test_server.host}:{test_server.port}/503",
            f"http://{test_server.host}:{test_server.port}/timeout",
        ]
        for url in urls:
            await crawler.fetch_url(url)

        # Проверяем, что статистика ошибок учитывает все типы
        assert crawler.stats["errors"].get("TransientError", 0) >= 1
        assert crawler.stats["errors"].get("PermanentError", 0) >= 1
