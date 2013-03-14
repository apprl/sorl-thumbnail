import os.path

from apparelrow.importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class ForzieriMapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        parts = image.partition('Forzieri/')
        large_image = parts[0] + parts[1] + os.path.splitext(os.path.basename(parts[2]))[0] + '?scl=1.5'

        return [(large_image, self.IMAGE_MEDIUM), (image, self.IMAGE_SMALL)]

    def get_category(self):
        category = super(ForzieriMapper, self).get_category()
        if self.record.get('type'):
            category += ' > %s' % self.record.get('type')

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=ForzieriMapper
