# libraries
import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

# code
class AsyncCrawler:
    # initialization with concurrency constraints / инициализация с ограничением конкурентности
    def __init__(self, max_concurrent: int = 10, timeout: aiohttp.ClientTimeout = None):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # Timeouts: connect/read
        if timeout is None:
            timeout = aiohttp.ClientTimeout(
                connect=5,  # TCP connection establishment timeout / таймаут установки TCP-соединения
                sock_read=10  # response read timeout / таймаут чтения ответа
            )

        # Connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,  # simultaneous connection count / всего одновременных соединений
            limit_per_host=10,  # connection count per host/ на один хост
            keepalive_timeout=30
        )

        # Client session creation
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )

        pass

    # one page loading / загрузка одной страницы
    async def fetch_url(self, url: str) -> str:
        async with self.semaphore:
            try:

                logger.debug(f"▶️ Start fetching: {url}")

                async with self.session.get(url) as response:
                    # check for exceptions / проверка на исключения: 2хх oк, 4хх исключение
                    response.raise_for_status()
                    text = await response.text()

                    logger.info(f"✅ Success {response.status}: {url}")
                    return text

            # HTTP errors / HTTP ошибки (404, 500, ...)
            except aiohttp.ClientResponseError as e:
                logger.warning(f"⚠️ HTTP error {e.status} for {url}")
                return f"HTTP ERROR {e.status}: {e.message}"
            # timeout error / ошибка таймаута
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Timeout error for {url}")
                return f"TIMEOUT ERROR"
            # network errors / сетевые ошибки
            except aiohttp.ClientError as e:
                logger.error(f"⚠️ Network error for {url}: {e}")
                return f"NETWORK ERROR: {e}"
            # others / остальное
            except Exception as e:
                logger.exception(f"⚠️ Unexpected error for {url}")
                return f"UNEXPECTED ERROR: {e}"


    # URL list parallel loading / параллельная загрузка списка URL
    # async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
    async def fetch_urls(self, urls: list[str]) -> list[tuple[str, str]]:
        # nested asynchronous function / вложенная асинхронная функция
        async def _fetch(url: str):
            result = await self.fetch_url(url)
            return url, result

        # asynchronous parallelism
        tasks = [asyncio.create_task(_fetch(url)) for url in urls]
        results = await asyncio.gather(*tasks)

        # return dict(results)
        return results

    # session closing / закрытие сессии
    async def close(self):
        await self.session.close()
