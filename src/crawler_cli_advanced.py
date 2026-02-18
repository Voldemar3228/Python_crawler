# src/crawler_cli_advanced.py
import argparse
import asyncio
from crawler.advanced_crawler import AdvancedCrawler

async def main():
    parser = argparse.ArgumentParser(description="Advanced Async Web Crawler CLI (AdvancedCrawler)")
    parser.add_argument("--config", type=str, help="Путь к YAML конфигурации")
    parser.add_argument("--urls", nargs="+", help="Стартовые URL для краулинга (CLI перекрывает конфиг)")
    parser.add_argument("--max-pages", type=int, help="Максимальное количество страниц")
    parser.add_argument("--max-depth", type=int, help="Максимальная глубина краулинга")
    parser.add_argument("--rate-limit", type=float, help="Лимит запросов в секунду")
    parser.add_argument("--respect-robots", action="store_true", help="Соблюдать robots.txt")
    parser.add_argument("--log-file", type=str, help="Файл логов (CLI перекрывает конфиг)")

    args = parser.parse_args()

    # Преобразуем CLI args в словарь для AdvancedCrawler
    cli_args = {
        "start_urls": args.urls,
        "max_pages": args.max_pages,
        "crawler": {
            "max_depth": args.max_depth,
            "rate_limit": args.rate_limit,
            "respect_robots": args.respect_robots,
        },
        "log_file": args.log_file,
    }

    # Создаем AdvancedCrawler
    crawler = AdvancedCrawler(config_path=args.config, cli_args=cli_args)

    # Запускаем краулинг
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
