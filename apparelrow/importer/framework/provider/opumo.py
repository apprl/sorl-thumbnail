from importer.framework.provider.linkshare import LinkshareMapper, Provider as LinkshareProvider

class OpumoMapper(LinkshareMapper):
    def get_gender(self):
        gender = self.map_gender(self.record.get('gender', ''))
        if not gender:
            gender = self.map_gender(self.record.get('category', ''))
            if not gender:
                gender = self.map_gender(self.record.get('keywords', ''))

        return gender

    def get_category(self):
        category = self.record.get('category')

        gender = self.get_gender()
        if gender:
            category = '%s > %s' % (gender, category)

        if self.record.get('secondary-category'):
            subcategory = self.record.get('secondary-category')
            subcategory = subcategory.split('~~', 1)
            category += ' > %s' % (subcategory[0],)

        return category

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper = OpumoMapper
        self.unique_fields = []
