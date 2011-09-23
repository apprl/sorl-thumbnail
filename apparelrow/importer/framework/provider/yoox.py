from importer.framework.provider.zanox import ZanoxMapper, Provider as ZanoxProvider

class YooxMapper(ZanoxMapper):
    def get_product_name(self):
        return self.get_manufacturer()

class Provider(ZanoxProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=YooxMapper
        self.unique_fields = None
