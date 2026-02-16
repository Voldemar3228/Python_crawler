# libraries
import aiohttp
import asyncio
import logging
import time
import re
import random
from urllib.parse import urljoin, urldefrag, urlparse

from crawler.parser import HTMLParser
from crawler.logger import setup_crawler_logger
from crawler.semaphore_manager import SemaphoreManager
from crawler.queue import CrawlerQueue
from crawler.rate_limiter import RateLimiter
from crawler.robots_parser import RobotsParser

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

        # --- Timeout & session ---
        if timeout is None:
            timeout = aiohttp.ClientTimeout(connect=5, sock_read=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, keepalive_timeout=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        # --- Parser ---
        self.parser = HTMLParser()

        # --- Rate limiter ---
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            per_domain=True,
            min_delay=min_delay,
            jitter=jitter,
        )

        # --- Robots.txt ---
        self.robots_parser = RobotsParser()
        self.respect_robots = respect_robots
        self.user_agent = user_agent

        # --- Allowed domains ---
        self.allowed_domains = allowed_domains

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

        # --- Respect robots.txt ---
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

        # --- Wait for rate limiter and crawl-delay ---
        await self.rate_limiter.acquire(domain)
        if crawl_delay > 0:
            await asyncio.sleep(crawl_delay)

        max_attempts = 3
        backoff = 1
        attempt = 0

        while attempt < max_attempts:
            async with self.semaphore_manager.limit(url):
                try:
                    headers = {"User-Agent": self.user_agent}
                    start_req = time.time()
                    async with self.session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        text = await response.text()
                        self.request_times.append(time.time() - start_req)
                        logger.info(f"✅ Success {response.status}: {url}")
                        return text

                except (aiohttp.ClientResponseError, aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"⚠️ Error for {url}: {e}")
                    attempt += 1
                    await asyncio.sleep(backoff + random.random() * 0.5)
                    backoff *= 2
                    self.failed_urls[url] = str(e)
                except Exception as e:
                    logger.exception(f"⚠️ Unexpected error for {url}")
                    self.failed_urls[url] = str(e)
                    return ""
        return ""

    # --- Parse HTML ---
    async def parse_html(self, url: str, html: str) -> dict:
        return await self.parser.parse_html(html, url)

    # --- Process one page ---
    async def _process_url(self, url: str):
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)

        html = await self.fetch_url(url)
        if not html:
            return None

        parsed = await self.parse_html(url, html)
        self.processed_urls[url] = parsed
        return parsed

    # --- Crawl engine ---
    async def crawl(self, start_urls: list[str], max_pages: int = 100, progress_interval: float = 2.0):
        queue = CrawlerQueue()
        results = []

        for url in start_urls:
            if self._is_allowed_url(url):
                await queue.add_url(url, 0)

        async def worker():
            nonlocal results
            while len(self.visited_urls) < max_pages:
                item = await queue.get_next()
                if not item:
                    break
                url, depth = item
                if url in self.visited_urls:
                    continue

                parsed = await self._process_url(url)
                if parsed:
                    results.append(parsed)

                    # --- Safe link traversal ---
                    for link in parsed.get("links", []):
                        if not isinstance(link, str) or not link.strip():
                            continue
                        # if isinstance(link, tuple):
                        #     link = link[0]
                        absolute = urljoin(url, link)
                        absolute, _ = urldefrag(absolute)
                        if self._is_allowed_url(absolute) and depth + 1 <= self.max_depth:
                            await queue.add_url(absolute, depth + 1)

        workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrent)]
        progress_task = asyncio.create_task(self._progress_logger(queue, interval=progress_interval))

        try:
            await asyncio.gather(*workers)
        finally:
            await progress_task
            await self.close()

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
        await self.session.close()
