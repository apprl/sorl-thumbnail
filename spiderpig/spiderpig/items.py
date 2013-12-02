import string

from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Identity, Compose, MapCompose
from scrapy.item import Item, Field


class ProductLoader(XPathItemLoader):
    default_output_processor = Compose(MapCompose(string.strip), TakeFirst())

    image_urls_out = Identity()


class Product(Item):
    key = Field()
    sku = Field()
    name = Field()
    description = Field()
    brand = Field()
    category = Field()
    gender = Field()
    vendor = Field()

    url = Field()
    affiliate = Field()

    regular_price = Field()
    discount_price = Field()
    currency = Field()

    colors = Field()

    in_stock = Field()
    stock = Field()

    image_urls = Field()
    images = Field()
