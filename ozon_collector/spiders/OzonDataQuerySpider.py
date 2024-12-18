import asyncio
import datetime
import logging
import random
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Set, TypeVar
from urllib.parse import quote_plus

import scrapy
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import BrowserContext, ConsoleMessage, Page
from pydantic import TypeAdapter
from scrapy import signals
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.signalmanager import dispatcher  # type: ignore[attr-defined]
from scrapy.utils.log import SpiderLoggerAdapter
from scrapy.utils.project import get_project_settings
from tenacity import after_log, before_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ozon_collector.items import OzonCollectorItem

T = TypeVar("T")

logger = logging.getLogger(__name__)

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


class RequestLimitExceededException(Exception):
    pass


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
    query_popularity_threshold: int  # Minimum popularity score for deep parsing.

    def __init__(
        self,
        initial_query_keyword: str = "",
        parse_in_depth: bool = False,
        query_popularity_threshold: int = 10,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the spider with the provided initial keyword and required configurations.

        Args:
            initial_query_keyword (str): The keyword to start data collection. Defaults to an empty string.
            parse_in_depth (bool): Flag to control whether deep parsing is performed.
            query_popularity_threshold (int): The threshold for query popularity to filter out low-popularity queries.
        """
        super().__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle_handler, signal=signals.spider_idle)

        self.initial_query_keyword = initial_query_keyword.strip()
        self.logger.info("Initial query keyword: %s", self.initial_query_keyword)
        self.parse_in_depth = TypeAdapter(bool).validate_python(parse_in_depth)
        self.logger.info("Parse in depth: %s", self.parse_in_depth)
        self.query_popularity_threshold = TypeAdapter(int).validate_python(query_popularity_threshold)
        self.logger.info("Query popularity threshold: %d", self.query_popularity_threshold)

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

    # Apply retry logic with Tenacity and exponential backoff
    @retry(
        retry=retry_if_exception_type(Exception),
        # Retry up to 10 times
        stop=stop_after_attempt(10),
        # Exponential backoff with minimum delay of 5 minutes and max delay of 60 minutes
        wait=wait_exponential(multiplier=1, min=60 * 5, max=60 * 60),  # min 5 minutes, max 60 minutes
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,  # Reraise the exception if retries fail
    )
    async def _render_execute_and_get_items(self, page: Page, query_keyword: str) -> List[OzonCollectorItem]:
        """Render the JS for a query, execute it, and yield items."""
        template = self.jinja2_env.get_template("collect_search_queries_sequential.js")
        rendered_js = template.render(
            keyword_query=query_keyword,
            max_retries=5,
        )

        # Execute the rendered JavaScript on the page
        result = await self.execute_js_in_browser(page, rendered_js)

        # If the result is not a list, log and raise an error
        if not isinstance(result, list) or len(result) == 0:
            self.logger.error(f"Expected list, but got {type(result)}. Raising ValueError.")
            raise ValueError(f"Expected list, but got {type(result)}")

        # Process items
        items = []
        for entry in result:
            if not isinstance(entry, dict):
                self.logger.error("Expected dict, but got invalid result.")
                raise ValueError("Expected dict but got something else")

            ordered_entry = {
                "_query_keyword": query_keyword,
                "_scraped_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
            ordered_entry.update(entry)
            item = OzonCollectorItem(**ordered_entry)
            items.append(item)

        return items

    async def parse_search_queries(self, response: Response, **kwargs: Any) -> Any:
        """Parse the initial page and handle login if necessary."""
        page: Page = response.meta["playwright_page"]
        context: BrowserContext = page.context

        # Define the callback to handle console messages
        def handle_console(msg: ConsoleMessage) -> None:
            self.logger.debug(f"[browser]: {msg}")

        # Listen for browser console messages
        page.on("console", handle_console)
        await page.reload()

        page_url = page.url
        self.logger.debug(f"Current URL: {page_url}, page:{page}, context: {context}")

        # Log the page URL for debugging purposes
        self.logger.info(f"Current page URL: {page_url}")

        # Apply retry logic with Tenacity and exponential backoff
        @retry(
            retry=retry_if_exception_type(RequestLimitExceededException),
            # Retry up to 10 times
            stop=stop_after_attempt(10),
            # Exponential backoff with minimum delay of 5 minutes and max delay of 60 minutes
            wait=wait_exponential(multiplier=1, min=60 * 5, max=60 * 60),  # min 5 minutes, max 60 minutes
            before=before_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
            reraise=True,  # Reraise the exception if retries fail
        )
        async def check_app_requests_limit(p: Page, log: SpiderLoggerAdapter) -> None:
            await p.reload()
            # Check if the request limit has been exceeded
            if p.url == "https://data.ozon.ru/app/requests-limit":
                log.warning("Request limit exceeded. Raising exception.")
                raise RequestLimitExceededException("Ozon request limit reached.")

        # Wait for the user to log in if necessary
        expected_url = "https://data.ozon.ru/app/search-queries"
        while not page.url.startswith(expected_url):
            # Check if the request limit has been exceeded
            await check_app_requests_limit(p=page, log=self.logger)

            self.logger.warning("User is not logged in to Ozon.")
            self.logger.info("Please log in to Ozon with your credentials.")
            breakpoint()  # Pause for manual intervention

        logger.info("User successfully logged in.")

        query_keyword = response.meta["query_keyword"]
        parsed_keywords: Set[str] = set()

        items = await self._render_execute_and_get_items(page, query_keyword)
        for item in items:
            # Get the popularity score for the current query
            popularity = int(item.get("count", 0))
            if popularity >= self.query_popularity_threshold:
                parsed_keywords.add(item["query"])
            yield item

        # Collect the keywords parsed during this step
        self.logger.debug(f"Parsed {len(parsed_keywords)} keywords from query '{query_keyword}': {parsed_keywords}")

        if self.parse_in_depth:
            for query_keyword in parsed_keywords:
                url = "https://data.ozon.ru/app/search-queries?__%s" % quote_plus(query_keyword)
                # Change the URL in the browser's address bar without reloading
                await page.evaluate(f"window.history.pushState(null, '', '{url}')")
                await asyncio.sleep(10)

                while True:
                    try:
                        items = await self._render_execute_and_get_items(page, query_keyword)
                    except Exception as e:
                        self.logger.error(e)
                        breakpoint()
                    break

                for item in items:
                    # Skip processing if the item’s query already matches the current query_keyword
                    if item.get("query") == query_keyword:
                        continue

                    yield item

        self.logger.info("Finished.")
