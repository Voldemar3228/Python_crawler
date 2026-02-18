# src/utils/stats.py
from collections import Counter
import time
from urllib.parse import urlparse

# === Существующие функции ===
def compute_page_stats(parsed_page: dict) -> dict:
    return {
        "url": parsed_page["url"],
        "text_length": len(parsed_page["text"]),
        "num_links": len(parsed_page["links"]),
        "num_h1": len(parsed_page["headers"].get("h1", [])),
        "num_h2": len(parsed_page["headers"].get("h2", [])),
        "num_h3": len(parsed_page["headers"].get("h3", [])),
        "num_images": len(parsed_page["images"]),
        "num_lists": len(parsed_page["lists"].get("ul", [])) + len(parsed_page["lists"].get("ol", [])),
        "num_tables": len(parsed_page["tables"]),
    }

def compute_overall_stats(parsed_pages: list[dict]) -> dict:
    total_text = sum(len(p["text"]) for p in parsed_pages)
    total_links = sum(len(p["links"]) for p in parsed_pages)
    total_images = sum(len(p["images"]) for p in parsed_pages)
    return {
        "total_pages": len(parsed_pages),
        "total_text_length": total_text,
        "total_links": total_links,
        "total_images": total_images,
    }


# === Новый класс для расширенной статистики краулера ===
class CrawlerStats:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.processed_pages = 0
        self.successful_pages = 0
        self.failed_pages = 0
        self.status_codes = Counter()
        self.domain_counts = Counter()
        self.request_times = []

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def record_page(self, url: str, status_code: int, success: bool, request_time: float = 0):
        self.processed_pages += 1
        if success:
            self.successful_pages += 1
        else:
            self.failed_pages += 1

        self.status_codes[status_code] += 1
        domain = urlparse(url).netloc
        self.domain_counts[domain] += 1
        if request_time:
            self.request_times.append(request_time)

    @property
    def elapsed_time(self):
        if not self.start_time:
            return 0
        return (self.end_time or time.time()) - self.start_time

    @property
    def avg_speed(self):
        elapsed = self.elapsed_time
        return self.processed_pages / elapsed if elapsed > 0 else 0

    @property
    def avg_request_time(self):
        return sum(self.request_times) / len(self.request_times) if self.request_times else 0

    def top_domains(self, n=5):
        return self.domain_counts.most_common(n)

    def get_summary(self):
        return {
            "processed_pages": self.processed_pages,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "status_codes": dict(self.status_codes),
            "top_domains": self.top_domains(),
            "elapsed_time": self.elapsed_time,
            "avg_speed_pages_per_sec": self.avg_speed,
            "avg_request_time_sec": self.avg_request_time
        }
