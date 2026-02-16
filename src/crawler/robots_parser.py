import aiohttp
from urllib.parse import urlparse, urljoin
import urllib.robotparser as robotparser


class RobotsParser:
    def __init__(self):
        self._cache = {}

    async def fetch_robots(self, base_url: str):
        parsed = urlparse(base_url)
        domain = parsed.scheme + "://" + parsed.netloc

        if domain in self._cache:
            return self._cache[domain]

        robots_url = urljoin(domain, "/robots.txt")

        rp = robotparser.RobotFileParser()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url) as resp:
                    text = await resp.text()
                    rp.parse(text.splitlines())
        except Exception:
            rp.parse([])

        self._cache[domain] = rp
        return rp

    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        rp = await self.fetch_robots(url)
        return rp.can_fetch(user_agent, url)

    async def get_crawl_delay(self, url: str, user_agent: str = "*") -> float:
        rp = await self.fetch_robots(url)
        delay = rp.crawl_delay(user_agent)
        return delay if delay else 0
