import dateutil
import logging
import datetime
from django.db import connection
from progressbar import ProgressBar, Percentage, Bar
from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.importer.base import BaseImporter
from apparelrow.dashboard.models import Cut, ClickCost, Sale
from apparelrow.profile.models import User

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
               AND PS.is_valid = True AND PS.created BETWEEN %s AND %s
               GROUP BY PS.user_id, PS.vendor)
               UNION
               (SELECT PS.vendor, PS.user_id, count(PS.id)
               FROM statistics_productstat PS, apparel_vendor V
               WHERE PS.user_id=0 AND  PS.vendor = V.name AND V.is_cpc = True
               AND PS.is_valid = True AND PS.created BETWEEN %s AND %s
               GROUP BY PS.user_id, PS.vendor)""", values)
        data = cursor.fetchall()
        return data

    def get_click_cost(self, vendor):
        try:
            click = ClickCost.objects.get(vendor=vendor)
            return click.amount, click.currency
        except ClickCost.DoesNotExist:
            logger.warn('ClickCost for vendor %s does not exist'%(vendor))
        return None, None

    def get_data(self, start_date, end_date, **kwargs):
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(start_date, datetime.time(23, 59, 59, 999999))
        logger.info("Importing Cost per Click data from %s until %s" % (start_date_query, end_date_query))
        data = self.get_cpc_clicks_per_vendor_per_user(start_date_query, end_date_query)
        maxval = len(data)
        pbar = None
        if kwargs.get('verbose', None) and maxval:
            pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=maxval).start()

        for index, (vendor_id, user_id, count) in enumerate(data):
            if pbar:
                pbar.update(index)
            try:
                vendor = Vendor.objects.get(name=vendor_id)
                user = None

                if user_id != 0:
                    user = User.objects.get(id=user_id)
                    # This avoids to create the sale if there is not a cut created. Log a warning, fix the error and
                    # run clicks_summary and collect_aggregated_data jobs for the remaining date again
                    Cut.objects.get(vendor=vendor, group=user.partner_group)

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
                        sale['status'] = Sale.PENDING
                        sale['adjusted_date'] = dateutil.parser.parse('%s'%datetime.date.today())
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