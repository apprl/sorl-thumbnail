from django.db.models.loading import get_model
from fuzzywuzzy import process

class BaseImporter:

    def __init__(self):
        self.vendors = get_model('apparel', 'Vendor').objects.all()
        self.vendor_map = dict(((x.name, x) for x in self.vendors))

    def map_vendor(self, vendor_string):
        closest_match, score = process.extractOne(vendor_string, self.vendor_map.keys())
        if score > 50:
            return closest_match, self.vendor_map[closest_match]

        return None

    def map_placement_and_user(self, sid):
        if sid:
            sid_split = sid.split('-', 1)
            if len(sid_split) != 2:
                return (0, 'Unknown')

            return int(sid_split[0]), sid_split[1]

        return (0, 'Unknown')
