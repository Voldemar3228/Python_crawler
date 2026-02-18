# src/crawler/sitemap_parser.py
import aiohttp
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from crawler.logger import setup_crawler_logger

logger = setup_crawler_logger()

class SitemapParser:
    """
    Парсер sitemap.xml и sitemap index.
    """

    def __init__(self):
        self.visited_sitemaps = set()  # чтобы не обрабатывать один sitemap несколько раз

    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        """
        Загружает sitemap или sitemap index и возвращает список всех URL.
        """
        if sitemap_url in self.visited_sitemaps:
            return []
        self.visited_sitemaps.add(sitemap_url)

        urls = []

        # 🔹 Вот сюда добавляем блок с обработкой ошибок
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as resp:
                    if resp.status != 200:
                        logger.warning(f"Sitemap not found: {sitemap_url} (status {resp.status})")
                        return []
                    text = await resp.text()
        except Exception as e:
            logger.error(f"Ошибка при загрузке sitemap {sitemap_url}: {e}")
            return urls

        # Парсинг XML
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            logger.error(f"Ошибка парсинга XML: {sitemap_url}")
            return urls

        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        if root.tag.endswith("sitemapindex"):
            # Sitemap Index → рекурсивно обрабатываем каждый sitemap
            for sitemap in root.findall("sm:sitemap", ns):
                loc = sitemap.find("sm:loc", ns).text
                if loc:
                    urls.extend(await self.fetch_sitemap(loc))
        elif root.tag.endswith("urlset"):
            # Обычный sitemap
            for url in root.findall("sm:url", ns):
                loc = url.find("sm:loc", ns).text
                if loc:
                    urls.append(loc)

        return urls
