import logging

import pytest
import asyncio
from aiohttp import web
from src.crawler.async_crawler import AsyncCrawler
from crawler.logger import setup_crawler_logger

# --- Фикстура логгера ---
@pytest.fixture(scope="session", autouse=True)
def crawler_logger():
    # return setup_crawler_logger(level=10)  # DEBUG
    setup_crawler_logger(level=logging.DEBUG)

# --- Асинхронный тестовый сервер ---
@pytest.fixture
async def test_server(unused_tcp_port):
    """
    Запускает минимальный aiohttp сервер для тестов AsyncCrawler.
    """
    async def handle(request):
        path = request.path
        html = f"""
        <html>
            <head><title>Test {path}</title></head>
            <body>
                <h1>Hello {path}</h1>
                <a href="/link1">Link1</a>
                <a href="/link2">Link2</a>
            </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    app = web.Application()
    app.router.add_get("/{tail:.*}", handle)

    port = unused_tcp_port
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()

    yield f"http://localhost:{port}"  # возвращаем базовый URL для тестов

    await runner.cleanup()

# --- Фикстура AsyncCrawler ---
@pytest.fixture
async def async_crawler():
    crawler = AsyncCrawler(max_concurrent=5)
    yield crawler
    await crawler.close()
