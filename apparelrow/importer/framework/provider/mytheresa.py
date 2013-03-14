import re

from apparelrow.importer.framework.provider.linkshare import Provider as LinkshareProvider, LinkshareMapper

class Mapper(LinkshareMapper):

    def get_image_url(self):
        image = self.record.get('image-url', '')
        large_image = re.sub(r'(\d+x\d+)', '1000x1000', image).replace('small_image', 'image')

        return [(large_image, self.IMAGE_MEDIUM), (image, self.IMAGE_SMALL)]

    def get_color(self):
        colors = super(Mapper, self).get_color()
        # If no colors have been found, search the description as well
        if len(colors) == 1:
            colors.extend(self.map_colors(self.record.get('description', '')))
        return colors

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=Mapper

