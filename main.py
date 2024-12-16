"""Ozon Search Queries Collector.

This script is the entry point for running the Ozon search queries collector spider.
It configures the Scrapy project settings dynamically, initializes the crawler, and
executes the `OzonDataQuerySpider`.
"""

from rich import print
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from ozon_collector.spiders.OzonDataQuerySpider import OzonDataQuerySpider

if __name__ == "__main__":

    def main() -> None:
        settings = get_project_settings()
        print(settings.copy_to_dict())

        # Enhance settings dynamically
        settings.set("CONCURRENT_REQUESTS", 1)
        settings.set("PLAYWRIGHT_BROWSER_TYPE", "chromium")

        process = CrawlerProcess(settings=settings)
        process.crawl(OzonDataQuerySpider, initial_keyword="сыр")
        process.start()

    main()
