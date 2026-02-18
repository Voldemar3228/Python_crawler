# src/advanced_crawler.py
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from crawler.async_crawler import AsyncCrawler
from crawler.config_loader import ConfigLoader
from storage.json_storage import JSONStorage
from storage.sqlite_storage import SQLiteStorage
from crawler.logger import setup_crawler_logger


class AdvancedCrawler:
    """
    Финальный интегрированный краулер.
    - Настройка через YAML + CLI override
    - Логирование в консоль + файл с ротацией
    - Прогресс и метрики
    - Сохранение данных
    - Экспорт статистики
    """

    def __init__(self, config_path: str = None, cli_args: dict = None):

        cli_args = cli_args or {}

        # ==========================================================
        # 🔹 1. Загрузка конфигурации
        # ==========================================================
        self.config = {}

        if config_path:
            loader = ConfigLoader(config_path)
            self.config = loader.config or {}

        # ==========================================================
        # 🔹 2. START URLS (CLI имеет приоритет)
        # ==========================================================
        self.start_urls = (
            cli_args.get("start_urls")
            or self.config.get("start_urls")
            or []
        )

        if not self.start_urls:
            raise ValueError("❌ Не указаны стартовые URL.")

        # ==========================================================
        # 🔹 3. MAX PAGES
        # ==========================================================
        self.max_pages = (
            cli_args.get("max_pages")
            or self.config.get("max_pages")
            or 100
        )

        # ==========================================================
        # 🔹 4. CRAWLER SETTINGS
        # ==========================================================
        crawler_cfg = self.config.get("crawler", {})

        self.max_concurrent = (
            cli_args.get("max_concurrent")
            or crawler_cfg.get("max_concurrent", 5)
        )

        self.max_depth = (
            cli_args.get("max_depth")
            or crawler_cfg.get("max_depth", 2)
        )

        self.rate_limit = (
            cli_args.get("rate_limit")
            or crawler_cfg.get("rate_limit", 1.0)
        )

        self.respect_robots = (
            cli_args.get("respect_robots")
            if cli_args.get("respect_robots") is not None
            else crawler_cfg.get("respect_robots", True)
        )

        self.include_patterns = crawler_cfg.get("include_patterns", [])
        self.exclude_patterns = crawler_cfg.get("exclude_patterns", [])
        self.allowed_domains = crawler_cfg.get("allowed_domains", [])

        # ==========================================================
        # 🔹 5. STORAGE
        # ==========================================================
        storage_cfg = self.config.get(
            "storage",
            {"type": "json", "path": "results.json"}
        )

        if storage_cfg["type"] == "json":
            self.storage = JSONStorage(storage_cfg["path"])
        elif storage_cfg["type"] == "sqlite":
            self.storage = SQLiteStorage(storage_cfg["path"])
        else:
            self.storage = None

        # ==========================================================
        # 🔹 6. LOGGING (консоль + файл)
        # ==========================================================
        log_file = Path(
            cli_args.get("log_file")
            or self.config.get("log_file")
            or "crawler.log"
        )

        log_level = getattr(
            logging,
            self.config.get("log_level", "INFO").upper()
        )

        self.logger = setup_crawler_logger(level=log_level)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,
            backupCount=5,
            encoding="utf-8"  # ← ВАЖНО
        )

        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        self.logger.addHandler(file_handler)

        # ==========================================================
        # 🔹 7. AsyncCrawler
        # ==========================================================
        self.crawler = AsyncCrawler(
            max_concurrent=self.max_concurrent,
            max_depth=self.max_depth,
            respect_robots=self.respect_robots,
            requests_per_second=self.rate_limit,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            allowed_domains=self.allowed_domains,
            storage=self.storage,
        )

    # ==============================================================
    # 🔹 RUN
    # ==============================================================

    async def run(self):

        start_time = datetime.utcnow()
        self.logger.info(
            f"🚀 AdvancedCrawler started | URLs: {len(self.start_urls)}"
        )

        try:
            async with self.crawler:
                results = await self.crawler.crawl(
                    start_urls=self.start_urls,
                    max_pages=self.max_pages
                )

        except KeyboardInterrupt:
            self.logger.warning("🛑 Graceful shutdown (Ctrl+C)")
            await self.crawler.close()
            results = list(self.crawler.processed_urls.values())

        except Exception as e:
            self.logger.exception(f"❌ Unexpected error: {e}")
            await self.crawler.close()
            results = list(self.crawler.processed_urls.values())

        # ==========================================================
        # 🔹 EXPORT
        # ==========================================================
        self.crawler.stats_exporter.export_to_json("stats.json")
        self.crawler.stats_exporter.export_to_html_report("report.html")

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        self.logger.info(
            f"✅ Finished | Pages: {len(results)} | Time: {elapsed:.2f}s"
        )

        return results
