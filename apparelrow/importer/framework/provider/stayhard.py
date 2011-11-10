from importer.framework.mapper import expand_entities
from importer.framework.provider.cj import CJMapper, Provider as CJProvider

# See cj.py

class StayhardMapper(CJMapper): 

    def get_variations(self):
        return [{'color': c} for c in self.map_colors(self.record.get('keywords', ''))]

class Provider(CJProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=StayhardMapper
