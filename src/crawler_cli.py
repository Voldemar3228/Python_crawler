import argparse
import asyncio
import os
from time import time
from tqdm import tqdm
from crawler.async_crawler import AsyncCrawler
from crawler.config_loader import ConfigLoader
from storage.json_storage import JSONStorage
from storage.sqlite_storage import SQLiteStorage


async def main():
    parser = argparse.ArgumentParser(description="Advanced Async Web Crawler CLI")
    parser.add_argument("--urls", nargs="+", help="Стартовые URL для краулинга")
    parser.add_argument("--max-pages", type=int, default=100, help="Максимальное количество страниц")
    parser.add_argument("--max-depth", type=int, default=2, help="Максимальная глубина краулинга")
    parser.add_argument("--output", type=str, default="results.json", help="Файл для сохранения результатов")
    parser.add_argument("--config", type=str, help="Путь к YAML/JSON конфигурации")
    parser.add_argument("--respect-robots", action="store_true", help="Соблюдать robots.txt")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Лимит запросов в секунду")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Максимум параллельных задач")

    args = parser.parse_args()

    # --- Загружаем конфиг ---
    if args.config:
        config_loader = ConfigLoader(args.config)
        config = config_loader.config
        start_urls = config.get("start_urls", [])
        max_pages = config.get("max_pages", args.max_pages)
        max_depth = config.get("max_depth", args.max_depth)
        rate_limit = config.get("rate_limit", args.rate_limit)
        max_concurrent = config.get("max_concurrent", args.max_concurrent)
        respect_robots = config.get("respect_robots", args.respect_robots)
        storage_config = config.get("storage", {"type": "json", "path": args.output})
    else:
        start_urls = args.urls or []
        max_pages = args.max_pages
        max_depth = args.max_depth
        rate_limit = args.rate_limit
        max_concurrent = args.max_concurrent
        respect_robots = args.respect_robots
        storage_config = {"type": "json", "path": args.output}

    if not start_urls:
        print("❌ Не указаны стартовые URL. Используйте --urls или конфигурационный файл.")
        return

    # --- Выбираем storage ---
    if storage_config["type"] == "json":
        storage = JSONStorage(storage_config["path"])
    elif storage_config["type"] == "sqlite":
        storage = SQLiteStorage(storage_config["path"])
    else:
        storage = None

    async with AsyncCrawler(
            max_concurrent=max_concurrent,
            max_depth=max_depth,
            respect_robots=respect_robots,
            requests_per_second=rate_limit,
            storage=storage
    ) as crawler:

        print("🚀 Запуск краулинга...")

        # --- Прогресс-бар и мониторинг ---
        start_time = time()
        progress_bar = tqdm(total=max_pages, desc="Pages Crawled", unit="page", dynamic_ncols=True)

        async def crawl_with_progress():
            results = []
            in_progress = set()

            # Перехватываем обработку каждой страницы
            async def track_page(url):
                in_progress.add(url)
                page = await crawler._process_url(url)
                in_progress.remove(url)

                # Обновляем прогресс-бар
                progress_bar.update(1)
                elapsed = time() - start_time
                speed = progress_bar.n / elapsed if elapsed > 0 else 0
                remaining = max_pages - progress_bar.n
                eta = remaining / speed if speed > 0 else 0

                success_count = len([p for p in crawler.processed_urls.values() if p])
                failed_count = len(crawler.failed_urls)
                progress_bar.set_postfix({
                    "Speed": f"{speed:.2f} p/s",
                    "ETA": f"{int(eta)}s",
                    "Active Tasks": len(in_progress),
                    "Success": success_count,
                    "Failed": failed_count
                })
                return page

            # --- Основной краулинг ---
            pages = await crawler.crawl(start_urls=start_urls, max_pages=max_pages)

            # Отслеживаем прогресс каждой страницы
            for page in pages:
                await track_page(page["url"])

            return pages

        results = await crawl_with_progress()
        progress_bar.close()

        print(f"✅ Краулинг завершён. Обработано {len(results)} страниц.")

        # --- Экспорт статистики ---
        crawler.stats_exporter.export_to_json("stats.json")
        crawler.stats_exporter.export_to_html_report("report.html")
        print("📊 Статистика и HTML-отчёт созданы: stats.json, report.html")

        # --- Закрытие storage ---
        if crawler.storage:
            await crawler.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
