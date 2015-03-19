import decimal
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.db import connection
import logging

from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.fields import ImageField

log = logging.getLogger(__name__)

def dictfetchall(cursor):
    """
        Returns all rows from a cursor as a dict
    """
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def get_referral_user_from_cookie(request):
    user = None
    user_id = request.get_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, None)
    if user_id:
        try:
            user = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            pass

    return user


def get_cuts_for_user_and_vendor(user_id, vendor):
    user = None
    normal_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)
    referral_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)
    publisher_cut = 1

    try:
        user = get_user_model().objects.get(pk=user_id)
        if user.partner_group:
            try:
                cuts = user.partner_group.cuts.get(vendor=vendor)
                normal_cut = cuts.cut
                publisher_cut = cuts.cut
                referral_cut = cuts.referral_cut
                data_exceptions = None

                # Handle exceptions for publisher cuts
                try:
                    data_exceptions = cuts.rules_exceptions
                    for data in data_exceptions:
                        if data['sid'] == user.id:
                            normal_cut = decimal.Decimal(data['cut'])
                except:
                    pass
                if user.owner_network:
                    owner = user.owner_network
                    if owner.owner_network_cut > 1:
                        owner.owner_network_cut = 1
                    publisher_cut -= owner.owner_network_cut

                    # Handle exceptions for Publisher Network owner
                    if data_exceptions:
                        data_exceptions = cuts.rules_exceptions
                        for data in data_exceptions:
                            if data['sid'] == user.id:
                                publisher_cut = 1 - decimal.Decimal(data['tribute'])
            except:
                log.warn("No cut exists for %s and vendor %s, please do correct this." % (user.partner_group,vendor))
    except get_user_model().DoesNotExist:
        pass

    return user, normal_cut, referral_cut, publisher_cut

def get_clicks_list(vendor_name, date, currency, user_id=None):
    """
        Returns a sorted list with detailed information from click earnings per product
        for a given user, vendor and day
    """
    start_date_query = datetime.datetime.combine(date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(date, datetime.time(23, 59, 59, 999999))
    values = [vendor_name, start_date_query, end_date_query]
    vendor = get_model('apparel', 'Vendor').objects.get(name=vendor_name)
    earning_cut = 1
    cursor = connection.cursor()
    click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=vendor)

    start_date_query = datetime.datetime.combine(date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(date, datetime.time(23, 59, 59, 999999))
    sale = get_model('dashboard', 'Sale').objects.filter(vendor=vendor,
                                                      type=get_model('dashboard', 'Sale').COST_PER_CLICK,
                                                      sale_date__range=[start_date_query, end_date_query])

    exchange_rate = 1
    if currency == "EUR":
        exchange_rate = sale[0].exchange_rate
    if user_id:
        try:
            user = get_user_model().objects.get(id=user_id)
            _, cut, _, publisher_cut = get_cuts_for_user_and_vendor(user_id, vendor)
            earning_cut = cut * publisher_cut
            values.append(user_id)
            cursor.execute(
                """SELECT PS.vendor, PS.user_id, PS.product, count(PS.id)
                   FROM statistics_productstat PS, profile_user U, apparel_vendor V
                   WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
                   AND V.is_cpc = True AND PS.created BETWEEN %s AND %s AND U.id = %s
                   GROUP BY PS.user_id, PS.vendor, PS.product ORDER BY count(PS.id) DESC""", values)
        except get_user_model().DoesNotExist:
            log.warn("User %s does not exist" % user)
    else:
        cursor.execute(
            """SELECT PS.vendor, PS.product, count(PS.id)
               FROM statistics_productstat PS, profile_user U, apparel_vendor V
               WHERE PS.user_id = U.id AND V.name = %s AND PS.vendor = V.name AND U.is_partner = True
               AND V.is_cpc = True AND PS.created BETWEEN %s AND %s
               GROUP BY PS.vendor, PS.product ORDER BY count(PS.id) DESC""", values)
    data = dictfetchall(cursor)
    for row in data:
        try:
            product = get_model('apparel', 'Product').objects.get(slug=row['product'])
            row['product_url'] = reverse('product-detail', args=[row['product']])
            row['product_name'] = product.product_name
            row['product_earning'] = float(int(row['count']) * click_cost.amount * earning_cut * exchange_rate)
        except get_model('apparel', 'Product').DoesNotExist:
            log.warn("Product %s does not exist" % row['product'])
    return data

def get_product_thumbnail_and_link(product):
    """
        Returns thumbnail and link for a product
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
        Returns total amount in EUR for a Vendor in given date range
    """
    total_amount = 0
    currency = None
    for item in get_model('dashboard', 'Sale').objects.filter(vendor=vendor,
                                                              sale_date__range=[start_date_query, end_date_query],
                                                              type=get_model('dashboard', 'Sale').COST_PER_CLICK):
        total_amount += item.original_amount
        if not currency and item.original_currency:
            currency = item.original_currency
    return total_amount, currency

def get_number_clicks(vendor, start_date_query, end_date_query):
    """
        Return total number of clicks for a Vendor in a given date range
    """
    return get_model('statistics', 'ProductStat').objects.\
        filter(vendor=vendor, created__range=[start_date_query, end_date_query]).count()

def get_total_clicks_per_vendor(vendor):
    """
        Returns total amount of clicks for a Vendor
    """
    return get_model('statistics', 'ProductStat').objects.filter(vendor=vendor).count()