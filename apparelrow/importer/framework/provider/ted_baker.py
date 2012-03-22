from importer.framework.mapper import expand_entities
from importer.framework.provider.affiliatewindow import AffiliateWindowMapper, Provider as AffiliateWindowProvider

class TedBakerMapper(AffiliateWindowMapper): 

    def get_image_url(self):
        image = self.record.get('merchant_image_url', '')
        return [(image.replace('feedimg', 'zoom'), self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

    def get_product_name(self):
        product_name = expand_entities(self.record.get('product_name'))
        product_name_parts = product_name.split(' - ')
        if len(product_name_parts) > 2:
            return ' - '.join(product_name_parts[1:])
        
        return product_name

class Provider(AffiliateWindowProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=TedBakerMapper
