from importer.framework.provider import CSVProvider
from importer.framework.parser import utils
from importer.framework.mapper import DataMapper

AVAILABILITY_MATRIX = {'n': False, 'no': False, 'not in stock': False}

class ZanoxMapper(DataMapper):
    def get_product_id(self):
        return self.record.get('MerchantProductNumber')

    def get_product_name(self):
        return self.record.get('ProductName')

    def get_product_url(self):
        return self.record.get('ZanoxProductLink')

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('ExtraTextOne', ''))]

    def get_gender(self):
        gender = self.map_gender(self.record.get('MerchantProductCategory', ''))
        if not gender:
            extra = self.record.get('ExtraTextOne', '')
            if extra:
                if extra.find('W') != -1:
                    return 'W'
                if extra.find('M') != -1:
                    return 'M'

        return gender

    def get_discount_price(self):
        price = self.record.get('ProductPriceOld')
        if price:
            return self.record.get('ProductPrice')

        return None

    def get_price(self):
        price = self.record.get('ProductPriceOld')
        if price:
            return price

        return self.record.get('ProductPrice')
        
    def get_currency(self):
        return self.record.get('CurrencySymbolOfPrice')

    def get_manufacturer(self):
        return self.record.get('ProductManufacturerBrand')

    def get_description(self):
        return self.record.get('ProductShortDescription')

    def get_category(self):
        return self.record.get('MerchantProductCategory')

    def get_availability(self):
        return None

    def get_image_url(self):
        return [(self.record.get('ImageLargeURL', '') or self.record.get('ImageMediumURL', ''), self.IMAGE_SMALL)]

class Provider(CSVProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=ZanoxMapper
        self.dialect=None # breaks if CSVStandard is used or a sniffed dialect
