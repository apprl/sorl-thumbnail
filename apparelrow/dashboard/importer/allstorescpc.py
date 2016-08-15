import dateutil
import decimal
import logging
import datetime
from django.db import connection
from apparelrow.dashboard.importer.base import BaseImporter
from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.models import Cut, Sale
from apparelrow.profile.models import User
from progressbar import ProgressBar, Percentage, Bar

logger = logging.getLogger('dashboard')


class Importer(BaseImporter):
    name = 'Cost per Click All Stores'

    def get_cpc_clicks_per_vendor_per_user(self, start_date, end_date):
        values = [start_date, end_date]
        cursor = connection.cursor()
        cursor.execute(
            """(SELECT PS.vendor, PS.user_id, count(PS.id)
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND U.is_partner = True AND PS.vendor = V.name AND PS.is_valid = True
               AND PS.created BETWEEN %s AND %s
               GROUP BY PS.user_id, PS.vendor
               )""", values)
        data = cursor.fetchall()
        return data

    def get_data(self, start_date, end_date, **kwargs):
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(start_date, datetime.time(23, 59, 59, 999999))
        logger.info("Importing Cost per Click data from %s until %s" % (start_date_query, end_date_query))
        data = self.get_cpc_clicks_per_vendor_per_user(start_date_query, end_date_query)
        pbar = None
        maxval = len(data)
        if kwargs.get('verbose', None) and maxval:
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=maxval).start()

        for index, (vendor_id, user_id, count) in enumerate(data):
            if pbar:
                pbar.update(index)
            try:
                user = None
                if user_id != 0:
                    user = User.objects.get(id=user_id)

                if user and user.is_partner and user.partner_group.has_cpc_all_stores:
                    sale = {}
                    vendor = Vendor.objects.get(name=vendor_id)
                    cut = Cut.objects.get(vendor=vendor, group=user.partner_group)
                    sale['original_sale_id'] = "cpc_"+str(end_date_query.date())+"_"+str(user.id)+"_"+str(vendor.id)
                    sale['affiliate'] = "cpc_all_stores"
                    sale['original_commission'] = cut.cpc_amount * count
                    sale['original_amount'] = cut.cpc_amount * count
                    sale['original_currency'] = cut.cpc_currency
                    sale['cut'] = 1
                    sale['vendor'] = vendor
                    sale['user_id'] = user.id
                    sale['placement'] = "Cost per click All Stores"
                    sale['sale_date'] = dateutil.parser.parse('%s' % start_date_query)
                    sale['status'] = Sale.PENDING
                    sale['adjusted_date'] = dateutil.parser.parse('%s' % datetime.date.today())
                    sale['type'] = Sale.COST_PER_CLICK
                    sale = self.validate(sale)
                    if not sale:
                        continue
                    yield sale
            except User.DoesNotExist:
                logger.warn('User %s does not exist' % user_id)
            except Vendor.DoesNotExist:
                logger.warn('Vendor %s does not exist' % vendor_id)
            except Cut.DoesNotExist:
                logger.warn('Cut for vendor %s and commission group for user %s does not exist' % (vendor_id, user_id))
        if pbar:
            pbar.finish()