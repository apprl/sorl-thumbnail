from theimp.parser.modules import BaseModule

from django.db.models.loading import get_model

class BrandMapper(BaseModule):

    def __call__(self, item):
        brand = item['brand']



        print self.parser

        return item
