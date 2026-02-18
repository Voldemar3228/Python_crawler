# demo.py
import asyncio
import json
import csv
import aiosqlite
from datetime import datetime

from crawler.async_crawler import AsyncCrawler
from storage.json_storage import JSONStorage
from storage.csv_storage import CSVStorage
from storage.sqlite_storage import SQLiteStorage


async def demo():
    # -----------------------
    # 1️⃣ Создаём хранилища
    # -----------------------
    json_storage = JSONStorage("demo_results.json", batch_size=10)
    csv_storage = CSVStorage("demo_results.csv", batch_size=10)
    sqlite_storage = SQLiteStorage("demo_results.db", batch_size=10)
    await sqlite_storage.init_db()

    # -----------------------
    # 2️⃣ Краулер с одновременным сохранением
    # -----------------------
    async with AsyncCrawler(
        max_concurrent=3,
        max_depth=1,
        storage=None  # будем сохранять вручную после парсинга
    ) as crawler:

        # Функция для сохранения во все три хранилища
        async def save_all(data):
            await asyncio.gather(
                json_storage.save(data),
                csv_storage.save(data),
                sqlite_storage.save(data)
            )

        start_urls = ["https://example.com"]
        results = []

        # Оборачиваем оригинальный _process_url, чтобы добавить сохранение
        original_process = crawler._process_url

        async def _process_and_save(url):
            standardized = await original_process(url)
            if standardized:
                await save_all(standardized)
                results.append(standardized)
            return standardized

        crawler._process_url = _process_and_save  # временно заменяем метод

        # Запускаем краулер
        await crawler.crawl(start_urls, max_pages=5)

    # -----------------------
    # 3️⃣ Закрываем хранилища
    # -----------------------
    await asyncio.gather(
        json_storage.close(),
        csv_storage.close(),
        sqlite_storage.close()
    )

    # -----------------------
    # 4️⃣ Статистика
    # -----------------------
    print("🔹 Statistics:")
    print(f"Pages crawled: {len(results)}")
    print(f"JSON pages: {len(results)}")
    print(f"CSV pages: {len(results)}")
    print(f"SQLite pages: {len(results)}\n")

    # -----------------------
    # 5️⃣ Чтение данных
    # -----------------------
    # JSON
    print("Reading first 3 pages from JSON:")
    with open("demo_results.json", "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            data = json.loads(line)
            print(f"{i+1}. {data['url']} - {data['title']}")

    # CSV
    print("\nReading first 3 pages from CSV:")
    with open("demo_results.csv", "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            print(f"{i+1}. {row['url']} - {row['title']}")

    # SQLite
    print("\nReading first 3 pages from SQLite:")
    async with aiosqlite.connect("demo_results.db") as db:
        async with db.execute("SELECT url, title FROM pages LIMIT 3") as cursor:
            i = 0
            async for row in cursor:
                i += 1
                print(f"{i}. {row[0]} - {row[1]}")


if __name__ == "__main__":
    asyncio.run(demo())
