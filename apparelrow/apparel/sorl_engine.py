from sorl.thumbnail.engines.pil_engine import Engine as PILEngine

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
