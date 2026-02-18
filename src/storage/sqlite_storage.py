# crawler/storage/sqlite_storage.py
from .base import DataStorage
import aiosqlite
import json
from datetime import datetime
import asyncio


class SQLiteStorage(DataStorage):
    """
    Асинхронное SQLite-хранилище с поддержкой batch-вставок.
    """

    def __init__(self, db_path: str, batch_size: int = 50):
        self.db_path = db_path
        self._conn = None
        self._batch = []
        self.batch_size = batch_size
        self._lock = asyncio.Lock()

    async def init_db(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                text TEXT,
                links TEXT,
                metadata TEXT,
                crawled_at TEXT,
                status_code INTEGER,
                content_type TEXT
            )
        """)
        await self._conn.commit()

    async def save(self, data: dict):
        """
        Добавляем запись в буфер и сохраняем при достижении batch_size.
        """
        async with self._lock:
            self._batch.append(data)
            if len(self._batch) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        """
        Сбрасываем буфер в базу данных. Не берём lock внутри!
        """
        if not self._batch or not self._conn:
            return

        async with self._conn.execute("BEGIN"):
            for d in self._batch:
                await self._conn.execute(
                    "INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        d["url"],
                        d["title"],
                        d["text"],
                        json.dumps(d["links"], ensure_ascii=False),
                        json.dumps(d["metadata"], ensure_ascii=False),
                        d["crawled_at"].isoformat() if isinstance(d["crawled_at"], datetime) else str(d["crawled_at"]),
                        d["status_code"],
                        d["content_type"]
                    )
                )
        await self._conn.commit()
        self._batch = []

    async def close(self):
        """
        Сбрасываем остаток буфера и закрываем соединение.
        """
        await self._flush()
        if self._conn:
            await self._conn.close()
            self._conn = None
