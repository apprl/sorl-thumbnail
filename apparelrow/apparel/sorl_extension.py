from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.engines.pil_engine import Engine as PILEngine

from os.path import basename
from django.conf import settings
from sorl.thumbnail.helpers import tokey, serialize

class Engine(PILEngine):
    def create(self, image, geometry, options):
        image = super(PILEngine, self).create(image, geometry, options)
        image = self.transparent(image, geometry, options)
        return image

    def transparent(self, image, geometry, options):
        if options.get('transparent', None):
            image = image.convert('RGBA')
            if image.mode == 'RGBA':
                pixels = image.load()
                for y in range(image.size[1]):
                    for x in range(image.size[0]):
                        if pixels[x, y] == (255, 255, 255, 255):
                            pixels[x, y] = (255, 255, 255, 0)

        return image

class NamedThumbnailBackend(ThumbnailBackend):
    def _get_thumbnail_filename(self, source, geometry_string, options):
        filename = basename(source.name)

        if filename[0:2] != '__':
            # Images with product name as file name always start with __
            return super(NamedThumbnailBackend, self)._get_thumbnail_filename(source, geometry_string, options)

        key = tokey(source.key, geometry_string, serialize(options))
        path = '%s/%s/%s' % (key[:2], key[2:4], key)
        return '%s%s/%s' % (settings.THUMBNAIL_PREFIX, path, filename)
