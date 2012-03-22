from importer.framework.provider.cj import CJMapper, Provider as CJProvider

class LuisaviaromaMapper(CJMapper): 

    def get_image_url(self):
        image = self.record.get('imageurl', '')
        large_image = image.replace('Small', 'Big')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

class Provider(CJProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=LuisaviaromaMapper
