import json
from pathlib import Path
from typing import Any

def save_json(path: str, data: Any, ensure_ascii: bool = False, indent: int = 2):
    """Сохраняет данные в JSON файл"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)

def load_json(path: str) -> Any:
    """Загружает JSON файл"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
