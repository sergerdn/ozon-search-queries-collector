import datetime
import random
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Iterable, Set, TypeVar
from urllib.parse import quote_plus

import scrapy
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import BrowserContext
from playwright.sync_api import Page
from scrapy import signals
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.signalmanager import dispatcher  # type: ignore[attr-defined]
from scrapy.utils.project import get_project_settings

from ozon_collector.items import OzonCollectorItem

T = TypeVar("T")

# Basic Playwright settings
basic_playwright_context_kwargs: Dict[str, Any] = {
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disk-cache-size=%d" % 524288000,  # 500 MB
    ],
    "viewport": {"width": 1920, "height": 1080},
    "locale": "en-US,en,ru",
    "geolocation": {
        "latitude": 55.782463,
        "longitude": 37.596637,
        "accuracy": 90,
    },
    "timezone_id": "Europe/Moscow",
    "permissions": ["geolocation"],
    "headless": False,
}


def log_execution_time(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator to log the execution time of a function."""

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        if hasattr(args[0], "logger"):  # Check if the first argument has a logger
            args[0].logger.info(f"Execution time for {func.__name__}: {elapsed_time:.2f} seconds.")
        return result

    return wrapper


class OzonDataQuerySpider(scrapy.Spider):
    """A Scrapy spider for collecting data from the Ozon Search Queries analytics page.

    This spider uses Playwright to handle JavaScript-rendered pages and collects search
    analytics data based on a provided keyword.
    """

    name = "ozon_data_query_spider"
    allowed_domains = ["www.ozon.ru", "ozon.ru", "data.ozon.ru"]
    start_urls = ["https://www.ozon.ru"]
    chrome_executable_path: Path
    browser_profile_storage: Path
    initial_query_keyword: str
    jinja2_env: Environment

    parse_in_depth: bool  # Flag to control depth of parsing

    def __init__(
        self, initial_query_keyword: str = "", parse_in_depth: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        """Initialize the spider with the provided initial keyword and required configurations.

        Args:
            initial_query_keyword (str): The keyword to start data collection. Defaults to an empty string.
        """
        super().__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle_handler, signal=signals.spider_idle)

        self.initial_query_keyword = initial_query_keyword.strip()
        self.logger.info("Initial query keyword: %s", self.initial_query_keyword)
        self.parse_in_depth = parse_in_depth

        # Get Scrapy settings
        settings = get_project_settings()

        # Configure Chrome executable path
        self.chrome_executable_path: Path = settings.get("GOOGLE_CHROME_EXECUTABLE_PATH")
        if not self.chrome_executable_path or not self.chrome_executable_path.exists():
            raise ValueError("Chrome executable path is not set or invalid.")

        # Configure browser profile storage
        self.browser_profile_storage: Path = settings.get("BROWSER_PROFILE_STORAGE_DIR")
        if not self.browser_profile_storage or not self.browser_profile_storage.exists():
            raise ValueError("Browser profile storage path is not set or invalid.")

        # Ensure at least one profile directory exists
        profiles = [dir_name for dir_name in self.browser_profile_storage.iterdir() if dir_name.is_dir()]
        if not profiles:
            default_profile = self.browser_profile_storage.joinpath("1")
            default_profile.mkdir()
            profiles.append(default_profile)

        # Configure Jinja2 environment
        templates_dir: Path = settings.get("TEMPLATES_DIR")
        if not templates_dir or not templates_dir.exists():
            raise ValueError("Template directory path is not set or invalid.")
        self.jinja2_env = Environment(loader=FileSystemLoader(templates_dir))

    def spider_idle_handler(self) -> None:
        """This handler is called when Scrapy is idle, i.e., when there are no more requests left in the queue to
        process.

        The function currently logs that the spider is idle. In the future, this function can be extended to trigger an
        external API or action to fetch more requests dynamically. These new requests will then be added to the Scrapy
        scheduler to keep the spider active and scraping data.

        Future extensions could include:
            - Fetching new requests from an external API when the queue is empty.
            - Retrieving new data from other sources such as databases or file systems.
            - Implementing logic to handle different types of requests or conditions before fetching more tasks.

        The ultimate goal is to ensure the spider continues to scrape data seamlessly, even when the queue is empty,
        by fetching new tasks dynamically and keeping the spider running.
        """

        self.logger.info("Spider is idle. Triggering external API or action to add more requests.")

    def start_requests(self) -> Iterable[Request]:
        """Generate the initial request to start data collection."""

        # Select a random browser profile directory
        profiles = [dir_name for dir_name in self.browser_profile_storage.iterdir() if dir_name.is_dir()]
        user_data_dir = profiles[random.randint(0, len(profiles) - 1)]
        self.logger.info("Using browser profile directory: %s", user_data_dir)

        # Extend the base dictionary with specific settings
        playwright_context_kwargs = basic_playwright_context_kwargs.copy()
        playwright_context_kwargs["user_data_dir"] = str(user_data_dir)
        playwright_context_kwargs["executable_path"] = str(self.chrome_executable_path)

        # The URL is dynamically generated only for Scrapy's deduplicated scheduler; websites don't need this.
        url = "https://data.ozon.ru/app/search-queries?__%s" % quote_plus(self.initial_query_keyword)
        yield scrapy.Request(
            url=url,
            callback=self.parse_search_queries,  # type: ignore[arg-type]
            priority=0,
            dont_filter=True,
            meta={
                "dont_cache": True,
                "query_keyword": self.initial_query_keyword,
                "max_retry_times": 100,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": playwright_context_kwargs,
            },
        )

    @log_execution_time
    async def execute_js_in_browser(self, page: Page, rendered_js: str) -> Any:
        """Execute the given JavaScript in the browser and validate the result.

        Args:
            page (Page): Playwright page instance to execute the JS.
            rendered_js (str): The JavaScript code to execute in the browser.

        Returns:
            Any: The result of the executed JavaScript if valid, otherwise None.
        """
        self.logger.info("Executing JavaScript in the browser.")
        return await page.evaluate(rendered_js)

    async def _render_execute_and_get_items(
        self, page: Page, query_keyword: str
    ) -> AsyncGenerator[OzonCollectorItem, None]:
        """Render the JS for a query, execute it, and yield items."""
        template = self.jinja2_env.get_template("collect_search_queries.js.j2")
        rendered_js = template.render(
            keyword_query=query_keyword,
            max_retries=5,
        )

        # Execute the rendered JavaScript on the page
        result = await self.execute_js_in_browser(page, rendered_js)

        # If the result is not a list, log and return
        if not isinstance(result, list):
            self.logger.warning("Result is not a list.")
            return

        # Process and yield items
        for entry in result:
            assert isinstance(entry, dict)
            ordered_entry = {
                "_query_keyword": query_keyword,
                "_scraped_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
            ordered_entry.update(entry)
            item = OzonCollectorItem(**ordered_entry)
            yield item

    async def parse_search_queries(self, response: Response, **kwargs: Any) -> Any:
        """Parse the initial page and handle login if necessary."""
        page: Page = response.meta["playwright_page"]
        context: BrowserContext = page.context  # type: ignore[assignment]

        self.logger.debug(f"Current URL: {page.url}, page:{page}, context: {context}")

        # Wait for the user to log in if necessary
        expected_url = "https://data.ozon.ru/app/search-queries"
        while not page.url.startswith(expected_url):
            self.logger.warning("User is not logged in to Ozon.")
            self.logger.info("Please log in to Ozon with your credentials.")
            breakpoint()  # Pause for manual intervention

        self.logger.info("User successfully logged in.")

        query_keyword = response.meta["query_keyword"]
        parsed_keywords: Set[str] = set()

        async for item in self._render_execute_and_get_items(page, query_keyword):
            parsed_keywords.add(item["query"])
            yield item

        # Collect the keywords parsed during this step
        self.logger.debug(f"Parsed {len(parsed_keywords)} keywords from query '{query_keyword}': {parsed_keywords}")

        if self.parse_in_depth:
            for query_keyword in parsed_keywords:
                url = "https://data.ozon.ru/app/search-queries?__%s" % quote_plus(query_keyword)
                # Change the URL in the browser's address bar without reloading
                await page.evaluate(f"window.history.pushState(null, '', '{url}')")

                async for item in self._render_execute_and_get_items(page, query_keyword):
                    yield item

        self.logger.info("Finished.")