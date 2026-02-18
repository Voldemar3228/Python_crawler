# crawler/storage/__init__.py

# Абстрактный базовый класс
from .base import DataStorage

# Конкретные реализации
from .json_storage import JSONStorage
from .csv_storage import CSVStorage
from .sqlite_storage import SQLiteStorage

# Явно указываем, что экспортируется при импорте *
__all__ = [
    "DataStorage",
    "JSONStorage",
    "CSVStorage",
    "SQLiteStorage"
]
