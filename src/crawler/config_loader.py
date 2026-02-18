# crawler/config_loader.py
import yaml
from pathlib import Path

class ConfigLoader:
    """Загрузка конфигурации YAML для краулера"""

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {path}")
        self.config = self._load()

    def _load(self):
        with self.path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data

    def get_crawler_settings(self):
        return self.config.get("crawler", {})

    def get_start_urls(self):
        return self.config.get("start_urls", [])

    def get_filters(self):
        return self.config.get("filters", {})

    def get_storage_settings(self):
        return self.config.get("storage", {})
