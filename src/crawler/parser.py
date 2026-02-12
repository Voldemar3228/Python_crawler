from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from crawler.logger import setup_crawler_logger
import logging
logger = setup_crawler_logger(level=logging.INFO)

class HTMLParser:
    # html parsing method
    async def parse_html(self, html: str, url: str) -> dict:
        """
        Main method of parsing HTML / Основной метод парсинга HTML.
        Returns: / Возвращает:
        {
            url: str,
            title: str,
            text: str,
            links: list[str],
            metadata: dict
        }
        """

        result = {
            "url": url,
            "title": "",
            "text": "",
            "links": [],
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
        }
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create BeautifulSoup for {url}: {e}")
            return result

        # Delete unnecessary elements / Удаляем ненужные элементы
        try:
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
        except Exception as e:
            logger.warning(f"⚠️ Failed to create BeautifulSoup for {url}: {e}")
            return result

        result["metadata"] = self._safe_extract(self.extract_metadata, soup, default={})
        result["title"] = result["metadata"].get("title", "")
        result["text"] = self._safe_extract(self.extract_text, soup, default="")
        result["links"] = self._safe_extract(self.extract_links, soup, url,  default=[])
        # Извлечение специфичных данных
        result["images"] = self._safe_extract(self.extract_images, soup, url, default=[])
        result["headers"] = self._safe_extract(self.extract_headers, soup,  default={})
        result["tables"] = self._safe_extract(self.extract_tables, soup,  default=[])
        result["lists"] = self._safe_extract(self.extract_lists, soup,  default={})

        return result

    def _safe_extract(self, func, *args, default=None):
        """
        Safely execute extractor function.
        """
        try:
            return func(*args)
        except Exception as e:
            logger.warning(
                f"⚠️ Parsing error in {func.__name__}: {e}",
                exc_info=True
            )
            return default

    # ---------------- Extractors ----------------

    # ---------------- Изображения ----------------
    def extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """
        Extract all <img> tags with absolute src and alt text.
        Returns: [{"src": str, "alt": str}, ...]
        """
        images = []
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"].strip())
            alt = img.get("alt", "").strip()
            images.append({"src": src, "alt": alt})
        return images

    # ---------------- Заголовки ----------------
    def extract_headers(self, soup: BeautifulSoup) -> dict:
        """
        Extract all h1, h2, h3 headers.
        Returns: {"h1": [...], "h2": [...], "h3": [...]}
        """
        headers = {}
        for level in ["h1", "h2", "h3"]:
            headers[level] = [h.get_text(strip=True) for h in soup.find_all(level)]
        return headers

    # ---------------- Таблицы ----------------
    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        """
        Extract tables as nested lists:
        [
            [ ["row1col1", "row1col2"], ["row2col1", "row2col2"] ],
            ...
        ]
        """
        tables = []
        for table in soup.find_all("table"):
            table_data = []
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                table_data.append([cell.get_text(strip=True) for cell in cells])
            if table_data:
                tables.append(table_data)
        return tables

    # ---------------- Списки ----------------
    def extract_lists(self, soup: BeautifulSoup) -> dict:
        """
        Extract ul and ol lists.
        Returns: {"ul": [[...], [...]], "ol": [[...], [...]]}
        """
        lists = {"ul": [], "ol": []}

        for ul in soup.find_all("ul"):
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            if items:
                lists["ul"].append(items)

        for ol in soup.find_all("ol"):
            items = [li.get_text(strip=True) for li in ol.find_all("li")]
            if items:
                lists["ol"].append(items)

        return lists

    # link extraction
    def extract_links(self, soup: BeautifulSoup, base_url: str, internal_only: bool = False) -> list[str]:
        """
        Extract and normalize links.

        - Convert relative links to absolute
        - Optionally filter external links
        - Validate URLs before adding
        """
        links = set()
        base_domain = urlparse(base_url).netloc

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()

            # пропускаем пустые, якоря и javascript
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            # базовая валидация
            if parsed.scheme not in ("http", "https"):
                continue
            if not parsed.netloc:
                continue

            # фильтрация внешних ссылок
            if internal_only and parsed.netloc != base_domain:
                continue

            # убираем фрагмент (#section)
            clean_url = parsed._replace(fragment="").geturl()

            links.add(clean_url)

        return list(links)

    # text extraction
    def extract_text(self, soup: BeautifulSoup, selector: str = None) -> str:
        """
        Extract page text.
        If CSS selector is specified, it extracts text only from the selected block.
        /
        Извлекает текст страницы.
        Если указан CSS selector — извлекает текст только из выбранного блока.
        """
        if selector:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator=" ", strip=True)
            return ""

        return soup.get_text(separator=" ", strip=True)

    # meta data extraction
    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        """
        Extract main meta data / Извлекает основные мета-данные:
        - title
        - description
        - keywords
        """
        metadata = {}

        # Title
        if soup.title and soup.title.string:
            metadata["title"] = soup.title.string.strip()

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            property_ = meta.get("property", "").lower()
            content = meta.get("content", "").strip()

            if not content:
                continue

            if name == "description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = content
            elif property_ == "og:title" and "title" not in metadata:
                metadata["title"] = content
            elif property_ == "og:description" and "description" not in metadata:
                metadata["description"] = content

        return metadata
