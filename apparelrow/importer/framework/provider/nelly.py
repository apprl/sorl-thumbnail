from importer.framework.provider.tradedoubler import TradeDoublerMapper, Provider as TradeDoublerProvider

class NellyMapper(TradeDoublerMapper):

    def get_image_url(self):
        image = self.record.get('extraImageProductLarge', '') or self.record.get('imageUrl', '')
        large_image = image.replace('productLarge', 'productPress')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)] 

class Provider(TradeDoublerProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=NellyMapper
