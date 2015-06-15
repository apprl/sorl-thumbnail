import optparse
import datetime
import logging
import calendar
from django.db.models.loading import get_model
from apparelrow.dashboard.views import get_clicks_from_sale, get_conversion_rate
from apparelrow.dashboard.models import Sale, UserEarning

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format YYYY-MM',
            default= None,
        ),
    )

    def handle(self, *args, **options):

        # Generate date range from the beginning until the end of the month
        date = options.get('date')
        if date:
            date_array = date.split("-")
            year = int(date_array[0])
            month = int(date_array[1])
            start_date = datetime.date(year, month, 1)
        else:
            start_date = datetime.date.today().replace(day=1)
        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        # Declare different variables to store the calculated values
        sales_count = [0, 0, 0] # total, publisher, apprl
        total_earnings = [0, 0, 0] # total, publisher, apprl
        cost_per_click_earnings = [0, 0, 0] # total, publisher, apprl
        cost_per_order_earnings = [0, 0, 0] # total, publisher, apprl
        cost_per_order_clicks = [0, 0, 0] # total, publisher, apprl
        cost_per_click_clicks = [0, 0, 0] # total, publisher, apprl
        total_clicks = [0, 0, 0] # total, publisher, apprl

        # Get total amount of clicks
        clicks = get_model('statistics', 'ProductStat')\
            .objects.filter(created__range=(start_date_query, end_date_query)).values('created', 'user_id')
        for click in clicks:
            total_clicks[0] += 1
            total_clicks[1] += 1 if click['user_id'] else 0
            total_clicks[2] += 1 if not click['user_id'] else 0

        for sale in get_model('dashboard', 'Sale').objects.filter(sale_date__range=(start_date_query, end_date_query),
                                                                  status__gte=Sale.PENDING):
            earnings_from_sale = UserEarning.objects.filter(sale=sale)
            for earning in earnings_from_sale:
                # Calculate earnings Cost per click
                if sale.type == Sale.COST_PER_CLICK:
                    cost_per_click_earnings[0] += earning.amount
                    if earning.user:
                        cost_per_click_earnings[1] += earning.amount
                    else:
                        cost_per_click_earnings[2] += earning.amount
                # Calculate earnings Cost per order
                elif sale.type == Sale.COST_PER_ORDER:
                    cost_per_order_earnings[0] += earning.amount
                    if earning.user:
                        cost_per_order_earnings[1] += earning.amount
                    else:
                        cost_per_order_earnings[2] += earning.amount

                # Calculate total amounts
                total_earnings[0] += earning.amount
                if earning.user_earning_type == 'apprl_commission':
                    total_earnings[2] += earning.amount
                else:
                    total_earnings[1] += earning.amount


            # Clicks
            clicks_from_sale = get_clicks_from_sale(sale)
            if sale.type == Sale.COST_PER_CLICK:
                cost_per_click_clicks[0] += clicks_from_sale
                if sale.user_id != 0:
                    cost_per_click_clicks[1] += clicks_from_sale
                else:
                    cost_per_click_clicks[2] += clicks_from_sale
            elif sale.type == Sale.COST_PER_ORDER:
                cost_per_order_clicks[0] += clicks_from_sale
                if sale.user_id != 0:
                    cost_per_order_clicks[1] += clicks_from_sale
                else:
                    cost_per_order_clicks[2] += clicks_from_sale

            if sale.type == Sale.COST_PER_ORDER:
                sales_count[0] += 1
                if sale.user_id:
                    sales_count[1] += 1
                else:
                    sales_count[2] += 1

        # Calculate clicks for cost per order stores
        cost_per_order_clicks[0] = total_clicks[0] - cost_per_click_clicks[0]
        cost_per_order_clicks[1] = total_clicks[1] - cost_per_click_clicks[1]
        cost_per_order_clicks[2] = total_clicks[2] - cost_per_click_clicks[2]

        # Show values

        print "-- Total earnings ( CPC + CPO ) --"
        print "Total: %s" % str(total_earnings[0])
        print "Publisher: %s" % str(total_earnings[1])
        print "Apprl: %s \n" % str(total_earnings[2])

        print "-- Cost per order earnings --"
        print "Total: %s" % str(cost_per_order_earnings[0])
        print "Publisher: %s" % str(cost_per_order_earnings[1])
        print "Apprl: %s\n" % str(cost_per_order_earnings[2])

        print "-- Cost per order clicks --"
        print "Total: %s" % str(cost_per_order_clicks[0])
        print "Publisher: %s" % str(cost_per_order_clicks[1])
        print "Apprl: %s \n" % str(cost_per_order_clicks[2])

        print "-- Cost per order sales --"
        print "Total: %s" % str(sales_count[0])
        print "Publisher: %s" % str(sales_count[1])
        print "Apprl: %s \n" % str(sales_count[2])

        print "-- Cost per order conversion rate --"
        print "Total: %s" % str(get_conversion_rate(sales_count[0], cost_per_order_clicks[0]))
        print "Publisher: %s" % str(get_conversion_rate(sales_count[1], cost_per_order_clicks[1]))
        print "Apprl: %s \n" % str(get_conversion_rate(sales_count[2], cost_per_order_clicks[2]))

        print "-- Cost per click earnings --"
        print "Total: %s" % str(cost_per_click_earnings[0])
        print "Publisher: %s" % str(cost_per_click_earnings[1])
        print "Apprl: %s \n" % str(cost_per_click_earnings[2])

        print "-- Cost per click clicks --"
        print "Total: %s" % str(cost_per_click_clicks[0])
        print "Publisher: %s" % str(cost_per_click_clicks[1])
        print "Apprl: %s \n" % str(cost_per_click_clicks[2])






