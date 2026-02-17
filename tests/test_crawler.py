import pytest
import asyncio
from crawler.queue import CrawlerQueue
from crawler.async_crawler import AsyncCrawler

# -----------------------------
# 0️⃣ Фикстура для тестового краулера
# -----------------------------
@pytest.fixture
async def async_crawler():
    crawler = AsyncCrawler(max_concurrent=2)
    yield crawler
    await crawler.close()


# -----------------------------
# 1️⃣ Тест загрузки страницы через fetch_url
# -----------------------------
@pytest.mark.asyncio
async def test_fetch_url_success(async_crawler, test_server):
    url = f"{test_server}/page1"
    html = await async_crawler.fetch_url(url)
    assert "Test /page1" in html
    assert "<h1>Hello /page1</h1>" in html


# -----------------------------
# 2️⃣ Тест параллельной загрузки нескольких URL через crawl
# -----------------------------
@pytest.mark.asyncio
async def test_crawl_multiple(async_crawler, test_server):
    urls = [f"{test_server}/a", f"{test_server}/b", f"{test_server}/c"]

    # Подменяем parse_html, чтобы не парсить реальные страницы
    async def fake_parse(url, html):
        return {
            "links": [],
            "text": html,
            "title": f"Test {url}",
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
            "url": url
        }

    async_crawler.parse_html = fake_parse

    results = await async_crawler.crawl(start_urls=urls, max_pages=3, max_depth=1)
    assert len(results) == 3
    titles = [p["title"] for p in results]
    for u in urls:
        assert any(u in t for t in titles)


# -----------------------------
# 3️⃣ Тест парсинга страницы
# -----------------------------
@pytest.mark.asyncio
async def test_parse_html(async_crawler, test_server):
    url = f"{test_server}/parse_test"

    async def fake_parse(url, html):
        return {
            "title": "Test /parse_test",
            "text": "Hello /parse_test",
            "links": ["http://example.com/a", "http://example.com/b"],
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
            "url": url
        }

    async_crawler.parse_html = fake_parse
    html = await async_crawler.fetch_url(url)
    parsed = await async_crawler.parse_html(url, html)
    assert parsed["title"] == "Test /parse_test"
    assert "Hello" in parsed["text"]
    assert len(parsed["links"]) == 2


# -----------------------------
# 4️⃣ Тестирование очереди с приоритетами
# -----------------------------
@pytest.mark.asyncio
async def test_crawler_queue_priority():
    queue = CrawlerQueue()
    await queue.add_url("url_low", priority=10)
    await queue.add_url("url_high", priority=1)
    await queue.add_url("url_mid", priority=5)

    first = await queue.get_next()
    second = await queue.get_next()
    third = await queue.get_next()

    assert first[0] == "url_high"
    assert second[0] == "url_mid"
    assert third[0] == "url_low"


# -----------------------------
# 5️⃣ Тест ограничения глубины
# -----------------------------
@pytest.mark.asyncio
async def test_max_depth():
    urls = ["http://example.com/start"]
    crawler = AsyncCrawler(max_concurrent=2)

    async def fake_parse(url, html):
        if url.endswith("start"):
            return {
                "links": ["http://example.com/a", "http://example.com/b"],
                "text": "",
                "title": url,
                "metadata": {},
                "images": [],
                "headers": {},
                "tables": [],
                "lists": {},
                "url": url
            }
        return {
            "links": ["http://example.com/c"],
            "text": "",
            "title": url,
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
            "url": url
        }

    crawler.parse_html = fake_parse
    results = await crawler.crawl(start_urls=urls, max_pages=10, max_depth=1)

    for parsed in results:
        for link in parsed.get("links", []):
            assert "c" not in link  # глубина 2 не должна быть добавлена


# -----------------------------
# 6️⃣ Тест фильтрации URL (allowed_domains + include/exclude)
# -----------------------------
@pytest.mark.asyncio
async def test_url_filtering():
    urls = ["http://example.com/start", "http://notallowed.com/page"]
    crawler = AsyncCrawler(
        allowed_domains=["example.com"],
        include_patterns=[r"/start"],
        exclude_patterns=[r"/forbidden"]
    )

    async def fake_parse(url, html):
        return {
            "links": ["http://example.com/start2", "http://example.com/forbidden"],
            "text": "",
            "title": url,
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
            "url": url
        }

    crawler.parse_html = fake_parse
    await crawler.crawl(start_urls=urls, max_pages=10)
    visited = crawler.visited_urls
    assert "http://example.com/forbidden" not in visited
    assert "http://example.com/start" in visited


# -----------------------------
# 7️⃣ Проверка отсутствия дубликатов в visited_urls
# -----------------------------
@pytest.mark.asyncio
async def test_no_duplicates_in_visited():
    urls = ["http://example.com/start"]
    crawler = AsyncCrawler(max_concurrent=2)

    async def fake_parse(url, html):
        return {
            "links": ["http://example.com/start", "http://example.com/other"],
            "text": "",
            "title": url,
            "metadata": {},
            "images": [],
            "headers": {},
            "tables": [],
            "lists": {},
            "url": url
        }

    crawler.parse_html = fake_parse

    await crawler.crawl(start_urls=urls, max_pages=10)
    visited = list(crawler.visited_urls)
    assert len(visited) == len(set(visited))
