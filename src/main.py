import asyncio
from src.crawler.async_crawler import AsyncCrawler
from crawler.logger import setup_crawler_logger
from utils import save_json, compute_page_stats, compute_overall_stats
import logging

logger = setup_crawler_logger(level=logging.INFO)

# --- Список страниц для теста ---
URLS = [
    "https://example.com",
    "https://www.python.org",
    "https://www.wikipedia.org",
]


# --- Основная асинхронная функция ---
async def main():
    crawler = AsyncCrawler(max_concurrent=5)

    logger.info("▶️ Start fetching and parsing pages...")

    # 1️⃣ Загружаем страницы параллельно
    results = await crawler.fetch_urls(URLS)

    parsed_pages = []
    for url, html in results:
        if html.startswith(("HTTP ERROR", "TIMEOUT ERROR", "NETWORK ERROR", "UNEXPECTED ERROR")):
            logger.warning(f"❌ Skipping {url} due to fetch error")
            continue

        # 2️⃣ Парсим страницу
        parsed = await crawler.fetch_and_parse(url)
        parsed_pages.append(parsed)

    # 3️⃣ Сохраняем результаты в JSON
    save_json("parsed_pages.json", parsed_pages)
    logger.info("✅ Parsed pages saved to parsed_pages.json")

    # 4️⃣ Выводим статистику по каждой странице
    logger.info("📊 Individual page stats:")
    for page in parsed_pages:
        stats = compute_page_stats(page)
        logger.info(stats)

    # 5️⃣ Общая статистика
    overall_stats = compute_overall_stats(parsed_pages)
    logger.info("📈 Overall stats:")
    logger.info(overall_stats)

    await crawler.close()


# --- Запуск ---
if __name__ == "__main__":
    asyncio.run(main())
