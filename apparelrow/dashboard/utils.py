import decimal
import datetime
import calendar
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import get_model, Sum, Count
from django.db import connection
from django.http import HttpResponse
from django.template import defaultfilters
import logging

from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.fields import ImageField
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.translation import ugettext_lazy as _
from apparelrow.apparel.utils import currency_exchange
from dateutil.relativedelta import *

log = logging.getLogger(__name__)

def map_placement(placement):
    link = 'Unknown'
    if placement == 'Ext-Shop':
        link = 'Shop on your site'
    elif placement == 'Ext-Look':
        link = 'Look on your site'
    elif placement == 'Ext-Link':
        link = 'Product link on your site'
    elif placement == 'Ext-Store':
        link = 'Store link on your site'
    elif placement == 'Look':
        link = 'Look on Apprl.com'
    elif placement == 'Shop':
        link = 'Shop on Apprl.com'
    elif placement == 'Feed':
        link = 'Feed on Apprl.com'
    elif placement == 'Profile':
        link = 'Your profile on Apprl.com'
    elif placement == 'Product':
        link = 'Product page'
    elif placement == 'Ext-Banner':
        link = 'Banner on your site'

    return link

def parse_date(month, year, first_to_first=False):
    if year is None and month is None:
        # If not date is selected then take the range from day one this month
        start_date = datetime.date.today().replace(day=1)
        end_date = start_date+relativedelta(months=+1)
        if not first_to_first:
            end_date = end_date+relativedelta(days=-1)

    else:
        # If either year or month has been selected.
        start_date = datetime.date(int(year), int(1), 1)
        end_date = start_date + relativedelta(years=+1)
        if not first_to_first:
            end_date = end_date + relativedelta(days=-1)

        if month != "0":
            # If month has been provided, then we need to get the range inside the requested month
            start_date = start_date.replace(month=int(month))
            end_date = start_date+relativedelta(months=+1)
            if not first_to_first:
                end_date = end_date+relativedelta(days=-1)

    return start_date, end_date

def get_clicks_from_sale(sale):
    """
    Return number of clicks generated from the given sale
    """
    user_id = sale.user_id
    start_date_query = datetime.datetime.combine(sale.sale_date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(sale.sale_date, datetime.time(23, 59, 59, 999999))
    vendor_name = sale.vendor
    clicks = get_model('statistics', 'ProductStat').objects.filter(vendor=vendor_name, user_id=user_id,
                                                          created__range=[start_date_query, end_date_query],
                                                                   is_valid=True).count()
    return clicks

def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict
    """
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def get_referral_user_from_cookie(request):
    """
    Return user instance retrieved from the request information
    """
    user = None
    user_id = request.get_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, None)
    if user_id:
        try:
            user = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            pass
    return user

def parse_cost_amount(click_cost):
    """
    Parse string with cost information and returns amount as Decimal and currency
    """
    amount = None
    currency = None
    if click_cost:
        array_click = click_cost.split(" ")
        amount = decimal.Decimal(array_click[0])
        currency = array_click[1]
    return amount, currency

def parse_rules_exception(data_exceptions, user_id):
    """
    Return cut for publisher network and total publisher cut after removing owner network tribute from exception if
    there is an exception for given user id
    """
    if not data_exceptions:
        data_exceptions = []

    cut_exception = None
    publisher_cut = None
    click_cost = None
    for data in data_exceptions:
        if data['sid'] == user_id:
            if 'cut' in data:
                cut_exception = decimal.Decimal(data['cut'])
            if 'tribute' in data:
                publisher_cut = 1 - decimal.Decimal(data['tribute'])
            if 'click_cost' in data:
                click_cost = data['click_cost']
    return cut_exception, publisher_cut, click_cost


def get_cuts_for_user_and_vendor(user_id, vendor):
    """
    Return a tuple that contains user instance, commission group cut, referral cut, publisher cut considering if the
    publisher belongs to a publisher network and pays tribute, given an user id and a vendor
    """
    user = None
    normal_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)
    referral_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)
    publisher_cut = 1

    try:
        user = get_user_model().objects.get(pk=user_id)
        if user.partner_group:
            try:
                # Publisher network total cut
                cuts = user.partner_group.cuts.get(vendor=vendor)
                normal_cut = cuts.cut
                referral_cut = cuts.referral_cut
                data_exceptions = None

                # Owner network cut
                if user.owner_network:
                    owner = user.owner_network
                    if owner.owner_network_cut > 1:
                        owner.owner_network_cut = 1
                    publisher_cut -= owner.owner_network_cut

                # Handle exceptions for publisher cuts and owner cuts
                if cuts.rules_exceptions:
                    cut_exception, publisher_cut_exception, _ = parse_rules_exception(cuts.rules_exceptions, user_id)
                    if cut_exception:
                        normal_cut = cut_exception
                    if publisher_cut_exception is not None and user.owner_network:
                        publisher_cut = publisher_cut_exception
            except:
                log.warn("No cut exists for %s and vendor %s, please do correct this." % (user.partner_group,vendor))
    except get_user_model().DoesNotExist:
        log.warn("User %s does not exist" % user_id)

    return user, normal_cut, referral_cut, publisher_cut

def get_clicks_list(vendor_name, date, currency, click_cost, user_id=None, is_store=False):
    """
    Return a sorted list with detailed information from click earnings per product
    for a given user, vendor and day

    """
    # Todo: Change this to dates only, remove 23.59:59:99999 and such
    start_date_query = datetime.datetime.combine(date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(date, datetime.time(23, 59, 59, 999999))
    values = [vendor_name, start_date_query, end_date_query]
    cursor = connection.cursor()

    if user_id:
        try:
            user = get_user_model().objects.get(id=user_id)
            values.append(user_id)
            values.extend([user_id, vendor_name, start_date_query, end_date_query])
            values.extend([vendor_name, start_date_query, end_date_query, user_id])
            values.extend([user_id, vendor_name, start_date_query, end_date_query])
            cursor.execute(
                """(SELECT PS.vendor, PS.user_id, PS.product, count(PS.id) as clicks
                   FROM statistics_productstat PS, profile_user U, apparel_vendor V
                   WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.product IS NOT NULL
                   AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s AND U.id = %s
                   GROUP BY PS.user_id, PS.vendor, PS.product)
                   UNION
                   (SELECT PS.vendor, PS.user_id, PS.product, count(PS.id) as clicks
                   FROM statistics_productstat PS, apparel_vendor V, profile_user U, dashboard_group G
                   WHERE PS.user_id = U.id AND U.partner_group_id = G.id AND G.has_cpc_all_stores = True AND PS.product IS NOT NULL
                   AND U.id = %s AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.is_valid
                   AND PS.created BETWEEN %s AND %s
                   GROUP BY PS.user_id, PS.vendor, PS.product)
                   UNION
                   (SELECT PS.vendor, PS.user_id, PS.source_link,count(PS.id) as clicks
                   FROM statistics_productstat PS, profile_user U, apparel_vendor V
                   WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.product IS NULL
                   AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s AND U.id = %s
                   GROUP BY PS.user_id, PS.vendor, PS.source_link)
                   UNION
                   (SELECT PS.vendor, PS.user_id, PS.source_link, count(PS.id) as clicks
                   FROM statistics_productstat PS, apparel_vendor V, profile_user U, dashboard_group G
                   WHERE PS.user_id = U.id AND U.partner_group_id = G.id AND G.has_cpc_all_stores = True AND PS.product IS NULL
                   AND U.id = %s AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.is_valid
                   AND PS.created BETWEEN %s AND %s
                   GROUP BY PS.user_id, PS.vendor, PS.source_link)
                   ORDER BY clicks DESC
                   """, values)
        except get_user_model().DoesNotExist:
            log.warn("User %s does not exist" % user)
    elif is_store:
        values.extend([vendor_name, start_date_query, end_date_query, ])
        values.extend([vendor_name, start_date_query, end_date_query, ])
        values.extend([vendor_name, start_date_query, end_date_query, ])
        cursor.execute(
            """(SELECT PS.vendor, PS.product, count(PS.id) as clicks
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
               AND PS.product IS NOT NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product)
               UNION
               (SELECT PS.vendor, PS.product, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V
               WHERE V.name = %s AND PS.vendor = V.name
               AND PS.product IS NOT NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product)
               UNION
               (SELECT PS.vendor, PS.source_link, count(PS.id) as clicks
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
               AND PS.product IS NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.source_link)
               UNION
               (SELECT PS.vendor, PS.source_link, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V
               WHERE V.name = %s AND PS.vendor = V.name
               AND PS.product IS NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.source_link)
               ORDER BY clicks DESC
               """, values)
    else:
        values.extend([vendor_name, start_date_query, end_date_query, vendor_name, start_date_query, end_date_query])
        cursor.execute(
            """(SELECT PS.vendor, PS.product, count(PS.id) as clicks
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
               AND PS.product IS NOT NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product)
               UNION
               (SELECT PS.vendor, PS.product, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V
               WHERE V.name = %s AND PS.vendor = V.name
               AND PS.product IS NOT NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product)
               UNION
               (SELECT PS.vendor, PS.product, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V, profile_user U, dashboard_group G
               WHERE PS.user_id = U.id AND U.partner_group = G.id AND G.has_cpc_all_stores = True
               AND PS.product IS NOT NULL AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.is_valid
               AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product)
               UNION
               (SELECT PS.vendor, PS.source_link, count(PS.id) as clicks
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
               AND PS.product IS NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.source_link)
               UNION
               (SELECT PS.vendor, PS.source_link, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V
               WHERE V.name = %s AND PS.vendor = V.name
               AND PS.product IS NULL AND V.is_cpc = True AND PS.is_valid AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.source_link)
               UNION
               (SELECT PS.vendor, PS.source_link, count(PS.id) as clicks
               FROM statistics_productstat PS, apparel_vendor V, profile_user U, dashboard_group G
               WHERE PS.user_id = U.id AND U.partner_group = G.id AND G.has_cpc_all_stores = True
               AND PS.product IS NULL AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True AND PS.is_valid
               AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.source_link)
               ORDER BY clicks DESC
               """, values)
    data = dictfetchall(cursor)
    for row in data:
        if not row['product'].startswith("http://") and not row['product'].startswith("https://") :
            row['product_name'] = row['product']
            try:
                product = get_model('apparel', 'Product').objects.get(slug=row['product'])
                row['product_name'] = ''
                if product.manufacturer:
                    row['product_name'] = "%s - " % product.manufacturer.name
                row['product_name'] = product.product_name if product.product_name else product.slug
                row['product_url'] = reverse('product-detail', args=[row['product']])
            except get_model('apparel', 'Product').DoesNotExist:
                row['product_name'] = row['product']
                log.warn("Product %s does not exist" % row['product'])
                row['product_url'] = "Clicks to %s" % row['product']
            row['product_earning'] = float(int(row['clicks']) * click_cost)
        else:
            row['product_name'] = "Clicks to %s" % row['product']
            row['product_url'] = row['product']
        row['product_earning'] = float(int(row['clicks']) * click_cost)
    return data

def get_product_thumbnail_and_link(product):
    """
    Return thumbnail and link for a product
    """
    product_image = ''
    if product.product_image:
        try:
            product_image = get_thumbnail(ImageField().to_python(product.product_image), '50', crop='noop').url
        except:
            pass
    product_link = None
    if product.slug:
        product_link = reverse('product-detail', args=[product.slug])
    return product_image, product_link

def get_clicks_amount(vendor, start_date_query, end_date_query):
    """
    Return total amount in EUR for a Vendor in given date range
    """
    total_amount = 0

    currency = None
    for item in get_model('dashboard', 'Sale').objects.filter(vendor=vendor,
                                                              sale_date__range=[start_date_query, end_date_query],
                                                              type=get_model('dashboard', 'Sale').COST_PER_CLICK,
                                                              affiliate="cost_per_click"):
        total_amount += item.original_amount
        if not currency and item.original_currency:
            currency = item.original_currency
    return total_amount, currency

def get_number_clicks(vendor, start_date_query, end_date_query):
    """
    Return total number of clicks for a Vendor in a given date range
    """
    return get_model('statistics', 'ProductStat').objects.\
        filter(vendor=vendor, created__range=[start_date_query, end_date_query], is_valid=True).count()

def get_total_clicks_per_vendor(vendor):
    """
    Return total number of clicks for a Vendor
    """
    # Todo: Change this to dates only, remove 23.59:59:99999 and such
    today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
    return get_model('statistics', 'ProductStat').objects.filter(vendor=vendor, is_valid=True).\
        exclude(created__range=(today_min, today_max)).count()

def get_user_attrs(user):
    """
    Return tuple with user attributes: ID, Name and Username
    """
    user_dict = get_user_dict(user)
    return user_dict['user_id'], user_dict['user_name'], user_dict['user_username']

def get_user_dict(user):
    user_id = 0 if not user else user.id
    user_name = 'APPRL' if user_id == 0 else ''
    user_username = 'APPRL' if user_id == 0 else ''
    if user:
        user_name = user.name if user.name else ''
        user_username = user.username if user.username else ''
    return {'user_id': user_id, 'user_name': user_name, 'user_username': user_username}

def get_user_thumbnail_and_link(user):
    """
    Return user avatar and link to the profile page
    """
    user_link = ''
    user_image = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR)
    if user:
        try:
            user_link = reverse('profile-likes', args=[user.slug])
            user_image = user.avatar
        except IOError:
            pass
    return user_image, user_link

def get_description_for_product(product, vendor):
    """
    Return attributes for Product: Name, Link and Image link
    """
    product_text = ''
    product_link = ''
    product_image = ''
    if product:
        product_image, product_link = get_product_thumbnail_and_link(product)
        product_text = ''
        if product.manufacturer:
            product_text += "%s - " % product.manufacturer.name
        product_text += product.product_name
    elif vendor:
        product_text = "Sale from %s" % vendor.name

    return product_text, product_link, product_image

def retrieve_user_earnings(month, year, user=None, limit=None):
    """
    Return a list of dictionaries with detailed data of User Earnings
    """

    if month == '0':
        start_date = datetime.date(int(year), int(1), 1)
        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)
    else:
        start_date = datetime.date(int(year), int(month), 1)

        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

    # Todo: Change this to dates only, remove 23.59:59:99999 and such
    start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))
    earnings = get_model('dashboard', 'UserEarning').objects\
        .filter(date__range=(start_date_query, end_date_query), status__gte=get_model('dashboard', 'Sale').PENDING)\
        .order_by('-date')
    if user:
        earnings = earnings.filter(user=user)
    if limit:
        earnings = earnings[:limit]
    earnings_list = []
    for earning in earnings:
        sale = earning.sale
        vendor = sale.vendor
        temp_dict = {}
        temp_dict['user_id'] = sale.user_id

        temp_dict['description_image'] = ''
        temp_dict['description_link'] = ''
        temp_dict['description_text'] = ''

        product_name, product_link, product_image = get_description_for_product(earning.from_product, vendor)
        temp_dict['product_name'] = product_name
        temp_dict['product_link'] = product_link
        temp_dict['product_image'] = product_image

        # Details
        if vendor:
            temp_dict['vendor'] = vendor.id
            temp_dict['sale_id'] = sale.id
            temp_dict['sale_vendor'] = vendor.name
            if earning.sale.affiliate in ('cost_per_click', 'cpc_all_stores'):
                temp_dict['details'] = "Clicks to %s" % vendor.name
            else:
                temp_dict['details'] = map_placement(earning.sale.placement)

        if earning.user_earning_type == "referral_sale_commission":
            temp_dict['details'] = "Referral sale by %s" % earning.from_user
            temp_dict['description_text'] = product_name
            temp_dict['description_link'] = product_link
            temp_dict['description_image'] = product_image
        elif earning.sale.is_promo:
                temp_dict['details'] = "Welcome to APPRL"
        elif earning.user_earning_type == 'publisher_sale_commission':
            temp_dict['description_text'] = product_name
            temp_dict['description_link'] = product_link
            temp_dict['description_image'] = product_image
        elif earning.user_earning_type in ('publisher_network_tribute', 'publisher_network_click_tribute',
                                           'publisher_network_click_tribute_all_stores') :
            temp_dict['description_image'] = earning.from_user.avatar
            temp_dict['description_text'] = earning.from_user.name if earning.from_user.name else earning.from_user.slug
            if earning.sale.affiliate in ('cost_per_click', 'cpc_all_stores'):
                temp_dict['details'] = "Clicks to %s" % vendor.name
            else:
                temp_dict['details'] = map_placement(earning.sale.placement)
        elif earning.sale.affiliate in ('cost_per_click', 'cpc_all_stores'):
            temp_dict['description_text'] = "Clicks to %s" % vendor.name

        # General info
        temp_dict['user_earning_type'] = earning.user_earning_type
        temp_dict['user_earning_type_display'] = earning.get_user_earning_type_display()
        temp_dict['sale_amount'] = "%.2f" % sale.converted_amount
        temp_dict['date_string'] = earning.date.strftime("%Y-%m-%d")
        temp_dict['date_timestamp'] = defaultfilters.date(earning.date, "U")

        temp_dict['from_user_link'] = ''
        if earning.user:
            if not user:
                # We won't supply a user for this function if we're looking at the admin screen, in that case we
                # want to give access to user dashboards
                temp_dict['admin_description_link'] = '{}?__imitera={}'.format(reverse('dashboard-date', args=[year, month]), earning.user_id)
            temp_dict['description_link'] = reverse('profile-likes', args=[earning.user.slug])
            temp_dict['from_user_name'] = earning.user.slug
            temp_dict['from_user_avatar'] = earning.user.avatar
            if earning.user.name:
                temp_dict['from_user_name'] = earning.user.name
        else:
            temp_dict['from_user_name'] = "APPRL"
        temp_dict['clicks'] = get_clicks_from_sale(sale)
        temp_dict['amount'] = "%.2f" % earning.amount

        earnings_list.append(temp_dict)
    return earnings_list

def get_day_range(q_date):
    # Todo: Change this to dates only, remove 23.59:59:99999 and such
    start_date = datetime.datetime.combine(q_date, datetime.time(0, 0, 0, 0))
    end_date = datetime.datetime.combine(q_date, datetime.time(23, 59, 59, 999999))
    return start_date, end_date

def aggregated_data_per_day(start_date, end_date, dashboard_type, values_opt, query_args):
    """
    Return array that contains the aggregated data per day to be displayed in the user dashboard
    """
    aggregated_per_day = get_model('dashboard', 'AggregatedData').objects.\
        filter(**query_args).values(*values_opt)
    data_per_day = {}

    # Initialize array that contains data per day
    for day in range(0, (end_date - start_date).days + 1):
        data_per_day[start_date + datetime.timedelta(day)] = [0, 0, 0, 0, 0, 0]

    if dashboard_type == 'publisher':
        for row in aggregated_per_day:
            data_per_day[row['created'].date()][0] += row['sale_earnings']
            data_per_day[row['created'].date()][1] += row['referral_earnings']
            data_per_day[row['created'].date()][2] += row['click_earnings']
            data_per_day[row['created'].date()][3] += row['total_clicks']
            data_per_day[row['created'].date()][4] += row['network_sale_earnings'] + row['network_click_earnings']
    elif dashboard_type == 'admin':
        for row in aggregated_per_day:
            # Total commission
            data_per_day[row['created'].date()][0] += row['sale_earnings'] + row['referral_earnings'] + row['network_sale_earnings']
            data_per_day[row['created'].date()][2] += row['click_earnings'] + row['network_click_earnings']
            if not row['user_id'] == 0:
                data_per_day[row['created'].date()][1] += row['sale_earnings'] + row['referral_earnings'] + row['network_sale_earnings']
                data_per_day[row['created'].date()][4] += row['total_clicks']
            data_per_day[row['created'].date()][3] += row['total_clicks']
            data_per_day[row['created'].date()][5] += row['paid_clicks']
    return data_per_day

def aggregated_data_per_month(user_id, start_date, end_date):
    """
    Return the AggregatedData summary for the given period
    """
    sum_data = get_model('dashboard', 'AggregatedData').objects.\
                filter(user_id=user_id, created__range=(start_date, end_date),
                       data_type='aggregated_from_total').\
                aggregate(Sum('sale_earnings'), Sum('click_earnings'), Sum('referral_earnings'),
                          Sum('network_sale_earnings'), Sum('network_click_earnings'), Sum('sales'),
                          Sum('network_sales'), Sum('referral_sales'), Sum('paid_clicks'), Sum('total_clicks'))
    return sum_data

def enumerate_months(user, month, is_admin=False):
    """
    Return list of tuples with ID, Text for the different months of the year
    """
    dt1 = user.date_joined.date()
    dt2 = datetime.date.today()
    if is_admin:
        dt1 = dt1.replace(year=2011)
    year_choices = range(dt1.year, dt2.year+1)
    month_display = ""
    month_choices = [(0, _('All year'))]
    for i in range(1,13):
        month_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))
        if month == i:
            month_display = datetime.date(2008, i, 1).strftime('%B')

    return month_display, month_choices, year_choices


def get_admin_aggregated_publishers(start_date, end_date):
    """
    Return AggregatedData summary per publisher for the given period for the admin view.
    """
    filter_dict = dict()
    filter_dict['created__range'] = (start_date, end_date)

    filter_dict['data_type'] = 'aggregated_from_total'
    values_tuple = ('user_id', 'user_name', 'user_username', 'user_link', 'user_image', 'aggregated_from_link')

    # NOTE: the derived field total_earnings_inc_network is a bit weird. It relies on an undocumented part of Django
    # but it seems to work and this is only for an internal screen
    # See: http://stackoverflow.com/a/36024089
    # TODO: After we upgrade to Django >= 1.8, change to using F queries instead.
    top_publishers = get_model('dashboard', 'AggregatedData').objects.filter(**filter_dict).exclude(user_id=0). \
        values(*values_tuple).annotate(total_earnings=Sum('sale_plus_click_earnings'),
                                       total_network_earnings=Sum('total_network_earnings'),
                                       total_earnings_inc_network=Sum('sale_plus_click_earnings', field='sale_plus_click_earnings + total_network_earnings'),
                                       total_clicks=Sum('total_clicks')).order_by('-total_earnings_inc_network',
                                                                                  '-total_earnings', '-total_clicks')

    return top_publishers


def get_aggregated_publishers(user_id, start_date, end_date, include_all_network_influencers=False):
    """
    Return AggregatedData summary for the publisher for the given period
    """
    filter_dict = dict()
    filter_dict['created__range'] = (start_date, end_date)

    filter_dict['data_type'] = 'aggregated_from_publisher'
    values_tuple = ('user_id', 'aggregated_from_id', 'aggregated_from_name', 'aggregated_from_slug',
                    'aggregated_from_image', 'aggregated_from_link')

    # Filter by User, if given user_id
    if user_id:
        filter_dict['user_id'] = user_id

    top_publishers = get_model('dashboard', 'AggregatedData').objects.filter(**filter_dict).exclude(user_id=0).\
        values(*values_tuple).annotate(total_earnings=Sum('sale_plus_click_earnings'),
                                       total_network_earnings=Sum('total_network_earnings'),
                                       total_clicks=Sum('total_clicks')).order_by('-total_network_earnings', '-total_earnings')

    if include_all_network_influencers:
        # If we're looking at the dashboard for a network owner, we want to include all related influencers, even those
        # that haven't generated any earnings
        top_publishers = list(top_publishers)
        earning_influencer_ids = set(p['aggregated_from_id'] for p in top_publishers)
        non_earning_influencers = get_user_model().objects.filter(owner_network__id=user_id).exclude(id__in=earning_influencer_ids).order_by('name')
        for influencer in non_earning_influencers:
            image, link = get_user_thumbnail_and_link(influencer)
            top_publishers.append({
                'user_id': user_id,
                'aggregated_from_id': influencer.id,
                'aggregated_from_name': influencer.name,
                'aggregated_from_slug': influencer.slug,
                'aggregated_from_image': image,
                'aggregated_from_link': link,
                'total_clicks': 0,
                'total_network_earnings': 0,
                'total_earnings': 0
            })
    return top_publishers

def get_aggregated_products(user_id, start_date, end_date):
    """
    Return AggregatedData summary per product for the given period.
    Note that this method uses __range funcion which is non inclusive when using Date.
    """
    filter_dict = dict()
    filter_dict['created__range'] = (start_date, end_date)
    filter_dict['data_type'] = 'aggregated_from_product'
    if user_id:
        network_influencers = get_user_model().objects.filter(owner_network__id=user_id).values_list('id', flat=True)
        if network_influencers:
            filter_dict['user_id__in'] = list(network_influencers) + [user_id]
        else:
            filter_dict['user_id'] = user_id

    top_products = get_model('dashboard', 'AggregatedData').objects.filter(**filter_dict).\
        values('aggregated_from_id', 'aggregated_from_name', 'aggregated_from_slug', 'aggregated_from_image',
               'aggregated_from_link').exclude(user_id=0).\
        annotate(total_earnings=Sum('sale_plus_click_earnings'),
                 total_network_earnings=Sum('total_network_earnings'),
                 total_clicks=Sum('total_clicks')).order_by('-total_network_earnings', '-total_earnings', '-total_clicks')

    return top_products

def get_user_earnings_dashboard(user, start_date, end_date):
    """
    Return user earnings list for a user under the given period
    """
    sale_model = get_model('dashboard', 'Sale')
    user_earnings = get_model('dashboard', 'UserEarning').objects\
        .filter(user=user, date__range=(start_date, end_date), status__gte=sale_model.PENDING)\
        .order_by('-date')
    for earning in user_earnings:
        earning.clicks = get_clicks_from_sale(earning.sale)
        earning.product_image = ''
        earning.product_link = ''
        earning.product_name = ''
        try:
            product = get_model('apparel', 'Product').objects.get(id=earning.sale.product_id)
            product_image, product_link = get_product_thumbnail_and_link(product)
            earning.product_image = product_image
            earning.product_link = product_link
            earning.product_name = product.product_name
        except get_model('apparel', 'Product').DoesNotExist:
            log.warn("Product %s does not exist" % earning.sale.product_id)

        if earning.from_user:
            earning.from_user_name = earning.from_user.slug
            earning.from_user_avatar = earning.from_user.avatar_small
            if earning.from_user.name:
                earning.from_user_name = earning.from_user.name
    return user_earnings

def summarize_earnings(data_per_day):
    """
    Return array with total summaries from the given array of data summarized per day
    """
    month_earnings = sum([x[0] for x in data_per_day])
    network_earnings = sum([x[3] for x in data_per_day])
    referral_earnings = sum([x[1] for x in data_per_day])
    ppc_earnings = sum([x[2] for x in data_per_day])

    return month_earnings, network_earnings, referral_earnings, ppc_earnings

def get_previous_period(start_date, end_date):
    """
    Return start date and end date for the period that comes before the given period
    """
    # Check if it is a month period or a year period
    if start_date.date().month == end_date.date().month:
        last_month_date = start_date.replace(day=1) - datetime.timedelta(days=1)
        prev_month = last_month_date.month
        prev_start_date = start_date.replace(month=prev_month, year=last_month_date.year)
        prev_end_date = prev_start_date
        prev_end_date = prev_start_date.replace(day=calendar.monthrange(prev_end_date.year, prev_end_date.month)[1])
        prev_end_date = datetime.datetime.combine(prev_end_date, datetime.time(23, 59, 59, 999999))
    else:
        prev_year = start_date.date().year - 1
        prev_start_date = start_date.replace(year=prev_year)
        prev_end_date = end_date.replace(year=prev_year)
    return prev_start_date, prev_end_date

def get_relative_change(previous_value, current_value):
    """
    Return relative change in percentage between two positive values
    """
    relative_change = None

    # Assuming values are positive or equal to zero
    if previous_value > 0  and current_value >= 0:
        delta = ((current_value - previous_value) * 100) / previous_value
        delta = int(delta)
        relative_change = ("+%(delta)s%%" % {'delta': delta}) if delta >= 0 else ("%(delta)s%%" % {'delta': delta})
    else:
        log.warning("Current value must be greater or equal than zero. Previous value must be greater than zero "
                    "to calculate percentage change")
    return relative_change

def get_relative_change_summary(prev_summary, current_summary):
    """
    Return array with relative changes in percentage for the Top Summary in the admin dashboard
    """
    relative_list = []
    for prev, current in zip(prev_summary, current_summary):
        relative_list.append(map(get_relative_change, prev, current))
    return relative_list

def get_invalid_clicks(start_date, end_date):
    """
    Return a list with invalid clicks sorted by Total, CPC and CPO
    """
    invalid_clicks_query = get_model('statistics', 'ProductStat').objects.\
                filter(created__range=(start_date, end_date), is_valid=False).\
                values('vendor').\
                annotate(total_clicks=Count('pk')).order_by('-total_clicks')
    invalid_clicks = [0, 0, 0]
    for row in invalid_clicks_query:
        try:
            vendor = get_model('apparel', 'Vendor').objects.get(name=row['vendor'])
            invalid_clicks[0] += row['total_clicks']
            if vendor.is_cpc:
                invalid_clicks[1] += row['total_clicks']
            else:
                invalid_clicks[2] += row['total_clicks']
        except get_model('apparel', 'Vendor').DoesNotExist:
            log.warning("Vendor %s does not exist. No possible identify if vendor is CPC or CPC" % row['vendor'])
    return invalid_clicks

def get_raw_conversion_rate(sales, clicks):
    """
    Return conversion rate on string format given the amount of sale and amount of clicks
    """
    conversion_rate = 0
    if clicks > 0:
            conversion_rate = decimal.Decimal(sales) / decimal.Decimal(clicks)
            conversion_rate = conversion_rate.quantize(decimal.Decimal('0.0001')) * 100
    return conversion_rate

def get_conversion_rate(sales, clicks):
    """
    Return conversion rate on string format given the amount of sale and amount of clicks
    """
    return ("%.2f %%" % get_raw_conversion_rate(sales, clicks))

def get_available_stores(current_location):
    """
    Return a list of vendors depending on the current location value
    """
    vendors = []
    for store in get_model('dashboard', 'StoreCommission').objects.all():
        store_name = store.vendor.name
        try:
            if current_location in settings.VENDOR_LOCATION_MAPPING[store_name]:
                vendors.append(store_name)
        except KeyError:
            vendors.append(store_name)
    return vendors

def render_detail_earnings(request):
    """
    Return a list of user earning details given a date range when an AJAX request is made
    Todo: Very heavy method, need to be fixed.
    """
    json_data = json.dumps({})
    if request.method == 'GET':
        month = request.GET.get('month', None)
        year = request.GET.get('year', None)
        user_id = request.GET.get('user_id', None)
        limit = request.GET.get('limit', None)
        user = None

        if user_id:
            try:
                user = get_user_model().objects.get(id=user_id)
            except get_user_model().DoesNotExist:
                log.warning("User %s does not exist." % user_id)
        if month and year:
            earnings = retrieve_user_earnings(month, year, user, limit)
            json_data = json.dumps(earnings)
    return HttpResponse(json_data)


def get_top_summary(current_user):
    """
    Return Top Summary data for Store Dashboard
    """
    sale_model = get_model('dashboard', 'Sale')
    payment_model = get_model('dashboard', 'Payment')
    pending_earnings = get_model('dashboard', 'UserEarning').objects\
            .filter(user=current_user, status=sale_model.PENDING, paid=sale_model.PAID_PENDING)\
            .aggregate(total=Sum('amount'))['total']

    confirmed_earnings = get_model('dashboard', 'UserEarning')\
            .objects.filter(user=current_user, status=sale_model.CONFIRMED, paid=sale_model.PAID_PENDING)\
            .aggregate(total=Sum('amount'))['total']

    pending_payment = 0
    payments = payment_model.objects.filter(cancelled=False, paid=False, user=current_user).order_by('-created')
    if payments:
        pending_payment = payments[0].amount

    total_earned = 0
    payments = payment_model.objects.filter(paid=True, user=current_user)
    default_currency = 'EUR'
    for pay in payments:
        rate = 1 if pay.currency == 'EUR' else currency_exchange(default_currency, pay.currency)
        total_earned += pay.amount * rate

    return pending_earnings, confirmed_earnings, pending_payment, total_earned

def check_user_has_cpc_all_stores(user):
    """
    Check if user exists, belongs to a partner group and publisher gets paid per click for all stores
    """
    return hasattr(user, 'partner_group') and hasattr(user.partner_group, 'has_cpc_all_stores') \
           and user.partner_group.has_cpc_all_stores