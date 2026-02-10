import asyncio
import pytest
from aiohttp import web

from crawler.logger import setup_crawler_logger
import crawler.crawler as crawler_module


@pytest.fixture(scope="session", autouse=True)
def crawler_logger():
    """
    Configuring a color logger for AsyncCrawler.
    Shows only manual logs (not system aiohttp/Python ones).
    /
    Настраивает цветной логгер для AsyncCrawler.
    Будут выводиться только ручные логи (не системные aiohttp/Python).
    """
    logger = setup_crawler_logger()
    crawler_module.logger = logger  # replacing the logger in the module
    return logger


@pytest.fixture
async def test_server(unused_tcp_port):
    """
    Asynchronous test server aiohttp for AsyncCrawler tests
    /
    Асинхронный тестовый сервер aiohttp для тестов AsyncCrawler.
    """
    app = web.Application()

    async def ok(request):
        return web.Response(text="OK")

    async def ok2(request):
        return web.Response(text="OK2")

    async def slow(request):
        await asyncio.sleep(2)
        return web.Response(text="SLOW")

    async def not_found(request):
        return web.Response(status=404, text="Not Found")

    app.router.add_get("/ok", ok)
    app.router.add_get("/ok2", ok2)
    app.router.add_get("/slow", slow)
    app.router.add_get("/not-exist", not_found)

    port = unused_tcp_port
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()

    yield f"http://localhost:{port}"

    await runner.cleanup()
