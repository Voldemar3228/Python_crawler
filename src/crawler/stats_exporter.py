# crawler/stats_exporter.py
import json
from urllib.parse import urlparse
from datetime import datetime
import matplotlib.pyplot as plt
import io
import base64

class CrawlerStatsExporter:
    """Класс для экспорта статистики краулера в JSON и HTML"""

    def __init__(self, crawler):
        self.crawler = crawler  # ссылка на AsyncCrawler

    def export_to_json(self, filename: str):
        """Сохраняет статистику краулера и содержимого страниц в JSON"""
        from utils.stats import compute_overall_stats

        data = {
            "crawler_summary": self.crawler.stats.get_summary(),
            "content_stats": compute_overall_stats(list(self.crawler.processed_urls.values())),
            "exported_at": datetime.utcnow().isoformat()
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"✅ Статистика экспортирована в JSON: {filename}")

    def export_to_html_report(self, filename: str):
        """Создаёт HTML-отчёт со статистикой и графиком"""
        from utils.stats import compute_overall_stats

        crawler_summary = self.crawler.stats.get_summary()
        content_stats = compute_overall_stats(list(self.crawler.processed_urls.values()))

        # 🔹 График: количество страниц по доменам
        domain_counts = {}
        for url in self.crawler.processed_urls:
            domain = urlparse(url).netloc
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        plt.figure(figsize=(6,4))
        plt.bar(domain_counts.keys(), domain_counts.values(), color="skyblue")
        plt.xticks(rotation=45, ha="right")
        plt.title("Страницы по доменам")
        plt.tight_layout()

        # Сохраняем график в base64
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")

        # 🔹 Генерация HTML
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Отчёт краулера</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                pre {{ background-color: #f4f4f4; padding: 10px; }}
            </style>
        </head>
        <body>
            <h1>Отчёт краулера</h1>
            <h2>Общая статистика</h2>
            <pre>{json.dumps(crawler_summary, ensure_ascii=False, indent=4)}</pre>

            <h2>Статистика содержимого страниц</h2>
            <pre>{json.dumps(content_stats, ensure_ascii=False, indent=4)}</pre>

            <h2>Распределение страниц по доменам</h2>
            <img src="data:image/png;base64,{img_base64}" alt="График доменов">
        </body>
        </html>
        """

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ HTML-отчёт создан: {filename}")
