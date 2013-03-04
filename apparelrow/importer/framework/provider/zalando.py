from importer.framework.provider.zanox import ZanoxMapper, Provider as ZanoxProvider

class ZalandoMapper(ZanoxMapper):

    def get_image_url(self):
        image = self.record.get('ImageLargeURL', '') or self.record.get('ImageMediumURL', '')
        large_image = image.replace('detail', 'large')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('ExtraTextTwo', ''))]

class Provider(ZanoxProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=ZalandoMapper
