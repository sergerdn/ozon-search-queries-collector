from rich import print
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from ozon_collector.spiders.BrowserleaksSpider import BrowserleaksSpider

if __name__ == "__main__":
    def main() -> None:
        settings = get_project_settings()
        print(settings.copy_to_dict())

        # Enhance settings dynamically
        settings.set("CONCURRENT_REQUESTS", 2)
        settings.set("DEPTH_LIMIT", 1)

        process = CrawlerProcess(settings=settings)
        process.crawl(BrowserleaksSpider)
        process.start()


    main()
