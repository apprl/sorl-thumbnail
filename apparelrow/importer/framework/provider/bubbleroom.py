from apparelrow.importer.framework.provider.tradedoubler import TradeDoublerMapper, Provider as TradeDoublerProvider

class BubbleroomMapper(TradeDoublerMapper):

    def get_image_url(self):
        image = super(BubbleroomMapper, self).get_image_url()
        large_image = image[0][0].replace('300', '600')

        return [(large_image, self.IMAGE_LARGE)]

    def get_gender(self):
        return self.map_gender(self.record.get('merchantCategoryName', ''))

class Provider(TradeDoublerProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=BubbleroomMapper
