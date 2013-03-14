import re

from apparelrow.importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

class Mapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        large_image = image.replace('S1', 'S6')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

    def get_category(self):
        category = super(Mapper, self).get_category()
        if self.record.get('type'):
            category += ' > %s' % self.record.get('type')

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=Mapper
