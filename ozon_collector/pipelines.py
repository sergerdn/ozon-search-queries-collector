# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.spiders import Spider

from ozon_collector.items import OzonCollectorItem

# useful for handling different item types with a single interface
# from itemadapter import ItemAdapter


class OzonCollectorPipeline:
    # noinspection PyMethodMayBeStatic
    def process_item(self, item: OzonCollectorItem, spider: Spider) -> OzonCollectorItem:
        return item
