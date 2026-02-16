# libraries
import aiohttp
import asyncio
from crawler.parser import HTMLParser

# logging logic
import logging
from crawler.logger import setup_crawler_logger

logger = setup_crawler_logger(level=logging.INFO)

from crawler.semaphore_manager import SemaphoreManager

from crawler.queue import CrawlerQueue
from urllib.parse import urljoin, urldefrag

from urllib.parse import urlparse

import time

import re

# code
class AsyncCrawler:
    # initialization with concurrency constraints / инициализация с ограничением конкурентности
    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: aiohttp.ClientTimeout = None,
        allowed_domains: list[str] = None,
        rate_limit: float = 0,
        include_patterns: list[str] = None,
        exclude_patterns: list[str] = None,
    ):
        self.max_concurrent = max_concurrent

        self.semaphore_manager = SemaphoreManager(
            global_limit=20,
            per_domain_limit=5
        )

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

        self.parser = HTMLParser()

        # --- Управление состоянием URL ---
        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}  # URL -> ошибка
        self.processed_urls: dict[str, dict] = {}  # URL -> результат парсинга

        # --- Ограничение доменов и rate limit ---
        self.allowed_domains = allowed_domains  # список разрешённых доменов, например ['example.com', 'python.org']
        self.rate_limit = rate_limit  # минимальная задержка между запросами к одному домену в секундах
        self._domain_last_access: dict[str, float] = {}  # когда последний раз делался запрос к домену

        # --- Фильтрация URL по паттернам ---
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []

    # checking urls before adding one to the queue / проверка при добавлении ссылок в очередь
    def _is_allowed_domain(self, url: str) -> bool:
        if not self.allowed_domains:
            return True
        domain = urlparse(url).netloc
        return any(domain.endswith(allowed) for allowed in self.allowed_domains)

    # --- Проверка паттернов include/exclude ---
    def _is_allowed_url(self, url: str) -> bool:
        if not self._is_allowed_domain(url):
            return False

        for pattern in self.exclude_patterns:
            if re.search(pattern, url):
                return False

        if self.include_patterns:
            for pattern in self.include_patterns:
                if re.search(pattern, url):
                    return True
            return False  # ни один include не совпал

        return True

    # one page loading / загрузка одной страницы
    async def fetch_url(self, url: str) -> str:
        domain = urlparse(url).netloc

        # --- rate limit ---
        if self.rate_limit > 0:
            last_access = self._domain_last_access.get(domain, 0)
            wait_time = self.rate_limit - (time.time() - last_access)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        self._domain_last_access[domain] = time.time()

        async with self.semaphore_manager.limit(url):

            logger.debug(f"▶️ Start fetching: {url}")

            try:
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

    # ready html parsing
    async def parse_html(self, url: str, html: str) -> dict:
        return await self.parser.parse_html(html, url)

    async def _process_url(self, url: str):
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)

        html = await self.fetch_url(url)

        if html.startswith(("HTTP ERROR", "TIMEOUT ERROR", "NETWORK ERROR", "UNEXPECTED ERROR")):
            self.failed_urls[url] = html
            return None

        parsed = await self.parse_html(url, html)
        self.processed_urls[url] = parsed
        return parsed

    # --- Crawl engine с max_depth, max_pages, фильтрацией и автоматическим добавлением ссылок ---
    async def crawl(
        self,
        start_urls: list[str],
        max_pages: int = 100,
        max_depth: int = 2,
        progress_interval: float = 2.0
    ):
        queue = CrawlerQueue()
        results = []

        # Добавляем стартовые URL с depth=0
        for url in start_urls:
            if self._is_allowed_url(url):
                await queue.add_url(url, priority=0)

        async def worker():
            nonlocal results
            while len(self.visited_urls) < max_pages:
                item = await queue.get_next()
                if not item:
                    return

                url, depth = item  # priority теперь выступает как depth
                if url in self.visited_urls:
                    continue

                parsed = await self._process_url(url)
                if parsed:
                    results.append(parsed)

                    # Ограничение глубины
                    if depth < max_depth:
                        for link in parsed.get("links", []):
                            absolute = urljoin(url, link)
                            absolute, _ = urldefrag(absolute)
                            if absolute not in self.visited_urls and self._is_allowed_url(absolute):
                                await queue.add_url((absolute, depth + 1))

        # Запускаем воркеров
        workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrent)]
        # Запускаем прогресс-логгер
        progress_task = asyncio.create_task(self._progress_logger(queue, interval=progress_interval))

        try:
            await asyncio.gather(*workers)
        finally:
            await progress_task
            await self.close()

        return results

    async def _progress_logger(self, queue: CrawlerQueue, interval: float = 2.0):
        start_time = time.time()
        prev_processed = 0
        while True:
            processed_count = len(self.processed_urls)
            in_queue = queue._queue.qsize()
            failed_count = len(self.failed_urls)
            elapsed = time.time() - start_time
            speed = (processed_count - prev_processed) / interval
            prev_processed = processed_count

            logger.info(
                f"📄 Processed: {processed_count} | "
                f"⏳ In queue: {in_queue} | "
                f"❌ Failed: {failed_count} | "
                f"⚡️ Speed: {speed:.2f} pages/sec"
            )

            if in_queue == 0 and processed_count + failed_count >= len(self.visited_urls):
                break

            await asyncio.sleep(interval)

    async def close(self):
        await self.session.close()
