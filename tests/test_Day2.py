import pytest
# from src.crawler.async_crawler import HTMLParser
from src.crawler.parser import HTMLParser
from src.crawler.logger import setup_crawler_logger

# Настройка логгера для тестов
logger = setup_crawler_logger(level=20)  # INFO, можно DEBUG для подробного вывода

@pytest.mark.asyncio
async def test_valid_html_parsing():
    logger.info("▶️ Starting test_valid_html_parsing")
    html = """
    <html>
        <head><title>Valid Page</title></head>
        <body>
            <h1>Header</h1>
            <p>Some text content</p>
            <a href="/relative-link">Relative</a>
            <a href="http://example.com/absolute">Absolute</a>
        </body>
    </html>
    """
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    logger.info(f"Parsed title: {parsed['title']}")
    logger.info(f"Parsed links: {parsed['links']}")
    logger.info(f"Parsed headers: {parsed['headers']}")

    assert parsed["title"] == "Valid Page"
    assert "Some text content" in parsed["text"]
    assert "http://test.com/relative-link" in parsed["links"]
    assert "http://example.com/absolute" in parsed["links"]
    assert parsed["headers"]["h1"] == ["Header"]

@pytest.mark.asyncio
async def test_broken_html_parsing():
    logger.info("⚠️ Starting test_broken_html_parsing")
    html = "<html><head><title>Broken Page</title><body><h1>Header<p>Unclosed tags"
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    logger.info(f"Parsed title: {parsed['title']}")
    logger.info(f"Parsed text snippet: {parsed['text'][:30]}...")

    assert parsed["title"] == "Broken Page"
    assert "Header" in parsed["text"]
    assert isinstance(parsed["links"], list)

@pytest.mark.asyncio
async def test_links_extraction():
    logger.info("🔗 Starting test_links_extraction")
    html = """
    <html>
        <body>
            <a href="/rel1">Rel1</a>
            <a href="/rel2">Rel2</a>
            <a href="http://external.com/ext">External</a>
            <a href="#anchor">Anchor</a>
            <a href="javascript:void(0)">JS</a>
        </body>
    </html>
    """
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://test.com")

    links = parsed["links"]
    logger.info(f"Extracted links: {links}")

    assert "#anchor" not in links
    assert "javascript:void(0)" not in links
    assert "http://test.com/rel1" in links
    assert "http://test.com/rel2" in links
    assert "http://external.com/ext" in links

@pytest.mark.asyncio
async def test_relative_url_conversion():
    logger.info("🔄 Starting test_relative_url_conversion")
    html = '<html><body><a href="/path/page.html">Relative</a></body></html>'
    parser = HTMLParser()
    parsed = await parser.parse_html(html, url="http://example.com/base/")

    logger.info(f"Converted links: {parsed['links']}")
    assert "http://example.com/path/page.html" in parsed["links"]

@pytest.mark.asyncio
async def test_extract_headers_images_lists_tables():
    logger.info("📊 Starting test_extract_headers_images_lists_tables")
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

    logger.info(f"Headers: {parsed['headers']}")
    logger.info(f"Lists: {parsed['lists']}")
    logger.info(f"Tables: {parsed['tables']}")
    logger.info(f"Images: {parsed['images']}")

    assert parsed["headers"]["h1"] == ["Header1"]
    assert parsed["headers"]["h2"] == ["Header2"]
    assert parsed["lists"]["ul"] == [["Item1"]]
    assert parsed["lists"]["ol"] == [["ItemA"]]
    assert parsed["tables"][0][0][0] == "Cell1"
    assert parsed["images"][0]["src"].endswith("img.jpg")
    assert parsed["images"][0]["alt"] == "Image1"
