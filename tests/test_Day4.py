import pytest
import asyncio
from aioresponses import aioresponses
from crawler.async_crawler import AsyncCrawler
from unittest.mock import AsyncMock
from aiohttp import web

BLOCKED_URL = "https://example.com/private"
ALLOWED_URL = "https://example.com/page1"
PAGE2_URL = "https://example.com/page2"
HTML_PAGE = "<html><head></head><body></body></html>"


@pytest.mark.asyncio
async def test_robots_blocked_url():
    crawler = AsyncCrawler(
        max_concurrent=2,
        respect_robots=True,
        max_depth=1,
        user_agent="TestBot/1.0",
    )

    # Замокаем RobotsParser.can_fetch и get_crawl_delay
    crawler.robots_parser.can_fetch = AsyncMock(side_effect=lambda url, ua: False if url == BLOCKED_URL else True)
    crawler.robots_parser.get_crawl_delay = AsyncMock(return_value=0)
    crawler.robots_parser.fetch_robots = AsyncMock(return_value=None)

    with aioresponses() as m:
        m.get(ALLOWED_URL, body=HTML_PAGE, status=200)
        m.get(BLOCKED_URL, body=HTML_PAGE, status=200)

        results = await crawler.crawl([ALLOWED_URL, BLOCKED_URL], max_pages=2)

    # --- Проверки ---
    assert ALLOWED_URL in crawler.processed_urls
    assert BLOCKED_URL in crawler.blocked_urls_by_robots
    print("Blocked URLs:", crawler.blocked_urls_by_robots)


@pytest.mark.asyncio
async def test_rate_limiting_single_domain():
    crawler = AsyncCrawler(
        max_concurrent=2,
        requests_per_second=2,
        respect_robots=True,
        min_delay=0,
        jitter=0,
        max_depth=1,
        user_agent="TestBot/1.0",
    )

    with aioresponses() as m:
        m.get("https://example.com/robots.txt", body="", status=200)
        m.get(ALLOWED_URL, body=HTML_PAGE, status=200)
        m.get(PAGE2_URL, body=HTML_PAGE, status=200)

        results = await crawler.crawl([ALLOWED_URL, PAGE2_URL], max_pages=2)

    # --- Проверки ---
    assert ALLOWED_URL in crawler.processed_urls
    assert PAGE2_URL in crawler.processed_urls
    assert all(url.startswith("https://example.com") for url in crawler.processed_urls)

    # Проверка статистики задержек
    assert all(d >= 0 for d in crawler.request_times)
    print("Request delays:", crawler.request_times)


@pytest.mark.asyncio
async def test_rate_limiting_multiple_domains():
    crawler = AsyncCrawler(max_concurrent=2, requests_per_second=1, min_delay=0, jitter=0)
    with aioresponses() as m:
        m.get("https://example1.com", body=HTML_PAGE, status=200)
        m.get("https://example2.com", body=HTML_PAGE, status=200)

        await crawler.crawl(["https://example1.com", "https://example2.com"], max_pages=2)

    assert "https://example1.com" in crawler.processed_urls
    assert "https://example2.com" in crawler.processed_urls


@pytest.mark.asyncio
async def test_delay_statistics_real_http():

    async def handler(request):
        await asyncio.sleep(0.5)  # имитация задержки
        return web.Response(text=HTML_PAGE, content_type='text/html')

    app = web.Application()
    app.router.add_get('/page1', handler)
    app.router.add_get('/page2', handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8081)
    await site.start()

    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1,
        min_delay=0.5,
        jitter=0,
        max_depth=1
    )

    await crawler.crawl([
        'http://localhost:8081/page1',
        'http://localhost:8081/page2'
    ], max_pages=2)

    assert len(crawler.request_times) >= 2
    avg_delay = sum(crawler.request_times) / len(crawler.request_times)
    assert avg_delay >= 0.5
    print("Request delays:", crawler.request_times)

    await runner.cleanup()
