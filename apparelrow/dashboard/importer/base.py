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

    def _get_user_and_cuts(self, data):
        user = None
        try:
            user = get_user_model().objects.get(pk=data['user_id'])
            if user.partner_group:
                try:
                    cuts = user.partner_group.cuts.get(vendor=data['vendor'])
                    logger.debug('Using non-default cut for user %s: %s' % (user, cuts))
                    return user, cuts.cut, cuts.referral_cut
                except:
                    pass
        except get_user_model().DoesNotExist():
            pass

        return user, decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT), decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)

    def calculate_cut(self, data):
        if 'user_id' in data and data['user_id']:
            logger.debug('Running calculate cut for user id: %s' % (data['user_id'],))

            user, cut, referral_cut = self._get_user_and_cuts(data)

            self.create_referral_sale(data, user, referral_cut)

            data['commission'] = cut * decimal.Decimal(data['commission'])
            if data['currency'] != data['original_currency']:
                data['commission'] = data['commission'] * decimal.Decimal('0.95')

        return data

    def create_referral_sale(self, data, user, referral_cut):
        if user and user.is_referral_parent_valid():
            temp_data = data.copy()

            temp_data['original_sale_id'] = '%s-%s' % (temp_data['original_sale_id'], user.referral_partner_parent_id)
            temp_data['is_referral_sale'] = True
            temp_data['referral_user'] = user
            temp_data['user_id'] = user.referral_partner_parent_id

            temp_data['commission'] = referral_cut * decimal.Decimal(temp_data['commission'])
            if temp_data['currency'] != temp_data['original_currency']:
                temp_data['commission'] = temp_data['commission'] * decimal.Decimal('0.95')

            instance, created = get_model('dashboard', 'Sale').objects.get_or_create(original_sale_id=temp_data['original_sale_id'], defaults=temp_data)
            if created:
                logger.debug('Created referral sale object: %s' % (instance,))

    def exchange_commission(self, data, instance):
        # Do not update if the original commission value is unchanged.
        if instance is not None and data['original_commission'] == instance.original_commission:
            return False, data

        # Use saved exchange rate if we need to update
        if instance and instance.exchange_rate:
            exchange_rate = instance.exchange_rate
        else:
            exchange_rate = currency_exchange('EUR', data['original_currency'])

        data['exchange_rate'] = exchange_rate
        data['converted_commission'] = exchange_rate * data['original_commission']
        data['converted_amount'] = exchange_rate * data['original_amount']
        data['commission'] = exchange_rate * data['original_commission']
        data['amount'] = exchange_rate * data['original_amount']
        data['currency'] = 'EUR'

        return True, data

    def map_vendor(self, vendor_string):
        if vendor_string:
            closest_match, score = process.extractOne(vendor_string, self.vendor_map.keys())
            if score > 50:
                return closest_match, self.vendor_map[closest_match]

        return None, None

    def map_placement_and_user(self, sid):
        return parse_sid(sid)
