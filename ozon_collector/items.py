# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class OzonCollectorItem(scrapy.Item):
    """Scrapy Item for collecting Ozon data.

    Represents a single entry in the data with fields corresponding to JSON keys.
    """

    _query_keyword = scrapy.Field()  # keyword
    _scraped_at = scrapy.Field()  # Timestamp of when the data was scraped

    avgCaRub = scrapy.Field()  # Average price, ₽
    avgCountItems = scrapy.Field()  # Products in search results
    ca = scrapy.Field()  # Cart conversion
    count = scrapy.Field()  # Query popularity
    itemsViews = scrapy.Field()  # Product views
    query = scrapy.Field()  # Search query
    uniqQueriesWCa = scrapy.Field()  # Added to cart
    uniqSellers = scrapy.Field()  # Product sellers
