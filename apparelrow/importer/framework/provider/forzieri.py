import os.path

from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class ForzieriMapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        parts = image.partition('Forzieri/')
        large_image = parts[0] + parts[1] + os.path.splitext(os.path.basename(parts[2]))[0] + '?scl=1.5'

        return [(large_image, self.IMAGE_MEDIUM), (image, self.IMAGE_SMALL)]

    def get_category(self):
        category = self.record.get('category')
        gender = self.get_gender()
        if gender:
            category = '%s > %s' % (gender, category)

        if self.record.get('secondary-category'):
            category += ' > %s' % self.record.get('secondary-category')
        if self.record.get('type'):
            category += ' > %s' % self.record.get('type')

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=ForzieriMapper
