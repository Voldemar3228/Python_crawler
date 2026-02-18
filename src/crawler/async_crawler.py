# libraries
import aiohttp
import asyncio
import logging
import time
import re
import random
from urllib.parse import urljoin, urldefrag, urlparse
import async_timeout
from datetime import datetime

from crawler.parser import HTMLParser
from crawler.logger import setup_crawler_logger
from crawler.semaphore_manager import SemaphoreManager
from crawler.queue import CrawlerQueue
from crawler.rate_limiter import RateLimiter
from crawler.robots_parser import RobotsParser
from crawler.retry_strategy import RetryStrategy
from crawler.errors import (
    TransientError,
    PermanentError,
    NetworkError,
    ParseError,
)
from crawler.circuit_breaker import CircuitBreaker
from storage.base import DataStorage

logger = setup_crawler_logger(level=logging.INFO)


class AsyncCrawler:
    def __init__(
            self,
            max_concurrent: int = 5,
            allowed_domains: list[str] | None = None,
            include_patterns: list[str] | None = None,
            exclude_patterns: list[str] | None = None,
            max_depth: int = 2,
            requests_per_second: float = 1.0,
            respect_robots: bool = True,
            min_delay: float = 0.0,
            jitter: float = 0.0,
            user_agent: str = "AsyncCrawler/1.0",
            timeout: aiohttp.ClientTimeout = None,
            connect_timeout=5,
            read_timeout=10,
            total_timeout=15,
            storage: DataStorage | None = None
    ):
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth

        # --- URL filters ---
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []

        # --- Crawler state ---
        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}
        self.processed_urls: dict[str, dict] = {}
        self.blocked_urls_by_robots: set[str] = set()
        self.request_times: list[float] = []

        # --- Semaphore / concurrency ---
        self.semaphore_manager = SemaphoreManager(global_limit=20, per_domain_limit=5)

        # # --- Timeout & session ---
        # if timeout is None:
        #     timeout = aiohttp.ClientTimeout(connect=5, sock_read=10)
        # connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, keepalive_timeout=30)
        # self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        # --- Parser ---
        self.parser = HTMLParser()

        # --- Rate limiter ---
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            per_domain=True,
            min_delay=min_delay,
            jitter=jitter,
        )

        self.storage = storage

        # --- Robots.txt ---
        self.robots_parser = RobotsParser()
        self.respect_robots = respect_robots
        self.user_agent = user_agent

        # --- Allowed domains ---
        self.allowed_domains = allowed_domains

        def _on_retry(exc, attempt, exc_type):
            logger.warning(f"🔁 Retry {attempt} for {exc_type.__name__}: {exc}")

        # --- Retry strategy ---
        self.retry_strategy = RetryStrategy(
            strategy={
                TransientError: {
                    "max_retries": 3,
                    "backoff_factor": 2.0,
                    "timeout_factor": 1.5  # каждый retry увеличивает таймаут на 50%
                },
                NetworkError: {
                    "max_retries": 2,
                    "backoff_factor": 1.5,
                    "timeout_factor": 1.2
                }
                # PermanentError не указан → не ретраится
            },
            on_retry=_on_retry,
        )

        # stats
        self.stats = {
            "errors": {},  # количество ошибок по типам, например: {"TransientError": 3}
            "success_retries": 0,  # сколько успешных повторов было
            "retry_times": [],  # время выполнения retry
            "permanent_failed_urls": {}  # список URL с PermanentError
        }

        # Timeouts logic
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.total_timeout = total_timeout
        self.session = None  # aiohttp session создаём в __aenter__

        # for CircuitBreaker
        self.circuit_breaker = CircuitBreaker(
            max_errors=5,
            window=60.0,
            reset_timeout=30.0
        )

    # async def _do_request(self, url: str) -> str:
    async def _do_request(self, url: str, **kwargs) -> str:
        """
        Выполняет HTTP GET с обработкой transient/permanent ошибок.
        Устойчиво к разрывам соединения и проблемам с текстом.
        """
        if not self.session:
            raise RuntimeError("Session is not initialized. Use 'async with AsyncCrawler()'")

        headers = {"User-Agent": self.user_agent}
        start_req = time.time()
        timeout = self.total_timeout

        try:
            async with async_timeout.timeout(timeout):
                async with self.session.get(url, headers=headers) as response:
                    # --- классификация по статусу ---
                    if response.status in (429, 503):
                        raise TransientError(f"HTTP {response.status}", status=response.status)
                    if response.status == 500:
                        raise TransientError("HTTP 500 Server Error", status=500)
                    if response.status in (401, 403, 404):
                        raise PermanentError(f"HTTP {response.status}", status=response.status)

                    response.raise_for_status()

                    # --- безопасное чтение тела ---
                    try:
                        content = await response.read()  # читаем как bytes
                        text = content.decode("utf-8", errors="replace")  # безопасное декодирование
                    except Exception as e:
                        raise TransientError(f"Failed to read/parse response: {e}") from e

                    self.request_times.append(time.time() - start_req)
                    logger.info(f"✅ Success {response.status}: {url}")
                    return text

        except PermanentError:
            # фиксируем PermanentError, чтобы не превращать в TransientError
            raise

        except asyncio.TimeoutError as e:
            raise TransientError("Timeout") from e
        except aiohttp.ClientConnectorError as e:
            raise NetworkError("Connection error") from e
        except aiohttp.ServerDisconnectedError as e:
            # сервер разорвал соединение
            raise TransientError("Server disconnected") from e
        except aiohttp.ClientError as e:
            raise TransientError(f"Client error: {e}") from e

    # async context manager
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(
            total=self.total_timeout,
            connect=self.connect_timeout,
            sock_read=self.read_timeout
        )
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, keepalive_timeout=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    # --- Domain filter ---
    def _is_allowed_domain(self, url: str) -> bool:
        if not self.allowed_domains:
            return True
        domain = urlparse(url).netloc
        return any(domain.endswith(a) for a in self.allowed_domains)

    # --- URL filter ---
    def _is_allowed_url(self, url: str) -> bool:
        if not self._is_allowed_domain(url):
            return False
        for pattern in self.exclude_patterns:
            if re.search(pattern, url):
                return False
        if self.include_patterns:
            return any(re.search(p, url) for p in self.include_patterns)
        return True

    # --- Fetch one page ---
    async def fetch_url(self, url: str) -> str:
        domain = urlparse(url).netloc

        # --- Circuit breaker ---
        if self.circuit_breaker.is_blocked(domain):
            remaining = self.circuit_breaker.get_remaining_block(domain)
            logger.warning(f"🚫 Domain {domain} is temporarily blocked ({remaining:.1f}s remaining)")
            self.failed_urls[url] = f"Blocked by circuit breaker ({remaining:.1f}s)"
            return ""

        # --- robots.txt + rate limiter ---
        crawl_delay = 0
        if self.respect_robots:
            await self.robots_parser.fetch_robots(domain)
            allowed = await self.robots_parser.can_fetch(url, self.user_agent)
            if not allowed:
                logger.info(f"🚫 Blocked by robots.txt: {url}")
                self.failed_urls[url] = "Blocked by robots.txt"
                self.blocked_urls_by_robots.add(url)
                return ""
            crawl_delay = await self.robots_parser.get_crawl_delay(self.user_agent) or 0

        await self.rate_limiter.acquire(domain)
        if crawl_delay > 0:
            await asyncio.sleep(crawl_delay)

        # --- функция для фиксации ошибок ---
        def record_error_stats(exc):
            name = type(exc).__name__
            self.stats["errors"][name] = self.stats["errors"].get(name, 0) + 1
            self.failed_urls[url] = str(exc)

        # --- Callback для retry ---
        def on_retry(exc, attempt, exc_type, delay=None, url=url):
            name = exc_type.__name__
            self.stats["errors"][name] = self.stats["errors"].get(name, 0) + 1

            delay_str = f"{delay:.2f}s" if delay else "-"
            logger.warning(f"🏷️ {name} | 🔗 {url} | 🔢 Attempt {attempt} | ⏰ Next try in {delay_str} | 🎯 Retrying")

            if attempt > 1:
                self.stats["success_retries"] += 1
            if delay:
                self.stats["retry_times"].append(delay)

            self.failed_urls[url] = str(exc)

        # self.retry_strategy.on_retry = on_retry

        # --- Semaphore + retry ---
        async with self.semaphore_manager.limit(url):
            try:
                result = await self.retry_strategy.execute_with_retry(
                    self._do_request,
                    url=url,
                    on_retry=on_retry
                )

                logger.info(f"🎯 Success | 🔗 {url}")
                return result

            except PermanentError as e:
                record_error_stats(e)
                logger.error(f"🚫 Permanent failure | 🔗 {url} | Reason: {str(e)}")
                return ""

            except Exception as e:
                record_error_stats(e)
                logger.exception(f"❌ Failed after retries {url}: {e}")
                self.circuit_breaker.record_error(domain)
                return ""

    # --- Parse HTML ---
    async def parse_html(self, url: str, html: str) -> dict:
        try:
            return await self.parser.parse_html(html, url)
        except Exception as e:
            logger.exception(f"Parse error for {url}")
            raise ParseError(str(e)) from e

    # --- Process one page ---
    async def _process_url(self, url: str):
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)

        html = await self.fetch_url(url)
        if not html:
            return None

        parsed = await self.parse_html(url, html)

        # 🔹 Стандартизация структуры данных
        standardized = {
            "url": url,
            "title": parsed.get("title", ""),
            "text": parsed.get("text", ""),
            "links": parsed.get("links", []),
            "metadata": parsed.get("metadata", {}),
            "crawled_at": datetime.utcnow(),
            "status_code": parsed.get("status_code", 200),
            "content_type": parsed.get("content_type", "text/html")
        }

        self.processed_urls[url] = standardized
        # 🔹 Добавляем сохранение данных через retry
        if self.storage:
            await self._save_with_retry(standardized)

        return standardized

    async def _save_with_retry(self, data, retries=3, delay=1):
        """
        Сохраняет данные через storage с повторными попытками при ошибках.
        """
        for attempt in range(1, retries + 1):
            try:
                await self.storage.save(data)
                return
            except Exception as e:
                logger.warning(f"Save attempt {attempt} failed for {data['url']}: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to save after {retries} attempts: {data['url']}")

    # --- Crawl engine ---
    async def crawl(self, start_urls: list[str], max_pages: int = 100, progress_interval: float = 2.0):
        queue = CrawlerQueue()
        results = []

        for url in start_urls:
            if self._is_allowed_url(url):
                await queue.add_url(url, 0)

        async def worker():
            nonlocal results

            while True:
                url, depth = await queue.get_next()

                try:
                    if url in self.visited_urls:
                        continue

                    parsed = await self._process_url(url)
                    if parsed:
                        results.append(parsed)

                        for link in parsed.get("links", []):
                            if not isinstance(link, str) or not link.strip():
                                continue

                            absolute = urljoin(url, link)
                            absolute, _ = urldefrag(absolute)

                            if (
                                    self._is_allowed_url(absolute)
                                    and depth + 1 <= self.max_depth
                                    and len(self.visited_urls) < max_pages
                            ):
                                await queue.add_url(absolute, depth + 1)

                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrent)]
        progress_task = asyncio.create_task(self._progress_logger(queue, interval=progress_interval))

        try:
            await queue.join()
        finally:
            for w in workers:
                w.cancel()

            await asyncio.gather(*workers, return_exceptions=True)
            await progress_task

        return results

    # --- Progress logger ---
    async def _progress_logger(self, queue: CrawlerQueue, interval: float = 2.0):
        prev_count = 0
        while True:
            processed_count = len(self.processed_urls)
            failed_count = len(self.failed_urls)
            blocked_count = len(self.blocked_urls_by_robots)
            in_queue = queue._queue.qsize()

            # скорость и средняя задержка
            speed = (processed_count - prev_count) / interval
            prev_count = processed_count
            avg_delay = sum(self.request_times) / len(self.request_times) if self.request_times else 0

            logger.info(
                f"📄 Processed: {processed_count} | "
                f"⏳ In queue: {in_queue} | "
                f"❌ Failed: {failed_count} | "
                f"🚫 Blocked: {blocked_count} | "
                f"⚡️ Speed: {speed:.2f} pages/sec | "
                f"⏱️ Avg delay: {avg_delay:.2f}s"
            )

            # если очередь пуста И все воркеры закончили, то выходим
            if in_queue == 0:
                # даём время воркерам проверить последние URL
                await asyncio.sleep(interval)
                in_queue_after_sleep = queue._queue.qsize()
                if in_queue_after_sleep == 0:
                    break

            await asyncio.sleep(interval)

    # --- Close session ---
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

        # 🔹 Закрытие storage
        if self.storage:
            try:
                await self.storage.close()
            except Exception as e:
                logger.error(f"Failed to close storage: {e}")
