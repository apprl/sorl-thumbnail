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
    get_user_attrs, get_day_range, check_user_has_cpc_all_stores

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage

from django.core.management.base import BaseCommand

logger = logging.getLogger('dashboard')

def get_date_range(q_date):
    """
    Parse the given date q_date and return an interval of datetime that consists on the given date range (day or month)
    and extends from the beginning of the starting day to the end of the last day.
    If q_date is None, it would return the range date for yesterday.
    """
    if q_date:
        # Parse and store month and year for the given string that indicates the day or month for which the data
        # will be aggregated
        date_array = q_date.split("-")
        year = int(date_array[0])
        month = int(date_array[1])

        if len(date_array) > 2:
            # Get datetime range for the given day
            start_date_query = datetime.datetime.strptime(q_date, '%Y-%m-%d')
            end_date_query = start_date_query
        else:
            # Get datetime range for the given month
            start_date_query = datetime.date(year, month, 1)
            end_date_query = start_date_query
            end_date_query = end_date_query.replace(day=calendar.monthrange(start_date_query.year, start_date_query.month)[1])
    else:
        # Get datetime range for the given day
        start_date_query = (datetime.date.today() - datetime.timedelta(1)).strftime('%Y-%m-%d')
        start_date_query = datetime.datetime.strptime(start_date_query, '%Y-%m-%d')
        end_date_query = start_date_query

    # Add time to datetime objects so it makes sure range cover first and last second of the datetime range
    start_date = datetime.datetime.combine(start_date_query, datetime.time(0, 0, 0, 0))
    end_date = datetime.datetime.combine(end_date_query, datetime.time(23, 59, 59, 999999))

    return start_date, end_date

def generate_aggregated_data_network_owner(owner, product, vendor, day, clicks, user):
    """
    Aggregates data for owners in a Publisher network.
    Sale earnings and click earnings are aggregated.
    Clicks are aggregated if vendor is CPC or if the publisher  belongs to a Commission group
    where has_cpc_all_stores=True.
    """
    start_date, end_date = get_day_range(day)
    clicks = decimal.Decimal(clicks)
    add_paid_clicks = False
    owner_instance, owner_created = AggregatedData.objects.\
        get_or_create(user_id=owner.id, created=day, data_type='aggregated_from_product',
                      aggregated_from_id=product.id, aggregated_from_name=product.product_name,
                      aggregated_from_slug=product.slug)

    # If instance is just created, add detailed information about user and product where the aggregated has
    # been based on.
    if owner_created:
        owner_instance.user_image, owner_instance.user_link = get_user_thumbnail_and_link(owner)
        owner_instance.aggregated_from_image, owner_instance.aggregated_from_link = get_product_thumbnail_and_link(product)
        _, owner_instance.user_name, owner_instance.user_username = get_user_attrs(owner)

    # If vendor is CPC or user belongs to a Commission group that pays per click to its publishers for all stores
    is_cpc_all_stores = check_user_has_cpc_all_stores(user)
    if vendor.is_cpc or is_cpc_all_stores:
        try:
            sale_type = "cpc_all_stores" if is_cpc_all_stores else "cost_per_click"
            earning_type = "publisher_network_click_tribute_all_stores" if is_cpc_all_stores \
                else "publisher_network_click_tribute"

            sale = Sale.objects.get(user_id=user.id, sale_date__range=(start_date, end_date),
                                    vendor=vendor, affiliate=sale_type)

            earning = UserEarning.objects.get(user_id=owner.id, user_earning_type=earning_type,
                                              from_user=user, date=day, sale=sale)
            clicks_number = get_clicks_from_sale(earning.sale)
            click_cost = 0
            if clicks_number > 0:
                click_cost = earning.amount / clicks_number

            #owner_instance.click_earnings += click_cost * clicks
            owner_instance.network_click_earnings += click_cost * clicks
            owner_instance.total_network_earnings += click_cost * clicks
            #owner_instance.sale_plus_click_earnings += click_cost * clicks

            if sale.affiliate != "cpc_all_stores":
                add_paid_clicks = True
                owner_instance.paid_clicks += clicks
        except Sale.DoesNotExist:
            logger.warning("Sale for user %s, owner %s, date %s does not exist" % (user.id, owner.id, day))
        except UserEarning.DoesNotExist:
            logger.warning("Click earning for user %s date %s does not exist" % (owner.id, day))

    # Add clicks to total clicks summary
    if add_paid_clicks:
        owner_instance.total_clicks += clicks
    owner_instance.save()

def generate_aggregated_from_total(row, user_dict, earning_amount):
    """
    Aggregate data per publisher from the total earnings.
    """
    instance, created = AggregatedData.objects.\
        get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_total',
                      user_name=user_dict['user_name'], user_username=user_dict['user_username'])

    # If instance has been created, add more information about the user
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
    elif row.user_earning_type in ('publisher_network_click_tribute', 'publisher_network_click_tribute_all_stores'):
        instance.network_click_earnings += earning_amount
        instance.total_network_earnings += earning_amount
    elif row.user_earning_type in ('publisher_sale_click_commission', 'publisher_sale_click_commission_all_stores'):
        instance.click_earnings += earning_amount
        instance.sale_plus_click_earnings += earning_amount
        if not row.sale.affiliate == "cpc_all_stores" or \
                (row.sale.affiliate == "cpc_all_stores" and row.sale.vendor.is_cpo):
            instance.paid_clicks += get_clicks_from_sale(row.sale)

    # If earning is from APPRL
    if user_dict['user_id'] == 0 and row.user_earning_type == 'apprl_commission':
        # Aggregated clicks only if sale is not a sale generated for those publishers who earn per click for all
        # store, so it avoids aggregating twice those clicks and the earning for APPRL on these sales is 0.00 always
        apprl_clicks = get_clicks_from_sale(row.sale)
        is_cpc_all_stores = check_user_has_cpc_all_stores(row.from_user)
        if row.sale.type == Sale.COST_PER_CLICK:
            instance.click_earnings += earning_amount
            if row.sale.user_id == 0 or \
                    (is_cpc_all_stores and row.sale.affiliate == "cpc_all_stores"):
                instance.paid_clicks += apprl_clicks
        elif row.sale.type == Sale.COST_PER_ORDER:
            instance.sale_earnings += earning_amount
            if row.sale.user_id == 0:
                instance.sales += 1
        instance.sale_plus_click_earnings += earning_amount

    instance.save()

def generate_aggregated_from_product(row, user_dict, earning_amount, start_date, end_date):
    """
    Aggregated data per publisher per product that originated the sale from total earnings.
    """
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

    if row.user_earning_type == 'publisher_sale_commission':
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
        if row.sale.affiliate != "cpc_all_stores":
            clicks_count = get_model('statistics', 'ProductStat').objects.\
                filter(is_valid=True, user_id=user_dict['user_id'], vendor=row.sale.vendor.name, product=row.from_product.slug,
                       created__range=(start_date, end_date)).count()
            is_cpc_all_stores = False
            if user_dict['user_id'] != 0:
                is_cpc_all_stores = check_user_has_cpc_all_stores(row.user)
            if row.sale.vendor.is_cpc or is_cpc_all_stores:
                instance.paid_clicks = clicks_count
            instance.total_clicks = clicks_count
        user = None if user_dict['user_id'] == 0 else get_user_model().objects.get(id=user_dict['user_id'])
        _, instance.user_name, instance.user_username = get_user_attrs(user)
        instance.aggregated_from_image, instance.aggregated_from_link = get_product_thumbnail_and_link(row.from_product)
    instance.save()

def generate_aggregated_from_links(row, user_dict, earning_amount, start_date, end_date):
    """
    Aggregated data per publisher per link that originated the sale from total earnings.
    """
    link = row.sale.source_link
    logger.debug("Generating aggregated data for links %s" % link)
    instance, created = AggregatedData.objects.\
        get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_product',
                      aggregated_from_id=0, aggregated_from_link=link)
    if created:
        logger.debug("Link %s has been created" % link)
        instance.user_image, instance.user_link = get_user_thumbnail_and_link(row.user)
        instance.user_name = user_dict['user_name']
        instance.user_username = user_dict['user_name']
        instance.aggregated_from_name = "Link to %s " % link

    if row.user_earning_type == 'publisher_sale_commission':
        instance.sale_earnings += row.amount
        instance.sales += 1
    elif row.user_earning_type == 'referral_sale_commission':
        instance.referral_sales += 1
        instance.referral_earnings += earning_amount
    instance.sale_plus_click_earnings += earning_amount
    instance.aggregated_from_slug = link
    instance.aggregated_from_image = staticfiles_storage.url(settings.APPAREL_DEFAULT_LINK_ICON)
    instance.save()

    if created:
        if row.sale.affiliate != "cpc_all_stores":
            clicks_count = get_model('statistics', 'ProductStat').objects.\
                filter(is_valid=True, user_id=user_dict['user_id'], vendor=row.sale.vendor.name,
                       source_link=link, created__range=(start_date, end_date)).count()
            cpc_all_stores = False
            if user_dict['user_id'] != 0:
                cpc_all_stores = check_user_has_cpc_all_stores(row.user)
            if row.sale.vendor.is_cpc or cpc_all_stores:
                instance.paid_clicks = clicks_count
            instance.total_clicks = clicks_count
        user = None if user_dict['user_id'] == 0 else get_user_model().objects.get(id=user_dict['user_id'])
        _, instance.user_name, instance.user_username = get_user_attrs(user)
    instance.save()

def generate_aggregated_from_publisher(row, user_dict, start_date, end_date):
    """
    Generate aggregated data from publisher when earning is a tribute
    """
    # Earning is a tribute
    if row.user_earning_type in ('publisher_network_tribute', 'publisher_network_click_tribute',
                                 'publisher_network_click_tribute_all_stores'):
        instance, publisher_created = AggregatedData.objects.\
            get_or_create(user_id=user_dict['user_id'], created=row.date.date(), data_type='aggregated_from_publisher',
                          aggregated_from_id=row.from_user.id, user_name=user_dict['user_name'], user_username=user_dict['user_username'])
        publisher_earning = UserEarning.objects.\
            get(user=row.from_user, date__range=(start_date, end_date), sale=row.sale)

        # Add image, link, and clicks to user if user it has been just created
        if publisher_created and row.sale.affiliate != "cpc_all_stores":
            instance.user_image, instance.user_link = get_user_thumbnail_and_link(row.user)
            stats = get_model('statistics', 'ProductStat').objects.\
                filter(created__range=(start_date, end_date), user_id=row.from_user.id, is_valid=True).\
                aggregate(clicks=Count('user_id'))
            instance.total_clicks += stats['clicks']

        if row.user_earning_type == 'publisher_network_tribute':
            # Publisher earning is a sale tribute
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
            # Publisher earning is a click tribute
            add_paid_clicks = False if publisher_earning.sale.affiliate == "cpc_all_stores" else True
            instance.click_earnings += publisher_earning.amount
            instance.network_click_earnings += row.amount
            if add_paid_clicks:
                instance.paid_clicks += get_clicks_from_sale(row.sale)

        instance.sale_plus_click_earnings += publisher_earning.amount
        instance.total_network_earnings += row.amount
        instance.aggregated_from_id = row.from_user.id
        instance.aggregated_from_name = row.from_user.name if row.from_user.name else ''
        instance.aggregated_from_slug = row.from_user.username if row.from_user.username else ''
        instance.aggregated_from_image, instance.aggregated_from_link = get_user_thumbnail_and_link(row.from_user)
        instance.save()

def generate_aggregated_clicks_from_publisher(start_date, end_date):
    """
    Aggregate clicks that were not including in earnings like CPO earnings that were not paid in general
    """
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

def generate_aggregated_clicks_from_product(start_date, end_date):
    """
    Aggregated clicks per product that originated the sale for the given period passed as parameter.
    """
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

                # Aggregate click data (earnings and amount of clicks) for product
                is_cpc_all_stores = check_user_has_cpc_all_stores(user)
                if vendor.is_cpc or is_cpc_all_stores:
                    try:
                        sale_type = "cpc_all_stores" if is_cpc_all_stores else "cost_per_click"
                        sale = Sale.objects.get(user_id=row['user_id'], sale_date__range=(start_date, end_date),
                                                vendor=vendor, affiliate=sale_type)

                        earning_type = 'publisher_sale_click_commission_all_stores' \
                            if is_cpc_all_stores else 'publisher_sale_click_commission'
                        earning = UserEarning.objects.get(user_id=row['user_id'], date=row['day'], sale=sale,
                                                      user_earning_type=earning_type)
                        clicks_amount = get_clicks_from_sale(earning.sale)
                        click_cost = 0
                        if clicks_amount > 0:
                            click_cost = earning.amount / clicks_amount
                        clicks = decimal.Decimal(row['clicks'])
                        instance.click_earnings += click_cost * clicks
                        instance.sale_plus_click_earnings += click_cost * clicks
                        instance.paid_clicks += decimal.Decimal(row['clicks'])

                    except UserEarning.DoesNotExist:
                        logger.warning("Click earning for user %s date %s does not exist" % (row['user_id'], row['day']))
                    except Sale.DoesNotExist:
                        logger.warning("Sale for user %s date %s does not exist" % (row['user_id'], row['day']))

                instance.total_clicks += decimal.Decimal(row['clicks'])
                instance.save()

                if user and user.owner_network:
                    generate_aggregated_data_network_owner(user.owner_network, product, vendor, row['day'],
                                                                row['clicks'], user)

def generate_aggregated_clicks_from_links(start_date, end_date):
    """
    Aggregated clicks per links that originated the sale for the given period passed as parameter.
    """
    aggregated_product_stat = get_model('statistics', 'ProductStat').objects.\
        filter(created__range=(start_date, end_date), is_valid=True, page__in=('Ext-Store', 'Ext-Link')).\
        exclude(source_link__isnull=True).\
        extra(select={'day': 'date( created )'}).\
        values('user_id', 'source_link', 'vendor', 'day').\
        annotate(clicks=Count('source_link')).\
        order_by('clicks')

    for row in aggregated_product_stat:
        user = None
        vendor = None

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

        if vendor and row['source_link'] != "" and (user or row['user_id'] == 0):
            instance, created = AggregatedData.objects.\
                get_or_create(user_id=row['user_id'], created=row['day'], data_type='aggregated_from_product',
                              aggregated_from_id=0, aggregated_from_link=row['source_link'])
            if created:
                _, instance.user_name, instance.user_username = get_user_attrs(user)
                instance.user_image, instance.user_link = get_user_thumbnail_and_link(user)
                instance.aggregated_from_image = staticfiles_storage.url(settings.APPAREL_DEFAULT_LINK_ICON)
                instance.aggregated_from_name = "Link to %s " % row['source_link']
                instance.aggregated_from_slug = row['source_link']

                is_cpc_all_stores = check_user_has_cpc_all_stores(user)

                if vendor.is_cpc or is_cpc_all_stores:
                    instance.paid_clicks += decimal.Decimal(row['clicks'])
                    try:
                        sale_type = "cpc_all_stores" if is_cpc_all_stores else "cost_per_click"
                        sale = Sale.objects.get(user_id=row['user_id'], sale_date__range=(start_date, end_date),
                                                vendor=vendor, affiliate=sale_type)
                        earning_type = 'publisher_sale_click_commission_all_stores' \
                            if is_cpc_all_stores else 'publisher_sale_click_commission'
                        earning = UserEarning.objects.get(user_id=row['user_id'], date=row['day'], sale=sale,
                                                          user_earning_type=earning_type)
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

    def handle(self, *args, **options):
        """
        Handler for job that aggregates data in general, for publishers and for products.
        Attention: This job does not handle correctly when a vendor has is_cpc=True and is_cpo=True, because
        they are exclusive among each other until the current time.
        """
        start_date, end_date = get_date_range(options.get('date'))
        logger.debug("Start collect agreggated data between %s and %s" % (start_date, end_date))

        # Remove all existent data for the given period
        AggregatedData.objects.filter(created__range=(start_date, end_date)).delete()

        # Get all earnings for the given period
        earnings = UserEarning.objects.filter(date__range=(start_date, end_date), status__gte=Sale.PENDING)

        # Loop over all earnings for the given period
        logger.debug("Generating aggregated data with %s earnings... " % earnings.count())
        for row in earnings:
            user_dict = get_user_dict(row.user)
            earning_amount = decimal.Decimal(row.amount)

            # Generate different aggregated data
            generate_aggregated_from_total(row, user_dict, earning_amount)
            if row.from_product:
                generate_aggregated_from_product(row, user_dict, earning_amount, start_date, end_date)
            elif row.sale.source_link and not row.sale.source_link == '':
                generate_aggregated_from_links(row, user_dict, earning_amount, start_date, end_date)
            generate_aggregated_from_publisher(row, user_dict, start_date, end_date)

        logger.debug("Generating aggregated clicks... ")
        generate_aggregated_clicks_from_publisher(start_date, end_date)
        generate_aggregated_clicks_from_product(start_date, end_date)
        generate_aggregated_clicks_from_links(start_date, end_date)

        logger.debug("Finishing collect agreggated data successfully")
        return
