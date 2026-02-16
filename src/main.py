import asyncio
from src.crawler.async_crawler import AsyncCrawler

async def main():
    # Пример сайта с robots.txt (публичный)
    start_urls = [
        "https://www.python.org/",
    ]

    crawler = AsyncCrawler(
        max_concurrent=3,
        max_depth=1,
        requests_per_second=0.5,  # ограничение 2 сек на запрос
        respect_robots=True,
        min_delay=1.0,
        jitter=0.5,
        user_agent="DemoCrawler/1.0",
        allowed_domains=["python.org"],  # ограничение доменов
    )

    results = await crawler.crawl(start_urls=start_urls, max_pages=10)

    print("\n=== Crawl finished ===")
    print(f"Processed pages: {len(crawler.processed_urls)}")
    print(f"Failed pages: {len(crawler.failed_urls)}")
    print(f"Blocked by robots.txt: {len(crawler.blocked_urls_by_robots)}")
    if crawler.request_times:
        avg_delay = sum(crawler.request_times)/len(crawler.request_times)
        print(f"Average request delay: {avg_delay:.2f} sec")
    else:
        print("No requests were made.")

    print("\nProcessed URLs:")
    for url in crawler.processed_urls:
        print("✅", url)

    print("\nBlocked URLs:")
    for url in crawler.blocked_urls_by_robots:
        print("🚫", url)

    print("\nFailed URLs:")
    for url, reason in crawler.failed_urls.items():
        print("❌", url, "| reason:", reason)

if __name__ == "__main__":
    asyncio.run(main())
