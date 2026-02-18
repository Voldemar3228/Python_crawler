import pytest
import os
import json
import csv
import aiosqlite
import asyncio
from datetime import datetime

from storage.json_storage import JSONStorage
from storage.csv_storage import CSVStorage
from storage.sqlite_storage import SQLiteStorage


@pytest.mark.asyncio
async def test_json_storage(tmp_path):
    file_path = tmp_path / "test.json"
    storage = JSONStorage(str(file_path), batch_size=2)

    data1 = {"url": "http://a.com", "title": "A", "crawled_at": datetime.utcnow()}
    data2 = {"url": "http://b.com", "title": "B", "crawled_at": datetime.utcnow()}
    data3 = {"url": "http://c.com", "title": "C", "crawled_at": datetime.utcnow()}

    await storage.save(data1)
    await storage.save(data2)  # batch_size reached → flush
    await storage.save(data3)  # remains in buffer
    await storage.close()      # flush remaining

    # Проверяем содержимое файла
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 3
        for line in lines:
            item = json.loads(line)
            assert "url" in item
            assert "crawled_at" in item


@pytest.mark.asyncio
async def test_csv_storage(tmp_path):
    file_path = tmp_path / "test.csv"
    storage = CSVStorage(str(file_path), batch_size=2)

    data1 = {"url": "http://a.com", "title": "A", "crawled_at": datetime.utcnow()}
    data2 = {"url": "http://b.com", "title": "B", "crawled_at": datetime.utcnow()}
    data3 = {"url": "http://c.com", "title": "C", "crawled_at": datetime.utcnow()}

    await storage.save(data1)
    await storage.save(data2)  # flush
    await storage.save(data3)  # in buffer
    await storage.close()      # flush remaining

    # Проверяем содержимое CSV
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 3
        for row in rows:
            assert "url" in row
            assert "title" in row


@pytest.mark.asyncio
async def test_sqlite_storage(tmp_path):
    db_path = tmp_path / "test.db"
    storage = SQLiteStorage(str(db_path), batch_size=2)
    await storage.init_db()

    data1 = {"url": "http://a.com", "title": "A", "text": "", "links": [], "metadata": {}, "crawled_at": datetime.utcnow(), "status_code": 200, "content_type": "text/html"}
    data2 = {"url": "http://b.com", "title": "B", "text": "", "links": [], "metadata": {}, "crawled_at": datetime.utcnow(), "status_code": 200, "content_type": "text/html"}
    data3 = {"url": "http://c.com", "title": "C", "text": "", "links": [], "metadata": {}, "crawled_at": datetime.utcnow(), "status_code": 200, "content_type": "text/html"}

    await storage.save(data1)
    await storage.save(data2)  # flush
    await storage.save(data3)
    await storage.close()      # flush remaining

    # Проверяем данные в БД
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute("SELECT url, title FROM pages") as cursor:
            rows = await cursor.fetchall()
            assert len(rows) == 3
            urls = [r[0] for r in rows]
            titles = [r[1] for r in rows]
            assert "http://a.com" in urls
            assert "A" in titles


@pytest.mark.asyncio
async def test_error_handling_json(tmp_path):
    file_path = tmp_path / "readonly.json"
    # Создаём файл и делаем его только для чтения
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    os.chmod(file_path, 0o400)

    storage = JSONStorage(str(file_path), batch_size=1)
    data = {"url": "http://fail.com", "title": "Fail", "crawled_at": datetime.utcnow()}

    try:
        await storage.save(data)
    except Exception:
        pass  # ошибка сохранения обработана
    finally:
        os.chmod(file_path, 0o600)  # возвращаем права на запись


@pytest.mark.asyncio
async def test_error_handling_csv(tmp_path):
    file_path = tmp_path / "readonly.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    os.chmod(file_path, 0o400)

    storage = CSVStorage(str(file_path), batch_size=1)
    data = {"url": "http://fail.com", "title": "Fail", "crawled_at": datetime.utcnow()}

    try:
        await storage.save(data)
    except Exception:
        pass
    finally:
        os.chmod(file_path, 0o600)


@pytest.mark.asyncio
async def test_error_handling_sqlite(tmp_path):
    db_path = tmp_path / "test.db"
    storage = SQLiteStorage(str(db_path), batch_size=1)
    await storage.init_db()
    # закрываем соединение чтобы вызвать ошибку при сохранении
    await storage._conn.close()
    data = {"url": "http://fail.com", "title": "Fail", "text": "", "links": [], "metadata": {}, "crawled_at": datetime.utcnow(), "status_code": 200, "content_type": "text/html"}
    try:
        await storage.save(data)
    except Exception:
        pass
