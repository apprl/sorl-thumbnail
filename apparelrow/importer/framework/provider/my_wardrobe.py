from importer.framework.provider.zanox import ZanoxMapper, Provider as ZanoxProvider
from importer.framework.parser import utils

class MyWardrobeMapper(ZanoxMapper):

    def get_category(self):
        gender = self.record.get('ExtraTextOne', '')
        if gender:
            return '%s > %s' % (gender, self.record.get('MerchantProductCategory'))

        return self.record.get('MerchantProductCategory')

    def get_discount_price(self):
        discount_price = super(MyWardrobeMapper, self).get_discount_price()
        if discount_price:
            return discount_price.replace(',', '.')

        return discount_price

    def get_price(self):
        price = super(MyWardrobeMapper, self).get_price()
        if price:
            return price.replace(',', '.')

        return price

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('ExtraTextThree', ''))]

class Provider(ZanoxProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=MyWardrobeMapper
        self.dialect=utils.CSVSemiColonDelimited
