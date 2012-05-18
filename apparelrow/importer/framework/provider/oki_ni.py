from importer.framework.provider.affiliatewindow import AffiliateWindowMapper, Provider as AffiliateWindowProvider

class OkiNiMapper(AffiliateWindowMapper):
    pass

class Provider(AffiliateWindowProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=OkiNiMapper
        self.unique_fields = None
