from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

class SaksMapper(LinkshareMapper):
    pass

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper = SaksMapper
        self.unique_fields = []
