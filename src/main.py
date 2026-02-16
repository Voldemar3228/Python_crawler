import asyncio
import logging
from urllib.parse import urljoin, urldefrag

from src.crawler.async_crawler import AsyncCrawler
from crawler.logger import setup_crawler_logger
from crawler.queue import CrawlerQueue
from utils import save_json

logger = setup_crawler_logger(level=logging.INFO)

URLS = [
    "https://example.com",
    "https://www.python.org",
    "https://www.wikipedia.org",
]

MAX_PAGES = 40
MAX_DEPTH = 1


async def worker(queue: CrawlerQueue, crawler: AsyncCrawler, stop_event: asyncio.Event):
    while not stop_event.is_set():

        # Ограничение по количеству страниц
        if len(crawler.visited_urls) >= MAX_PAGES:
            stop_event.set()
            break

        item = await queue.get_next()

        if not item:
            # если очередь пуста — завершаем
            stop_event.set()
            break

        url, depth = item

        if url in crawler.visited_urls:
            continue

        parsed = await crawler._process_url(url)

        if parsed and depth < MAX_DEPTH:
            for link in parsed.get("links", []):
                absolute = urljoin(url, link)
                absolute, _ = urldefrag(absolute)

                if crawler._is_allowed_url(absolute):
                    await queue.add_url(absolute, depth + 1)


async def progress_logger(crawler, queue, stop_event, interval=2.0):
    while not stop_event.is_set():
        processed = len(crawler.processed_urls)
        failed = len(crawler.failed_urls)
        in_queue = queue._queue.qsize()

        logger.info(
            f"📄 Processed: {processed} | "
            f"⏳ In queue: {in_queue} | "
            f"❌ Failed: {failed}"
        )

        await asyncio.sleep(interval)


async def main():

    crawler = AsyncCrawler(
        max_concurrent=5,
        allowed_domains=["example.com", "python.org", "wikipedia.org"],
    )

    queue = CrawlerQueue()
    stop_event = asyncio.Event()

    # стартовые URL
    for url in URLS:
        if crawler._is_allowed_url(url):
            await queue.add_url(url, 0)

    workers = [
        asyncio.create_task(worker(queue, crawler, stop_event))
        for _ in range(crawler.max_concurrent)
    ]

    progress_task = asyncio.create_task(
        progress_logger(crawler, queue, stop_event)
    )

    try:
        await asyncio.gather(*workers)
    finally:
        stop_event.set()
        await progress_task
        await crawler.close()

    parsed_pages = list(crawler.processed_urls.values())
    save_json("parsed_pages.json", parsed_pages)

    logger.info("✅ Crawling finished")
    logger.info(f"Total visited: {len(crawler.visited_urls)}")
    logger.info(f"Total processed: {len(crawler.processed_urls)}")
    logger.info(f"Total failed: {len(crawler.failed_urls)}")


if __name__ == "__main__":
    asyncio.run(main())
