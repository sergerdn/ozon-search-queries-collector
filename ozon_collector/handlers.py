import logging
from typing import Any, Type, TypeVar

from scrapy import Spider
from scrapy.core.downloader.handlers.http import HTTPDownloadHandler  # type: ignore[attr-defined]
from scrapy.crawler import Crawler
from scrapy.http.request import Request
from scrapy.utils.reactor import verify_installed_reactor
from scrapy_playwright.handler import ScrapyPlaywrightDownloadHandler

CombinedHandler = TypeVar("CombinedHandler", bound="CombinedDownloadHandler")
logger = logging.getLogger(__name__)


class CombinedDownloadHandler(HTTPDownloadHandler):
    """A custom Download Handler that combines functionality from both Scrapy Playwright and Scrapy Impersonate. It
    dynamically selects the appropriate handler based on the request metadata.

    Attributes:
        playwright_handler (ScrapyPlaywrightDownloadHandler): Handles Playwright-based requests.
    """

    def __init__(self, crawler: Crawler):
        """Initialize the CombinedDownloadHandler.

        Args:
            crawler (Crawler): Scrapy crawler instance.
        """
        super().__init__(settings=crawler.settings, crawler=crawler)

        # Initialize handlers
        self.playwright_handler = ScrapyPlaywrightDownloadHandler(crawler=crawler)

        verify_installed_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

        logger.debug("CombinedDownloadHandler initialized.")

    @classmethod
    def from_crawler(cls: Type[CombinedHandler], crawler: Crawler) -> CombinedHandler:
        """Create an instance of CombinedDownloadHandler using the Scrapy crawler.

        Args:
            crawler (Crawler): Scrapy crawler instance.

        Returns:
            CombinedDownloadHandler: An instance of this class.
        """
        return cls(crawler)

    def download_request(self, request: Request, spider: Spider) -> Any:
        """Process the download request by delegating it to the appropriate handler.

        Args:
            request (Request): The Scrapy request object.
            spider (Spider): The Scrapy spider instance.

        Returns:
            Deferred: The Twisted Deferred object from the chosen handler.
        """
        if request.meta.get("playwright"):
            logger.debug(f"Using Scrapy Playwright for {request.url} .")
            return self.playwright_handler.download_request(request, spider)
        else:
            # Fallback to the default HTTP handler
            logger.debug(f"Using default HTTP handler for {request.url}.")
            return super().download_request(request, spider)
