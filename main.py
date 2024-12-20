"""Ozon Search Queries Collector.

This script is the entry point for running the Ozon search queries collector spider.
It configures the Scrapy project settings dynamically, initializes the crawler, and
executes the `OzonDataQuerySpider`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from rich import print
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from ozon_collector.spiders.OzonDataQuerySpider import OzonDataQuerySpider

if __name__ == "__main__":
    ABS_PATH: Path = Path(os.path.dirname(os.path.abspath(__file__)))
    enf_filename = ABS_PATH / ".env.development"
    assert enf_filename.exists()
    load_dotenv(enf_filename)

    def main() -> None:
        settings = get_project_settings()
        print(settings.copy_to_dict())

        # Enhance settings dynamically
        settings.set("CONCURRENT_REQUESTS", 1)
        settings.set("PLAYWRIGHT_BROWSER_TYPE", "chromium")
        settings.set("DEPTH_LIMIT", 1)

        process = CrawlerProcess(settings=settings)
        process.crawl(
            OzonDataQuerySpider,
            initial_query_keyword="сыр",
            parse_in_depth=True,
            query_popularity_threshold=0,
        )
        process.start()

    main()
