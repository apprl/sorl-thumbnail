import datetime
import math
import decimal

from django.conf import settings
from django.db.models.loading import get_model
from fuzzywuzzy import process

from dashboard.models import Sale
from apparel.utils import currency_exchange

class BaseImporter:

    def __init__(self):
        self.vendors = get_model('apparel', 'Vendor').objects.all()
        self.vendor_map = dict(((x.name, x) for x in self.vendors))

    def generate_subdates(self, start_date, end_date, max_days=30):
        days = (end_date - start_date).days
        intervals = max(1, int(math.ceil(days / float(max_days))))

        new_start_date = start_date
        for days in range(intervals):
            new_end_date = new_start_date + datetime.timedelta(days=max_days)
            new_end_date = min(new_end_date, end_date)
            yield new_start_date, new_end_date
            new_start_date = new_end_date

    def validate(self, data, instance=None):
        """
        Validate a data dictionary and ready it for inseration in the sale
        transasction database.
        """
        if 'original_sale_id' not in data:
            return False

        try:
            data['original_commission'] = decimal.Decimal(data['original_commission'])
            data['original_amount'] = decimal.Decimal(data['original_amount'])
        except (TypeError, decimal.InvalidOperation) as e:
            return False

        if instance is None:
            try:
                instance = Sale.objects.get(original_sale_id=data['original_sale_id'])
            except Sale.DoesNotExist:
                pass

        data = self.exchange_commission(data, instance)

        if 'user_id' in data and data['user_id']:
            cut = settings.APPAREL_DASHBOARD_CUT_DEFAULT
            profile = get_model('profile', 'ApparelProfile').objects.filter(user=data['user_id'])
            if profile:
                profile = profile[0]
                if profile.partner_group:
                    instance = profile.partner_group.cuts.filter(vendor=data['vendor'])
                    if instance:
                        cut = instance[0].cut

            data['commission'] = decimal.Decimal(cut) * decimal.Decimal(data['commission'])

        return data

    def exchange_commission(self, data, instance):
        # Do not update commission if status is CONFIRMED or higher and the
        # original commission value is unchanged.
        if instance is not None and \
           instance.status != data['status'] and \
           data['status'] >= Sale.CONFIRMED and \
           data['original_commission'] == instance.original_commission:
            return data

        exchange_rate = currency_exchange('SEK', data['original_currency'])
        exchange_rate_modifier = decimal.Decimal(0.95)

        data['commission'] = exchange_rate * exchange_rate_modifier * data['original_commission']
        data['amount'] = exchange_rate * exchange_rate_modifier * data['original_amount']
        data['currency'] = 'SEK'

        return data

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
