from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.engines.pil_engine import Engine as PILEngine

import os.path
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
        path, filename = os.path.split(source.name)
        paths = path.split('/')
        if paths[1] != 'products' or len(paths) < 4:
            # No brand name in path should use old thumbnail_name algorithm
            return super(NamedThumbnailBackend, self)._get_thumbnail_filename(source, geometry_string, options)

        key = tokey(source.key, geometry_string, serialize(options))
        return '%s%s/%s/%s' % (settings.THUMBNAIL_PREFIX, key, paths[-1], filename)
