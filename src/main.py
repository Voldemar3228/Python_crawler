import asyncio
from crawler.async_crawler import AsyncCrawler
from crawler.config_loader import ConfigLoader
from storage.json_storage import JSONStorage
from storage.csv_storage import CSVStorage
from storage.sqlite_storage import SQLiteStorage


async def main():
    # 🔹 Загружаем конфигурацию
    config = ConfigLoader("config.yaml")
    crawler_settings = config.get_crawler_settings()
    start_urls = config.get_start_urls()
    filters = config.get_filters()
    storage_config = config.get_storage_settings()

    # 🔹 Настраиваем хранилища
    storages = []

    if storage_config.get("json", {}).get("enabled"):
        s = storage_config["json"]
        storages.append(JSONStorage(s["filename"], batch_size=s.get("batch_size", 50)))

    if storage_config.get("csv", {}).get("enabled"):
        s = storage_config["csv"]
        storages.append(CSVStorage(s["filename"], delimiter=s.get("delimiter", ",")))

    if storage_config.get("sqlite", {}).get("enabled"):
        s = storage_config["sqlite"]
        sqlite_store = SQLiteStorage(s["db_path"], batch_size=s.get("batch_size", 50))
        await sqlite_store.init_db()
        storages.append(sqlite_store)

    # 🔹 Объединяем в один объект (пример: используем JSONStorage, можно добавить MultiStorage)
    # Для простоты берем первое хранилище
    storage = storages[0] if storages else None

    # 🔹 Инициализация краулера
    crawler = AsyncCrawler(
        max_concurrent=crawler_settings.get("max_concurrent", 5),
        max_depth=crawler_settings.get("max_depth", 2),
        include_patterns=filters.get("include_patterns"),
        exclude_patterns=filters.get("exclude_patterns"),
        requests_per_second=crawler_settings.get("requests_per_second", 1.0),
        respect_robots=crawler_settings.get("respect_robots", True),
        user_agent=crawler_settings.get("user_agent", "AdvancedCrawler/1.0"),
        storage=storage
    )

    # 🔹 Краулинг
    async with crawler:
        await crawler.crawl(start_urls, max_pages=crawler_settings.get("max_pages", 100))

        # 🔹 Экспорт статистики
        crawler.stats_exporter.export_to_json("stats.json")
        crawler.stats_exporter.export_to_html_report("report.html")

        # 🔹 Закрытие хранилища
        if storage:
            await storage.close()

asyncio.run(main())
