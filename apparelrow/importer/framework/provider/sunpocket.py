from apparelrow.importer.framework.provider.cj import CJMapper, Provider as CJProvider

class SunpocketMapper(CJMapper):
    pass

class Provider(CJProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=SunpocketMapper
        self.unique_fields = ['product-id']
