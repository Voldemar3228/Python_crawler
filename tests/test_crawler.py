import pytest
import asyncio

@pytest.mark.asyncio
async def test_fetch_url_success(async_crawler, test_server):
    url = f"{test_server}/page1"
    html = await async_crawler.fetch_url(url)
    assert "Test /page1" in html
    assert "<h1>Hello /page1</h1>" in html

@pytest.mark.asyncio
async def test_fetch_urls_multiple(async_crawler, test_server):
    urls = [f"{test_server}/a", f"{test_server}/b", f"{test_server}/c"]
    results = await async_crawler.fetch_urls(urls)
    assert len(results) == 3
    for url, html in results:
        assert "Hello" in html

@pytest.mark.asyncio
async def test_fetch_and_parse(async_crawler, test_server):
    url = f"{test_server}/parse_test"
    parsed = await async_crawler.fetch_and_parse(url)
    assert parsed["title"] == "Test /parse_test"
    assert "<h1>Hello /parse_test</h1>" not in parsed["text"]  # text cleaned
    assert len(parsed["links"]) == 2
