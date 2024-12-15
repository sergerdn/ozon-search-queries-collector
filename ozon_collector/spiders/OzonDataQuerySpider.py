import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import scrapy
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import BrowserContext, Page
from scrapy import Request
from scrapy.http import Response
from scrapy.utils.project import get_project_settings

from ozon_collector.items import OzonCollectorItem


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log the execution time of a function."""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        if hasattr(args[0], "logger"):  # Check if the first argument has a logger
            args[0].logger.info(
                f"Execution time for {func.__name__}: {elapsed_time:.2f} seconds."
            )
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
    initial_keyword: str
    jinja2_env: Environment

    def __init__(self, initial_keyword: str = "", *args, **kwargs):
        """Initialize the spider with the provided initial keyword and required configurations.

        Args:
            initial_keyword (str): The keyword to start data collection. Defaults to an empty string.
        """
        super().__init__(*args, **kwargs)

        self.initial_keyword = initial_keyword.strip()
        self.logger.info("Initial keyword: %s", self.initial_keyword)

        # Get Scrapy settings
        settings = get_project_settings()

        # Configure Chrome executable path
        self.chrome_executable_path: Path = settings.get(
            "GOOGLE_CHROME_EXECUTABLE_PATH"
        )
        if not self.chrome_executable_path or not self.chrome_executable_path.exists():
            raise ValueError("Chrome executable path is not set or invalid.")

        # Configure browser profile storage
        self.browser_profile_storage: Path = settings.get("BROWSER_PROFILE_STORAGE_DIR")
        if (
            not self.browser_profile_storage
            or not self.browser_profile_storage.exists()
        ):
            raise ValueError("Browser profile storage path is not set or invalid.")

        # Ensure at least one profile directory exists
        profiles = [
            dir_name
            for dir_name in self.browser_profile_storage.iterdir()
            if dir_name.is_dir()
        ]
        if not profiles:
            default_profile = self.browser_profile_storage.joinpath("1")
            default_profile.mkdir()
            profiles.append(default_profile)

        # Configure Jinja2 environment
        templates_dir: Path = settings.get("TEMPLATES_DIR")
        if not templates_dir or not templates_dir.exists():
            raise ValueError("Template directory path is not set or invalid.")
        self.jinja2_env = Environment(loader=FileSystemLoader(templates_dir))

    def start_requests(self) -> Iterable[Request]:
        """Generate the initial request to start data collection."""

        # Select a random browser profile directory
        profiles = [
            dir_name
            for dir_name in self.browser_profile_storage.iterdir()
            if dir_name.is_dir()
        ]
        user_data_dir = profiles[random.randint(0, len(profiles) - 1)]
        self.logger.info("Using browser profile directory: %s", user_data_dir)

        yield scrapy.Request(
            url="https://data.ozon.ru/app/search-queries",
            callback=self.parse_initial,
            priority=0,
            dont_filter=True,
            meta={
                "dont_cache": True,
                "max_retry_times": 100,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_data_dir": str(user_data_dir),
                    "executable_path": str(self.chrome_executable_path),
                    "args": ["--disable-blink-features=AutomationControlled"],
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
                },
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

    async def parse_initial(self, response: Response, **kwargs: Any) -> Any:
        """Parse the initial page and handle login if necessary."""
        page: Page = response.meta["playwright_page"]
        context: BrowserContext = page.context

        self.logger.debug(f"Current URL: {page.url}")

        # Wait for the user to log in if necessary
        expected_url = "https://data.ozon.ru/app/search-queries"
        while not page.url.startswith(expected_url):
            self.logger.warning("User is not logged in to Ozon.")
            self.logger.info("Please log in to Ozon with your credentials.")
            breakpoint()  # Pause for manual intervention

        self.logger.info("User successfully logged in.")

        # Render the JavaScript template
        template = self.jinja2_env.get_template("collect_search_queries.js.j2")
        rendered_js = template.render(
            keyword_query=self.initial_keyword,
            max_retries=5,
        )

        # Execute the rendered JavaScript in the browser
        result = await self.execute_js_in_browser(page, rendered_js)
        if not isinstance(result, list):
            self.logger.warning("Result is not a list.")
            return

        # Process items
        for entry in result:
            assert isinstance(entry, dict)
            ordered_entry = {
                "_keyword": self.initial_keyword,
                "_scraped_at": datetime.utcnow().isoformat(),
            }
            ordered_entry.update(entry)
            item = OzonCollectorItem(**ordered_entry)

            yield item

        self.logger.info("Finished.")
