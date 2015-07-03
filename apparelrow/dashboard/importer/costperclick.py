import dateutil
import decimal
import logging
import datetime
from django.db import connection
from apparelrow.dashboard.importer.base import BaseImporter
from django.db.models.loading import get_model
from django.contrib.auth import get_user_model

logger = logging.getLogger('dashboard')


class Importer(BaseImporter):
    name = 'Cost per Click'

    def get_cpc_clicks_per_vendor_per_user(self, start_date, end_date):
        values = [start_date, end_date, start_date, end_date]
        cursor = connection.cursor()
        cursor.execute(
            """(SELECT PS.vendor, PS.user_id, count(PS.id)
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND U.is_partner = True AND  PS.vendor = V.name AND V.is_cpc = True
               AND PS.created BETWEEN %s AND %s
               GROUP BY PS.user_id, PS.vendor)
               UNION
               (SELECT PS.vendor, PS.user_id, count(PS.id)
               FROM statistics_productstat PS, apparel_vendor V
               WHERE PS.user_id=0 AND  PS.vendor = V.name AND V.is_cpc = True
               AND PS.created BETWEEN %s AND %s
               GROUP BY PS.user_id, PS.vendor)""", values)
        data = cursor.fetchall()
        return data

    def get_click_cost(self, vendor):
        try:
            click = get_model('dashboard', 'ClickCost').objects.get(vendor=vendor)
            return click.amount, click.currency
        except get_model('dashboard', 'ClickCost').DoesNotExist:
            logger.warn('ClickCost for vendor %s does not exist'%(vendor))
        return None, None

    def get_data(self, start_date, end_date, **kwargs):
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(start_date, datetime.time(23, 59, 59, 999999))
        logger.info("Importing Cost per Click data from %s until %s" % (start_date_query, end_date_query))
        data = self.get_cpc_clicks_per_vendor_per_user(start_date_query, end_date_query)
        for (vendor_id, user_id, count) in data:
            try:
                user = None
                if user_id != 0:
                    user = get_user_model().objects.get(id=user_id)
                vendor = get_model('apparel', 'Vendor').objects.get(name=vendor_id)
                if (user and user.is_partner) or user_id == 0:
                    click_cost, currency = self.get_click_cost(vendor)
                    if click_cost and currency:
                        sale = {}
                        sale['original_sale_id'] = "cpc_"+str(start_date)+"_"+str(user_id)+"_"+str(vendor_id)
                        sale['affiliate'] = "cost_per_click"
                        sale['vendor'] = vendor
                        sale['original_commission'] = click_cost * count
                        sale['original_amount'] = click_cost * count
                        sale['original_currency'] = currency
                        sale['user_id'] = user_id
                        sale['placement'] = "Cost per click"
                        sale['sale_date'] = dateutil.parser.parse('%s' % start_date_query)
                        sale['status'] = get_model('dashboard', 'Sale').PENDING
                        sale['adjusted_date'] = dateutil.parser.parse('%s'%datetime.date.today())
                        sale['type'] = get_model('dashboard', 'Sale').COST_PER_CLICK
                        try:
                            store = get_model('advertiser', 'Store').objects.get(vendor=vendor)
                            sale['store_id'] = store.identifier

                        except get_model('advertiser', 'Store').DoesNotExist:
                            sale['store_id'] = None
                        sale = self.validate(sale)
                        if not sale:
                            continue
                        yield sale
            except get_user_model().DoesNotExist:
                logger.warn('User %s does not exist' % user_id)
            except get_model('apparel', 'Vendor').DoesNotExist:
                logger.warn('Vendor %s does not exist' % vendor_id)