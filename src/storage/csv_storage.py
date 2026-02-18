import aiofiles
import asyncio
import csv
import io
from .base import DataStorage


class CSVStorage(DataStorage):
    """
    Асинхронное CSV-хранилище с поддержкой batch-записи.
    """

    def __init__(
        self,
        filepath: str,
        encoding: str = "utf-8",
        delimiter: str = ",",
        batch_size: int = 50,
    ):
        self.filepath = filepath
        self.encoding = encoding
        self.delimiter = delimiter
        self.batch_size = batch_size

        self._file = None
        self._lock = asyncio.Lock()
        self._headers_written = False
        self._fieldnames = None
        self._buffer = []

    async def _ensure_open(self):
        if not self._file:
            self._file = await aiofiles.open(
                self.filepath,
                mode="a",
                encoding=self.encoding,
                newline=""
            )

    async def _flush(self):
        """
        Сбрасываем буфер в файл.
        """
        if not self._buffer:
            return

        await self._ensure_open()

        async with self._lock:
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=self._fieldnames,
                delimiter=self.delimiter,
                quoting=csv.QUOTE_MINIMAL
            )

            if not self._headers_written:
                writer.writeheader()
                self._headers_written = True

            for row in self._buffer:
                writer.writerow(row)

            await self._file.write(output.getvalue())
            self._buffer = []

    async def save(self, data: dict) -> None:
        """
        Добавляем запись в буфер. Если буфер достиг batch_size, сбрасываем в файл.
        """
        if not self._fieldnames:
            self._fieldnames = list(data.keys())

        self._buffer.append(data)

        if len(self._buffer) >= self.batch_size:
            await self._flush()

    async def close(self) -> None:
        """
        Сбрасываем оставшийся буфер и закрываем файл.
        """
        await self._flush()
        if self._file:
            await self._file.flush()
            await self._file.close()
            self._file = None
