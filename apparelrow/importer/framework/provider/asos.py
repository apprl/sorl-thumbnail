from apparelrow.importer.framework.provider.zanox import ZanoxMapper, Provider as ZanoxProvider

class AsosMapper(ZanoxMapper):

    def get_image_url(self):
        image = self.record.get('ImageLargeURL')
        if image:
            large_image = image.replace('xl.', 'xxl.')
        else:
            image = self.record.get('ImageMediumURL', '')
            large_image = image.replace('l.', 'xxl.')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

class Provider(ZanoxProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=AsosMapper
