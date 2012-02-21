from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

# See linkshare.py

class MatchesMapper(LinkshareMapper): 

    def get_product_name(self):
        return self.record.get('description')

    def get_category(self):
        category = self.record.get('category')

        if self.record.get('secondary-category'):
            category += ' > %s' % self.record.get('secondary-category')

        if self.record.get('gender'):
            category = '%s > %s' % (self.record.get('gender'), category)

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=MatchesMapper
        self.unique_fields = ['product-id']
