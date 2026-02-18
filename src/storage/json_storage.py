import aiofiles
import asyncio
import json
from .base import DataStorage
from datetime import datetime


class JSONStorage(DataStorage):
    """
    Асинхронное JSON-хранилище с поддержкой batch-записи.
    Каждая запись сохраняется как отдельная строка JSON.
    """

    def __init__(self, filename: str, batch_size: int = 50):
        self.filename = filename
        self._buffer = []
        self.batch_size = batch_size
        self._file = None
        self._lock = asyncio.Lock()  # для потокобезопасности

    async def _ensure_open(self):
        if not self._file:
            self._file = await aiofiles.open(
                self.filename,
                mode='a',
                encoding='utf-8'
            )

    async def _flush(self):
        if not self._buffer:
            return

        await self._ensure_open()

        async with self._lock:
            for item in self._buffer:
                # Преобразуем datetime в ISO строку
                data_to_write = item.copy()
                if isinstance(data_to_write.get("crawled_at"), datetime):
                    data_to_write["crawled_at"] = data_to_write["crawled_at"].isoformat()

                await self._file.write(json.dumps(data_to_write, ensure_ascii=False) + "\n")

            self._buffer = []

    async def save(self, data: dict):
        """
        Добавляем запись в буфер и сбрасываем при достижении batch_size.
        """
        self._buffer.append(data)
        if len(self._buffer) >= self.batch_size:
            await self._flush()

    async def close(self):
        """
        Сбрасываем оставшийся буфер и закрываем файл.
        """
        await self._flush()
        if self._file:
            await self._file.flush()
            await self._file.close()
            self._file = None
