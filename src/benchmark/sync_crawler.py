# src/benchmark/sync_crawler.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm  # прогресс-бар

def crawl_sync(start_urls, max_pages=100):
    visited = set()
    queue = list(start_urls)
    results = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BenchmarkBot/1.0)"
    }

    # создаём прогресс-бар
    pbar = tqdm(total=max_pages, desc="SYNC crawl")

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code != 200:
                continue

            html = r.text
            results.append(url)
            visited.add(url)
            pbar.update(1)  # обновляем прогресс-бар

            # --- Найти ссылки на странице ---
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])  # разрешаем относительные ссылки
                if href.startswith("http") and href not in visited:
                    queue.append(href)

        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")

    pbar.close()
    return results, len(visited)
