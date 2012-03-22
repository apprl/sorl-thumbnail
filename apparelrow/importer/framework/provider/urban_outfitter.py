from importer.framework.provider.affiliatewindow import AffiliateWindowMapper, Provider as AffiliateWindowProvider

class UrbanOutfitterMapper(AffiliateWindowMapper): 

    def get_image_url(self):
        image = self.record.get('merchant_image_url', '')
        large_image = image.replace('_m', '_l')
        return [(large_image, self.IMAGE_MEDIUM), (image, self.IMAGE_SMALL)]

class Provider(AffiliateWindowProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=UrbanOutfitterMapper
