import json
import re
from typing import Any, Dict, Iterable

import scrapy
from rich import print
from scrapy.http.request import Request
from scrapy.http.response import Response

# fmt: off
default_headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,ru;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


# fmt: on


class BrowserleaksSpider(scrapy.Spider):
    name = "browserleaks_spider"
    allowed_domains = ["tls.browserleaks.com"]
    start_urls = ["https://tls.browserleaks.com"]
    responses: Dict[str, Any] = {}

    def start_requests(self) -> Iterable[Request]:
        headers = default_headers.copy()
        yield Request(
            url="https://tls.browserleaks.com",
            headers=headers,
            dont_filter=True,
            callback=self.parse_http2,  # type: ignore[arg-type]
            meta={"dont_cache": True, "http2": True},
        )
        yield Request(
            url="https://tls.browserleaks.com",
            dont_filter=True,
            callback=self.parse_playwright,  # type: ignore[arg-type]
            meta={"dont_cache": True, "playwright": True},
        )

    def closed(self, reason: Any) -> Any:
        print(self.responses)

    # noinspection PyMethodMayBeStatic
    async def parse_http2(self, response: Response, **kwargs: Any) -> Any:
        self.responses["http2"] = json.loads(response.text)

    # noinspection PyMethodMayBeStatic
    async def parse_playwright(self, response: Response, **kwargs: Any) -> Any:
        pattern = r"<pre>(.*?)</pre>"
        matches = re.findall(pattern, response.text, re.DOTALL)
        self.responses["playwright"] = json.loads(matches[0])
