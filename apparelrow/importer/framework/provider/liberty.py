from apparelrow.importer.framework.provider.affiliatewindow import AffiliateWindowMapper, Provider as AffiliateWindowProvider

class LibertyMapper(AffiliateWindowMapper):

    def get_product_name(self):
        name = super(LibertyMapper, self).get_product_name()

        product_name_parts = name.split(' ')
        for index, part in enumerate(reversed(product_name_parts)):
            if part.lower() == 'size' and index <= 2:
                return ' '.join(product_name_parts[:-(index + 1)])

            elif index > 2:
                break

        return name

    def get_image_url(self):
        image = self.record.get('merchant_image_url', '')
        large_image = image.replace('large1', 'enlarge')

        return [(large_image, self.IMAGE_LARGE), (image, self.IMAGE_SMALL)]

class Provider(AffiliateWindowProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=LibertyMapper
