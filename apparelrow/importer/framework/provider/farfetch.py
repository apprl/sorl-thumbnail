from apparelrow.importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class FarfetchMapper(LinkshareMapper): 
    pass

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=FarfetchMapper
