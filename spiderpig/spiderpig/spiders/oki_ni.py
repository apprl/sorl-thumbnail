from scrapy.contrib.spiders import CSVFeedSpider

from spiderpig.spiderpig.items import Product
from spiderpig.spiderpig.spiders import AffiliateMixin


class OkiNiSpider(CSVFeedSpider, AffiliateMixin):
    name = 'oki-ni'
    allowed_domains = ['oki-ni.com']
    start_urls = ['http://datafeed.api.productserve.com/datafeed/download/apikey/993ddcbcf6025953d8d8861233cd2f45/mid/2083/columns/merchant_id,merchant_name,aw_product_id,merchant_product_id,product_name,description,category_id,category_name,merchant_category,aw_deep_link,aw_image_url,search_price,delivery_cost,merchant_deep_link,merchant_image_url,aw_thumb_url,brand_id,brand_name,commission_amount,commission_group,condition,currency,delivery_time,display_price,ean,in_stock,is_hotpick,isbn,is_for_sale,language,merchant_thumb_url,model_number,mpn,parent_product_id,pre_order,product_type,promotional_text,rrp_price,specifications,stock_quantity,store_price,upc,valid_from,valid_to,warranty,web_offer/format/csv/delimiter/|/compression/gzip/']
    delimiter = '|'

    def parse_row(self, response, row):
        item = Product()
        item['key'] = row.get('merchant_deep_link')
        item['sku'] = row.get('merchant_product_id')
        item['name'] = row.get('product_name')
        item['vendor'] = self.name
        item['url'] = row.get('aw_deep_link')
        item['affiliate'] = self.AFFILIATE_AW
        item['category'] = '%s > %s' % (row.get('category_name'), row.get('merchant_category'))
        item['description'] = row.get('description')
        item['brand'] = row.get('brand_name')
        item['gender'] = '%s %s' % (row.get('category_name'), row.get('product_name'))
        item['colors'] = '%s %s' % (row.get('specifications'), row.get('product_name'))
        item['regular_price'] = row.get('rrp_price')
        item['discount_price'] = row.get('search_price')
        item['currency'] = row.get('currency')
        item['in_stock'] = True if str(row.get('in_stock')) == '1' else False
        item['stock'] = row.get('stock_quantity')
        item['image_urls'] = [row.get('merchant_image_url')]

        return item
