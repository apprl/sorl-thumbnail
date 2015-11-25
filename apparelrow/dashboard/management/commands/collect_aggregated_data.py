import optparse
import datetime
import logging
from django.db.models.loading import get_model
from django.contrib.auth import get_user_model
import decimal
import calendar
from django.db.models import Count

from apparelrow.dashboard.models import Sale, UserEarning, AggregatedData
from apparelrow.dashboard.views import get_clicks_from_sale
from apparelrow.dashboard.utils import get_product_thumbnail_and_link, get_user_dict, get_user_thumbnail_and_link, \
    get_user_attrs, get_day_range

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')


class Command(BaseCommand):
    args = ''
    help = 'Import dashboard data'
    option_list = BaseCommand.option_list + (
        optparse.make_option('--date',
            action='store',
            dest='date',
            help='Select a custom date in the format YYYY-MM-DD',
            default= None,
        ),
    )

    def generate_aggregated_data_network_owner(self, owner, product, vendor, day, clicks, user):
        start_date, end_date = get_day_range(day)
        clicks = decimal.Decimal(clicks)

        ownerp_instance, ownerp_created = AggregatedData.objects.\
            get_or_create(user_id=owner.id, created=day, data_type='aggregated_from_product',
                      aggregated_from_id=product.id, aggregated_from_name=product.product_name,
                      aggregated_from_slug=product.slug)
        if ownerp_created:
            ownerp_instance.user_image, ownerp_instance.user_link = get_user_thumbnail_and_link(owner)
            ownerp_instance.aggregated_from_image, ownerp_instance.aggregated_from_link = get_product_thumbnail_and_link(product)
            _, ownerp_instance.user_name, ownerp_instance.user_username = get_user_attrs(owner)
        if vendor.is_cpc:
            ownerp_instance.paid_clicks += decimal.Decimal(clicks)
            try:
                sale = Sale.objects.get(user_id=user.id, sale_date__range=(start_date, end_date),
                                        vendor=vendor, affiliate="cost_per_click")
                earning = UserEarning.objects.get(user_id=owner.id,
                                                  user_earning_type='publisher_network_click_tribute',
                                                  from_user=user, date=day, sale=sale)
                clicks_number = get_clicks_from_sale(earning.sale)
                click_cost = 0
                if clicks_number > 0:
                    click_cost = earning.amount / clicks_number

                ownerp_instance.click_earnings += click_cost * clicks
                ownerp_instance.sale_plus_click_earnings += click_cost * clicks
            except Sale.DoesNotExist:
                logger.warning("Sale for user %s, owner %s, date %s does not exist" % (user.id, owner.id, day))
            except UserEarning.DoesNotExist:
                logger.warning("Click earning for user %s date %s does not exist" % (owner.id, day))
        ownerp_instance.total_clicks += decimal.Decimal(clicks)
        ownerp_instance.save()

    def get_date_range(self, q_date):
        if q_date:
            date_array = q_date.split("-")
            year = int(date_array[0])
            month = int(date_array[1])

            if len(date_array) > 2:
                start_date_query = datetime.datetime.strptime(q_date, '%Y-%m-%d')
                end_date_query = start_date_query
            else:
                start_date_query = datetime.date(year, month, 1)
                end_date_query = start_date_query
                end_date_query = end_date_query.replace(day=calendar.monthrange(start_date_query.year, start_date_query.month)[1])
        else:
            start_date_query = (datetime.date.today() - datetime.timedelta(1)).strftime('%Y-%m-%d')
            start_date_query = datetime.datetime.strptime(start_date_query, '%Y-%m-%d')
            end_date_query = start_date_query

        start_date = datetime.datetime.combine(start_date_query, datetime.time(0, 0, 0, 0))
        end_date = datetime.datetime.combine(end_date_query, datetime.time(23, 59, 59, 999999))

        return start_date, end_date

    def generate_aggregated_from_total(self, row, user_dict, earning_amount):
        instance, created = AggregatedData.objects.\
            get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_total',
                          user_name=user_dict['user_name'], user_username=user_dict['user_username'])

        if created:
            instance.user_image, instance.user_link = get_user_thumbnail_and_link(row.user)

        # Aggregate earnings by type
        if row.user_earning_type in ('referral_sale_commission', 'referral_signup_commission'):
            instance.referral_sales += 1
            instance.referral_earnings += earning_amount
            instance.sale_plus_click_earnings += earning_amount
        elif row.user_earning_type == 'publisher_sale_commission':
            instance.sale_earnings += earning_amount
            instance.sale_plus_click_earnings += earning_amount
            instance.sales += 1
        elif row.user_earning_type == 'publisher_network_tribute':
            instance.network_sale_earnings += earning_amount
            instance.total_network_earnings += earning_amount
            instance.network_sales += 1
        elif row.user_earning_type == 'publisher_network_click_tribute':
            instance.network_click_earnings += earning_amount
            instance.total_network_earnings += earning_amount
        elif row.user_earning_type == 'publisher_sale_click_commission':
            instance.click_earnings += earning_amount
            instance.sale_plus_click_earnings += earning_amount
            instance.paid_clicks += get_clicks_from_sale(row.sale)

        if user_dict['user_id'] == 0 and row.user_earning_type == 'apprl_commission':
            if row.sale.type == Sale.COST_PER_CLICK:
                instance.click_earnings += earning_amount
                if row.sale.user_id == 0:
                    instance.paid_clicks += get_clicks_from_sale(row.sale)
            elif row.sale.type == Sale.COST_PER_ORDER:
                instance.sale_earnings += earning_amount
                if row.sale.user_id == 0:
                    instance.sales += 1
            instance.sale_plus_click_earnings += earning_amount
        instance.save()

    def generate_aggregated_from_product(self, row, user_dict, earning_amount, start_date, end_date):
        logger.debug("Generating aggregated data for product %s" % row.from_product.product_name)
        instance, created = AggregatedData.objects.\
            get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_product',
                          aggregated_from_id=row.from_product.id)
        if created:
            logger.debug("Product %s has been created" % row.from_product.product_name)
            instance.user_image, instance.user_link = get_user_thumbnail_and_link(row.user)
            instance.user_name = user_dict['user_name']
            instance.user_username = user_dict['user_name']
            instance.aggregated_from_image, instance.aggregated_from_link = get_product_thumbnail_and_link(row.from_product)

        if row.user_earning_type in ('publisher_sale_commission', 'apprl_commission'):
            instance.sale_earnings += row.amount
            instance.sales += 1
        elif row.user_earning_type == 'referral_sale_commission':
            instance.referral_sales += 1
            instance.referral_earnings += earning_amount
        instance.sale_plus_click_earnings += earning_amount
        instance.aggregated_from_id = row.from_product.id
        instance.aggregated_from_name = row.from_product.product_name \
            if row.from_product.product_name else ''
        instance.aggregated_from_slug = row.from_product.slug if row.from_product.slug else ''
        instance.save()

        if created:
            clicks_count = get_model('statistics', 'ProductStat').objects.\
                filter(is_valid=True, user_id=user_dict['user_id'], vendor=row.sale.vendor.name, product=row.from_product.slug,
                       created__range=(start_date, end_date)).count()
            if row.sale.vendor.is_cpc:
                instance.paid_clicks = clicks_count
            instance.total_clicks = clicks_count
            user = None if user_dict['user_id'] == 0 else get_user_model().objects.get(id=user_dict['user_id'])
            _, instance.user_name, instance.user_username = get_user_attrs(user)
            instance.aggregated_from_image, instance.aggregated_from_link = get_product_thumbnail_and_link(row.from_product)
        instance.save()

    def generate_aggregated_from_publisher(self, row, user_dict, start_date, end_date):
        """
            Generate aggregated data from publisher when earning is a tribute
        """
        if row.user_earning_type in ('publisher_network_tribute', 'publisher_network_click_tribute'):
            instance, publisher_created = AggregatedData.objects.\
                get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_publisher',
                              aggregated_from_id=row.from_user.id, user_name=user_dict['user_name'], user_username=user_dict['user_username'])
            publisher_earning = UserEarning.objects.\
                get(user=row.from_user, date__range=(start_date, end_date), sale=row.sale)
            if publisher_created:
                instance.user_image, instance.user_link = get_user_thumbnail_and_link(row.user)
                stats = get_model('statistics', 'ProductStat').objects.\
                    filter(created__range=(start_date, end_date), user_id=row.from_user.id, is_valid=True).\
                    aggregate(clicks=Count('user_id'))
                instance.total_clicks += stats['clicks']
            if row.user_earning_type == 'publisher_network_tribute':
                instance.sale_earnings += publisher_earning.amount
                instance.network_sale_earnings += row.amount
                instance.network_sales += 1

                if row.from_product:
                    product_instance, product_created = AggregatedData.objects.\
                get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_product',
                              aggregated_from_id=row.from_product.id)
                    if product_created:
                        product_instance.user_image, product_instance.user_link = get_user_thumbnail_and_link(row.user)
                        product_instance.user_name = user_dict['user_name']
                        product_instance.user_username = user_dict['user_username']
                        product_instance.aggregated_from_image, product_instance.aggregated_from_link = get_product_thumbnail_and_link(row.from_product)
                    product_instance.sale_earnings += publisher_earning.amount
                    product_instance.network_sale_earnings += decimal.Decimal(row.amount)
                    product_instance.sale_plus_click_earnings += publisher_earning.amount
                    product_instance.total_network_earnings += decimal.Decimal(row.amount)
                    product_instance.sales += 1
                    product_instance.aggregated_from_id = row.from_product.id
                    product_instance.aggregated_from_name = row.from_product.product_name \
                        if row.from_product.product_name else ''
                    product_instance.aggregated_from_slug = row.from_product.slug if row.from_product.slug else ''
                    product_instance.save()
            else:
                instance.click_earnings += publisher_earning.amount
                instance.network_click_earnings += row.amount
                instance.paid_clicks += get_clicks_from_sale(row.sale)
            instance.sale_plus_click_earnings += publisher_earning.amount
            instance.total_network_earnings += row.amount
            instance.aggregated_from_id = row.from_user.id
            instance.aggregated_from_name = row.from_user.name if row.from_user.name else ''
            instance.aggregated_from_slug = row.from_user.username if row.from_user.username else ''
            instance.aggregated_from_image, instance.aggregated_from_link = get_user_thumbnail_and_link(row.from_user)
            instance.save()

    def generate_aggregated_clicks_from_publisher(self, start_date, end_date):
        # Total clicks under the given period group by user
        clicks_query = get_model('statistics', 'ProductStat').objects.\
            filter(created__range=(start_date, end_date), is_valid=True).\
            extra(select={'day': 'date( created )'}).\
            values('user_id', 'day').\
            annotate(clicks=Count('user_id')).\
            order_by('clicks')

        for row in clicks_query:
            instance, created = AggregatedData.objects.\
                get_or_create(user_id=row['user_id'], created=row['day'], data_type='aggregated_from_total')
            if created:
                if row['user_id'] == 0:
                    _, instance.user_name, instance.user_username = get_user_attrs(None)
                else:
                    try:
                        row_user = get_user_model().objects.get(id=row['user_id'])
                        instance.user_image, instance.user_link = get_user_thumbnail_and_link(row_user)
                        _, instance.user_name, instance.user_username = get_user_attrs(row_user)
                    except get_user_model().DoesNotExist:
                        logger.warning("User %s does not exist" % row['user_id'])
            instance.total_clicks += row['clicks']
            instance.save()

    def generate_aggregated_clicks_from_product(self, start_date, end_date):
        # Total clicks under the given period group by product
        aggregated_product_stat = get_model('statistics', 'ProductStat').objects.\
            filter(created__range=(start_date, end_date), is_valid=True).\
            extra(select={'day': 'date( created )'}).\
            values('user_id', 'product', 'vendor', 'day').\
            annotate(clicks=Count('product')).\
            order_by('clicks')

        for row in aggregated_product_stat:
            user = None
            product = None
            vendor = None

            # Try fetch product if it exists
            try:
                product = get_model('apparel', 'Product').objects.get(slug=row['product'])
            except get_model('apparel', 'Product').DoesNotExist:
                logger.warning("Product %s does not exist" % row['product'])

            # Try fetch vendor if it exists
            try:
                vendor = get_model('apparel', 'Vendor').objects.get(name=row['vendor'])
            except get_model('apparel', 'Vendor').DoesNotExist:
                logger.warning("Vendor %s does not exist" % row['vendor'])

            # Try fetch user if it is not APPRL user and if user exists
            if row['user_id'] != 0:
                try:
                    user = get_user_model().objects.get(id=row['user_id'])
                except get_user_model().DoesNotExist:
                    logger.warning("User %s does not exist" % row['user_id'])

            # If product and vendor exist, generate aggregated data for product
            if product and vendor:
                # Get datetime range for entire day
                start_date, end_date = get_day_range(row['day'])

                # Generate AggregatedData for product
                instance, created = AggregatedData.objects.\
                    get_or_create(user_id=row['user_id'], created=row['day'], data_type='aggregated_from_product',
                                  aggregated_from_id=product.id, aggregated_from_name=product.product_name,
                                  aggregated_from_slug=product.slug)
                if created:
                    _, instance.user_name, instance.user_username  = get_user_attrs(user)
                    instance.user_image, instance.user_link = get_user_thumbnail_and_link(user)
                    instance.aggregated_from_image, instance.aggregated_from_link = get_product_thumbnail_and_link(product)

                    if vendor.is_cpc:
                        instance.paid_clicks += decimal.Decimal(row['clicks'])
                        try:
                            sale = Sale.objects.get(user_id=row['user_id'], sale_date__range=(start_date, end_date),
                                                    vendor=vendor, affiliate="cost_per_click")
                            earning = UserEarning.objects.get(user_id=row['user_id'], date=row['day'], sale=sale,
                                                              user_earning_type='publisher_sale_click_commission')
                            clicks_amount = get_clicks_from_sale(earning.sale)
                            click_cost = 0
                            if clicks_amount > 0:
                                click_cost = earning.amount / clicks_amount
                            clicks = decimal.Decimal(row['clicks'])
                            instance.click_earnings += click_cost * clicks
                            instance.sale_plus_click_earnings += click_cost * clicks
                        except UserEarning.DoesNotExist:
                            logger.warning("Click earning for user %s date %s does not exist" % (row['user_id'], row['day']))
                        except Sale.DoesNotExist:
                            logger.warning("Sale for user %s date %s does not exist" % (row['user_id'], row['day']))

                    instance.total_clicks += decimal.Decimal(row['clicks'])
                    instance.save()

                    if user and user.owner_network:
                        self.generate_aggregated_data_network_owner(user.owner_network, product, vendor, row['day'],
                                                                    row['clicks'], user)

    def handle(self, *args, **options):
        start_date, end_date = self.get_date_range(options.get('date'))
        logger.debug("Start collect agreggated data between %s and %s" % (start_date, end_date))

        # Remove all existent data for the given period
        AggregatedData.objects.filter(created__range=(start_date, end_date)).delete()

        # Get all earnings for the given period
        earnings = UserEarning.objects.filter(date__range=(start_date, end_date), status__gte=Sale.PENDING)

        # Loop over all earnings for the given period
        logger.debug("Generating aggregated data with % earnings... " % earnings.count())
        for row in earnings:
            user_dict = get_user_dict(row.user)
            earning_amount = decimal.Decimal(row.amount)
            sale = row.sale

            # Generate different aggregated data
            self.generate_aggregated_from_total(row, user_dict, earning_amount)
            if row.from_product:
                self.generate_aggregated_from_product(row, user_dict, earning_amount, start_date, end_date)
            self.generate_aggregated_from_publisher(row, user_dict, start_date, end_date)

        logger.debug("Generating aggregated clicks... ")
        self.generate_aggregated_clicks_from_publisher(start_date, end_date)
        self.generate_aggregated_clicks_from_product(start_date, end_date)

        logger.debug("Finishing collect agreggated data successfully")
        return
