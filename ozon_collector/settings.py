# Scrapy settings for ozon_collector project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import logging
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from playwright.async_api import Request

from .utils import get_browser_profile_storage, get_chrome_executable_path

ABS_PATH: Path = Path(os.path.dirname(os.path.abspath(__file__))).parent
enf_filename = ABS_PATH / ".env.development"
assert enf_filename.exists()
load_dotenv(enf_filename)

logger = logging.getLogger(__name__)

BOT_NAME = "ozon_collector"

SPIDER_MODULES = ["ozon_collector.spiders"]
NEWSPIDER_MODULE = "ozon_collector.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = None

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 2

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,ru;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "service-worker-navigation-preload": "true",
    "upgrade-insecure-requests": "1",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "ozon_collector.middlewares.OzonCollectorSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    "ozon_collector.middlewares.OzonCollectorDownloaderMiddleware": 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# ITEM_PIPELINES = {
#    "ozon_collector.pipelines.OzonCollectorPipeline": 300,
# }

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES: List[int] = []
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

RETRY_TIMES = 10
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]

# Playwright settings
DOWNLOAD_HANDLERS = {
    "http": "ozon_collector.handlers.CombinedDownloadHandler",
    "https": "ozon_collector.handlers.CombinedDownloadHandler",
}

# The browser type to be launched, e.g. chromium, firefox, webkit.
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30 * 1000  # 30 seconds

BROWSER_PROFILE_STORAGE_DIR = get_browser_profile_storage()
GOOGLE_CHROME_EXECUTABLE_PATH = get_chrome_executable_path()

J2_TEMPLATES_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__))) / "spiders" / "j2_templates"
assert J2_TEMPLATES_DIR.exists()


def should_abort_request(request: Request) -> bool:
    """Check if the request should be aborted based on URL and resource type."""

    # Define a list of URL prefixes to block
    blocked_urls = [
        "https://sentry.ozon.ru",
        "https://data.ozon.ru/app/csp-report?",
        "https://cdns.ozon.ru/v1/mc",
        "https://cdns.ozon.ru/v1/lg",
        "https://xapi.ozon.ru/dlte/multi",
    ]

    # Block requests based on resource type (e.g., images)
    if request.resource_type == "image":
        logger.debug(f"Blocked image request: {request.url}")
        return True

    # Check if the request URL matches any of the blocked URL prefixes
    for blocked_url in blocked_urls:
        if request.url.startswith(blocked_url):
            logger.debug(f"Blocked request: {request.url}")
            return True

    # Optionally, log requests that aren't blocked for monitoring
    logger.debug(f"Allowed request: {request.url}")

    # If no conditions match, allow the request
    return False


# https://github.com/scrapy-plugins/scrapy-playwright?tab=readme-ov-file#playwright_abort_request
PLAYWRIGHT_ABORT_REQUEST = should_abort_request
