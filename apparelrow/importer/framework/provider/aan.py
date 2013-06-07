import logging

from apparelrow.importer.framework.provider import Provider as BaseProvider
from apparelrow.importer.framework.mapper import DataMapper

logger = logging.getLogger('apparel.importer')

class AanMapper(DataMapper):
    pass

class Provider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=AanMapper
