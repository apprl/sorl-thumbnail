from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

class HarrodsMapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        large_image = image.replace('_main_', '_zoom_')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=HarrodsMapper
