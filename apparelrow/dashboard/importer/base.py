import datetime
import math
import decimal
import dateutil.parser
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.loading import get_model
from fuzzywuzzy import process

from apparelrow.dashboard.models import Sale
from apparelrow.apparel.utils import currency_exchange, parse_sid


logger = logging.getLogger('dashboard.import')


class BaseImporter:

    def __init__(self):
        self.vendors = get_model('apparel', 'Vendor').objects.all()
        self.vendor_map = dict(((x.name, x) for x in self.vendors))

    def parse_to_utc(self, dtstr):
        """
        Fails for naive datetimes
        """
        dt = dateutil.parser.parse(dtstr)
        if dt.tzinfo:
            dt = dt.astimezone(dateutil.tz.tzutc())

        return dt

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

        # XXX: Make sure dates are not timezone aware. Date might be a bit off
        # and should be fixed in the future for affected importers
        if 'sale_date' in data:
            data['sale_date'] = data['sale_date'].replace(tzinfo=None)
        if 'adjusted_date' in data:
            data['adjusted_date'] = data['adjusted_date'].replace(tzinfo=None)

        if instance is None:
            try:
                instance = Sale.objects.get(original_sale_id=data['original_sale_id'])
            except Sale.DoesNotExist:
                pass

        update, data = self.exchange_commission(data, instance)
        if update:
            data = self.calculate_cut(data)

        return data

    def calculate_cut(self, data):
        if 'user_id' in data and data['user_id']:
            cut = settings.APPAREL_DASHBOARD_CUT_DEFAULT
            profile = get_user_model().objects.filter(pk=data['user_id'])
            if profile:
                profile = profile[0]
                if profile.partner_group:
                    instance = profile.partner_group.cuts.filter(vendor=data['vendor'])
                    if instance:
                        cut = instance[0].cut
                        logger.debug('Using custom cut for profile %s: %s' % (profile, cut))

            data['commission'] = decimal.Decimal('0.95') * decimal.Decimal(cut) * decimal.Decimal(data['commission'])

        return data


    def exchange_commission(self, data, instance):
        # Do not update if the original commission value is unchanged.
        if instance is not None and data['original_commission'] == instance.original_commission:
            return False, data

        # Use saved exchange rate if we need to update
        if instance and instance.exchange_rate:
            exchange_rate = instance.exchange_rate
        else:
            exchange_rate = currency_exchange('SEK', data['original_currency'])

        data['exchange_rate'] = exchange_rate
        data['converted_commission'] = exchange_rate * data['original_commission']
        data['converted_amount'] = exchange_rate * data['original_amount']
        data['commission'] = exchange_rate * data['original_commission']
        data['amount'] = exchange_rate * data['original_amount']
        data['currency'] = 'SEK'

        return True, data

    def map_vendor(self, vendor_string):
        closest_match, score = process.extractOne(vendor_string, self.vendor_map.keys())
        if score > 50:
            return closest_match, self.vendor_map[closest_match]

        return None, None

    def map_placement_and_user(self, sid):
        return parse_sid(sid)
