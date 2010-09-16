from importer.framework.provider import Provider as ProviderBase


class Provider(ProviderBase):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.extension = 'csv'
    
    def process(self, **kwargs):
        pass

