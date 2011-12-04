from importer.framework.mapper import expand_entities
from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class ForzieriMapper(LinkshareMapper):

    def get_category(self):
        category = self.record.get('category')
        gender = self.get_gender()
        if gender:
            category = '%s > %s' % (gender, category)

        if self.record.get('secondary-category'):
            category += ' > %s' % self.record.get('secondary-category')
        if self.record.get('type'):
            category += ' > %s' % self.record.get('type')

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=ForzieriMapper
