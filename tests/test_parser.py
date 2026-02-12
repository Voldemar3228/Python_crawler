import pytest
from src.crawler.async_crawler import HTMLParser
import logging
from src.crawler.logger import setup_crawler_logger

# -------------------
# Настройка логирования
# -------------------
logger = setup_crawler_logger(level=logging.INFO)


# -------------------
# Тесты
# -------------------

@pytest.mark.asyncio
async def test_extract_text():
    html = "<html><body><p>Hello World</p></body></html>"
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    # Логирование
    logger.info(f"[test_extract_text] Extracted text: {parsed['text']}")

    assert "Hello World" in parsed["text"]


@pytest.mark.asyncio
async def test_extract_links():
    html = '<html><body><a href="/link1">Link1</a><a href="http://example.com">Ext</a></body></html>'
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    # Логирование
    logger.info(f"[test_extract_links] Extracted links: {parsed['links']}")

    # ссылки должны быть абсолютными
    assert "http://test.com/link1" in parsed["links"]
    assert "http://example.com" in parsed["links"]


@pytest.mark.asyncio
async def test_extract_headers_images_lists_tables():
    html = """
    <html><body>
        <h1>Header1</h1>
        <h2>Header2</h2>
        <ul><li>Item1</li></ul>
        <ol><li>ItemA</li></ol>
        <table><tr><td>Cell1</td></tr></table>
        <img src="img.jpg" alt="Image1"/>
    </body></html>
    """
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    # Логирование
    logger.info(f"[test_extract_headers_images_lists_tables] Headers: {parsed['headers']}")
    logger.info(f"[test_extract_headers_images_lists_tables] Lists: {parsed['lists']}")
    logger.info(f"[test_extract_headers_images_lists_tables] Tables: {parsed['tables']}")
    logger.info(f"[test_extract_headers_images_lists_tables] Images: {parsed['images']}")

    # Проверки
    assert parsed["headers"]["h1"] == ["Header1"]
    assert parsed["headers"]["h2"] == ["Header2"]
    assert parsed["lists"]["ul"] == [["Item1"]]
    assert parsed["lists"]["ol"] == [["ItemA"]]
    assert parsed["tables"][0][0][0] == "Cell1"
    assert parsed["images"][0]["src"].endswith("img.jpg")
    assert parsed["images"][0]["alt"] == "Image1"
