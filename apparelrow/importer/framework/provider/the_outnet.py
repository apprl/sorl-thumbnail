from apparelrow.importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class TheOutnetMapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        large_image = image.replace('_in_l', '_in_xl')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=TheOutnetMapper
        self.unique_fields = ['product-id']
