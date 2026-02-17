# main.py
import asyncio
import json
from aiohttp import web
from crawler.async_crawler import AsyncCrawler
from crawler.errors import TransientError, PermanentError

# --- 1️⃣ Локальный сервер с разными статусами ---
async def handler_200(request):
    return web.Response(text="✅ OK", status=200)

async def handler_500(request):
    return web.Response(text="⚠️ Server Error", status=500)

async def handler_503(request):
    return web.Response(text="⚠️ Service Unavailable", status=503)

async def handler_404(request):
    return web.Response(text="❌ Not Found", status=404)

def create_test_server():
    app = web.Application()
    app.router.add_get("/200", handler_200)
    app.router.add_get("/500", handler_500)
    app.router.add_get("/503", handler_503)
    app.router.add_get("/404", handler_404)
    runner = web.AppRunner(app)
    return runner

# --- 2️⃣ Асинхронная функция main ---
async def main():
    # --- Стартуем локальный сервер на 8080 ---
    runner = create_test_server()
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    print("🌐 Test server running at http://localhost:8080")

    # --- URL для теста ---
    test_urls = [
        "http://localhost:8080/200",  # успех
        "http://localhost:8080/500",  # transient → retry
        "http://localhost:8080/503",  # transient → retry
        "http://localhost:8080/404",  # permanent → no retry
    ]

    # --- Создаём и запускаем crawler ---
    async with AsyncCrawler(
        max_concurrent=3,
        max_depth=1,
        respect_robots=False  # чтобы локальный сервер не мешал robots.txt
    ) as crawler:

        print("\n🚀 Starting crawl...\n")
        results = await crawler.crawl(test_urls, max_pages=10)

        print("\n✅ Crawl finished\n")

        # --- Статистика ---
        print("📊 ===== Statistics =====")
        print("Processed URLs:", len(crawler.processed_urls))
        print("Failed URLs:", len(crawler.failed_urls))
        print("Errors by type:", crawler.stats["errors"])
        print("Successful retries:", crawler.stats["success_retries"])

        if crawler.stats["retry_times"]:
            avg_retry = sum(crawler.stats["retry_times"]) / len(crawler.stats["retry_times"])
        else:
            avg_retry = 0

        print(f"Average retry delay: {avg_retry:.2f}s")

        # --- Сохраняем отчёт ---
        report = {
            "processed_urls": list(crawler.processed_urls.keys()),
            "failed_urls": crawler.failed_urls,
            "error_stats": crawler.stats,
        }

        with open("crawler_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        print("\n📄 Report saved to crawler_report.json")

    # --- Выключаем сервер ---
    await runner.cleanup()
    print("🛑 Test server stopped.")

# --- 3️⃣ Запуск ---
if __name__ == "__main__":
    asyncio.run(main())
