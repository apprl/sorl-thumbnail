import json

from scrapy.exceptions import DropItem

from theimp.models import Product

class StockPipeline:
    def process_item(self, item, spider):
        item['in_stock'] = item.get('in_stock', False)

        return item

class PricePipeline:

    def process_item(self, item, spider):
        price = item.get('price', None)
        currency = item.get('currency', None)
        in_stock = item.get('in_stock', None)

        if price:
            price_parts = price.rsplit(' ', 1)
            if len(price_parts) == 1 and not currency:
                raise DropItem('Missing currency in %s' % item)

            if len(price_parts[1]) != 3:
                raise DropItem('Could not parse currency some price in %s' % item)

            # TODO: better handling of currency?

            item['price'] = price_parts[0]
            item['currency'] = price_parts[1]

            return item
        elif in_stock == False:
            item['price'] = u''
            item['currency'] = u''

            return item
        else:
            raise DropItem('Missing price and no in_stock information in %s' % item)

class PushJSONPipeline:
    def process_item(self, item, spider):
        json_string = json.dumps(dict(item))

        product, created = Product.objects.get_or_create(key=item['identifier'], defaults={'json': json_string})
        if not created:
            product.json = json_string
            product.save()

        print product
