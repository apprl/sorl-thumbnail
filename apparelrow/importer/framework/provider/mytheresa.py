from importer.framework.provider.linkshare import Provider as LinkshareProvider, LinkshareMapper
class MyTheresaMapper(LinkshareMapper):
    def get_color(self):
        colors = super(MyTheresaMapper, self).get_color()
        # If no colors have been found, search the description as well
        if len(colors) == 1:
            colors.extend(self.map_colors(self.record.get('description', '')))
        return colors

class Provider(LinkshareProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=MyTheresaMapper

