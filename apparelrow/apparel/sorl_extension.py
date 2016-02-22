from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.engines.pil_engine import Engine as PILEngine

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    import Image, ImageDraw, ImageOps

import os.path
from os.path import basename
from django.conf import settings
from sorl.thumbnail.helpers import tokey, serialize


ADOBE_TO_XYZ = (
    0.57667, 0.18556, 0.18823, 0,
    0.29734, 0.62736, 0.07529, 0,
    0.02703, 0.07069, 0.99134, 0,
)

XYZ_TO_SRGB = (
    3.2406, -1.5372, -0.4986, 0,
    -0.9689, 1.8758, 0.0415, 0,
    0.0557, -0.2040, 1.0570, 0,
)


def adobe_to_srgb(image):
    return image.convert('RGB', ADOBE_TO_XYZ).convert('RGB', XYZ_TO_SRGB)


def is_adobe_rgb(image):
    return 'Adobe RGB' in image.info.get('icc_profile', '')


def preserve_adobe_rgb(image, **kwargs):
    if is_adobe_rgb(image):
        return adobe_to_srgb(image)
    return image


class Engine(PILEngine):
    def create(self, image, geometry, options):
        image = super(PILEngine, self).create(image, geometry, options)
        image = preserve_adobe_rgb(image)
        image = self.transparent(image, geometry, options)
        return image

    def scale(self, image, geometry, options):
        keep_size = options.get('keep_size', False)
        if keep_size:
            is_collage = options.get('is_collage', False)
            return self._keep_size(image, geometry, is_collage)

        return super(PILEngine, self).scale(image, geometry, options)

    def _keep_size(self, image, geometry, is_collage=False):
        empty_image = Image.new('RGBA', (geometry[0], geometry[1]), (255, 255, 255, 0))
        empty_image_w, empty_image_h = empty_image.size

        image.thumbnail((geometry[0], geometry[1]), resample=Image.ANTIALIAS)
        image_w, image_h = image.size

        if is_collage:
            image_draw = ImageDraw.Draw(image)
            image_draw.rectangle(((0,0), (image_w - 1, image_h - 1)), outline=(238, 238, 238, 255))
            del image_draw

        offset = ((empty_image_w - image_w) / 2, (empty_image_h - image_h) / 2)
        empty_image.paste(image, offset)

        return empty_image

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


class CustomCircularEngine(PILEngine):
    def create(self, image, geometry, options):
        image = super(PILEngine, self).create(image, geometry, options)
        image = self.circular(image, geometry, options)
        return image

    def circular(self, image, geometry, options):
        # Create circular mask, super size to then resize with antialiasing
        bigsize = (geometry[0]*3, geometry[1]*3)
        mask = Image.new('L', bigsize, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask.resize(geometry, Image.ANTIALIAS)

        # Resize image
        output = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        return output


class NamedThumbnailBackend(ThumbnailBackend):
    def _get_thumbnail_filename(self, source, geometry_string, options):
        path, filename = os.path.split(source.name)
        paths = path.split('/')
        if len(paths) < 4 or paths[1] != 'products':
            # No brand name in path should use old thumbnail_name algorithm
            return super(NamedThumbnailBackend, self)._get_thumbnail_filename(source, geometry_string, options)

        key = tokey(source.key, geometry_string, serialize(options))
        return '%s%s/%s/%s' % (settings.THUMBNAIL_PREFIX, key, paths[-1], filename)
