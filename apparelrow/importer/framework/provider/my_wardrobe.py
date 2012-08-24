from importer.framework.provider.zanox import ZanoxMapper, Provider as ZanoxProvider

class MyWardrobeMapper(ZanoxMapper):

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('ExtraTextThree', ''))]

class Provider(ZanoxProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=MyWardrobeMapper
