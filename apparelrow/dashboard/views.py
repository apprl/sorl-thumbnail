import datetime
import calendar
import decimal
import operator
import re
import json

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, Http404
from django.db.models import get_model, Sum, Count
from django.forms import ModelForm
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _, get_language
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib import messages
from django.template.loader import render_to_string


from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.fields import ImageField

from apparelrow.dashboard.models import Sale, Payment, Signup
from apparelrow.dashboard.tasks import send_email_task
from apparelrow.dashboard.utils import get_referral_user_from_cookie, get_cuts_for_user_and_vendor, get_clicks_list, get_product_thumbnail_and_link
from apparelrow.apparel.utils import currency_exchange
from apparelrow.profile.tasks import mail_managers_task
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView



import logging
log = logging.getLogger(__name__)

def map_placement(placement):
    link = _('Unknown')
    if placement == 'Ext-Shop':
        link = _('Shop on your site')
    elif placement == 'Ext-Look':
        link = _('Look on your site')
    elif placement == 'Ext-Link':
        link = _('Product link on your site')
    elif placement == 'Ext-Store':
        link = _('Store link on your site')
    elif placement == 'Look':
        link = _('Look on Apprl.com')
    elif placement == 'Shop':
        link = _('Shop on Apprl.com')
    elif placement == 'Feed':
        link = _('Feed on Apprl.com')
    elif placement == 'Profile':
        link = _('Your profile on Apprl.com')
    elif placement == 'Product':
        link = _('Product page')
    elif placement == 'Ext-Banner':
        link = _('Banner on your site')

    return link

def get_conversion_rate(sales, clicks):
    """ Return conversion rate on string format given the amount of sale and amount of clicks
    """
    conversion_rate = 0
    if clicks > 0:
            conversion_rate = decimal.Decimal(sales) / decimal.Decimal(clicks)
            conversion_rate = conversion_rate.quantize(decimal.Decimal('0.0001')) * 100
    return ("%.2f %%" % conversion_rate)

def get_available_stores(current_location):
    """ Return a list of vendors depending on the current location value
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

def get_most_clicked_products(start_date, end_date, user_id=None, limit=5):
    user_criteria = ''
    values = [start_date, end_date, limit]
    if user_id:
        user_criteria = 'WHERE sp.user_id = %s'
        values = [start_date, end_date, user_id, limit]

    product_table = get_model('apparel', 'Product').objects.raw("""
            SELECT ap.id, ap.slug, ap.product_name, ap.product_image, ab.name AS brand_name, COUNT(sp.id) AS clicks
            FROM apparel_product ap
            INNER JOIN apparel_brand ab ON ab.id = ap.manufacturer_id
            INNER JOIN statistics_productstat sp ON ap.slug = sp.product AND sp.created BETWEEN %s AND %s
            {0} GROUP BY ap.id, ab.name
            ORDER BY clicks DESC
            LIMIT %s
        """.format(user_criteria), values)
    most_clicked_products = []
    for product in product_table:
        product_image, product_link = get_product_thumbnail_and_link(product)

        most_clicked_products.append({
            'product_image': product_image,
            'product_link': product_link,
            'product': '%s %s' % (product.brand_name, product.product_name) if product.product_name else _('Unknown'),
            'clicks': product.clicks
        })

    return most_clicked_products

def get_publishers(start_date, end_date, user_id=None, limit=5, see_all=True):
    owner_user = None
    if user_id:
        owner_user = get_user_model().objects.get(pk=user_id)

    # If user is a Network owner, fetch all publishers that belongs to the user's Network
    if owner_user:
        publishers = get_user_model().objects.filter(owner_network=owner_user)
    else:
        publishers = get_user_model().objects.all()

    top_publishers = []
    temp_product_prod = []
    most_sold = {}
    for publisher in publishers:
        user_criteria = ''
        values = [start_date, end_date, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]
        if not user_id:
            owner_user = publisher.owner_network

        if user_id:
            user_criteria = 'ds.user_id = %s AND'
            values = [start_date, end_date, publisher.id, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]

        sale_table = Sale.objects.raw("""
                SELECT ds.id, ds.created, ds.commission, ds.currency, ds.placement, ds.converted_commission, ds.user_id,
                       ds.is_referral_sale, ds.referral_user_id, ds.is_promo, ds.converted_amount,
                       ap.slug, ap.product_name, ap.product_image, pu.image, ab.name AS brand_name, COUNT(sp.id)
                       AS clicks, pu.name
                FROM dashboard_sale ds
                LEFT OUTER JOIN profile_user pu ON pu.id = ds.user_id
                LEFT OUTER JOIN apparel_product ap ON ds.product_id = ap.id
                LEFT OUTER JOIN apparel_brand ab ON ab.id = ap.manufacturer_id
                LEFT OUTER JOIN statistics_productstat sp
                    ON ds.user_id = sp.user_id AND ap.slug = sp.product AND sp.created BETWEEN %s AND %s
                WHERE
                    {0}
                    ds.status BETWEEN %s AND %s AND
                    ds.sale_date BETWEEN %s AND %s
                GROUP BY ds.id, ap.product_name, ap.product_image, ap.slug, ab.name, pu.name, pu.image
                ORDER BY ds.created DESC
            """.format(user_criteria), values)

        user_dict = {}
        temp_products = []
        publisher_image = ''

        try:
            publisher_image = get_thumbnail(ImageField().to_python(publisher.image), '50', crop='noop').url
        except:
            pass

        for sale in sale_table:
            if not sale.is_promo:
                product_image, product_link = get_product_thumbnail_and_link(sale)
                network_earnings = 0
                network_click_earnings = 0
                publisher_earnings = 0
                publisher_click_earnings = 0
                total_earnings = 0
                earnings = None
                converted_amount = 0
                try:
                    # Owner earnings
                    earnings = get_model('dashboard', 'UserEarning').objects.get(user=owner_user, sale=sale)
                    total_earnings = earnings.amount
                    converted_amount = sale.converted_amount

                    if earnings.user_earning_type == 'publisher_network_tribute':
                        network_earnings = earnings.amount
                    elif earnings.user_earning_type == 'publisher_network_click_tribute':
                        network_click_earnings = earnings.amount

                    # Publisher earnings
                    earnings = get_model('dashboard', 'UserEarning').objects.get(user=publisher, sale=sale)
                    if earnings.user_earning_type == 'publisher_sale_commission':
                        publisher_earnings = earnings.amount
                    if earnings.user_earning_type == 'publisher_sale_click_commission':
                        publisher_click_earnings = earnings.amount

                except get_model('dashboard', 'UserEarning').DoesNotExist:
                    pass
                temp = {
                    'converted_amount': converted_amount,
                    'currency': sale.currency,
                    'clicks': sale.clicks,
                    'sales': 0,
                    'publisher_earnings': publisher_earnings,
                    'network_earnings': network_earnings + network_click_earnings,
                    'publisher_click_earnings': publisher_click_earnings,
                    'product': '%s %s' % (sale.brand_name, sale.product_name) if sale.product_name else _('Unknown'),
                    'user': sale.name if sale.name else '%s' % (publisher.username),
                    'product_image': product_image,
                    'product_link': product_link,
                    'publisher_image': publisher_image,
                    'publisher_link': reverse('profile-likes', args=[publisher.username]),
                    'total_earnings': total_earnings,
                    'total_network_earnings': publisher_earnings + publisher_click_earnings
                }
                if user_dict:
                    if earnings:
                        user_dict['sales'] += 1
                    user_dict['converted_amount'] += temp['converted_amount']
                    user_dict['network_earnings'] += temp['network_earnings']
                    user_dict['publisher_earnings'] += temp['publisher_earnings']
                    user_dict['publisher_click_earnings'] += temp['publisher_click_earnings']
                    user_dict['total_network_earnings'] += temp['total_network_earnings']
                    if temp['product']:
                        if not temp['product'] in temp_products:
                            user_dict['clicks'] += temp['clicks']
                            temp_products.append(temp['product'])
                else:
                    if temp['clicks'] > 0:
                        temp_products.append(temp['product'])
                    user_dict = dict(temp)
                    if earnings:
                        user_dict['sales'] = 1
                    else:
                        user_dict['sales'] = 0

                if sale.product_name:
                    if temp['product'] in most_sold:
                        if earnings:
                            most_sold[temp['product']]['sales'] += 1
                        most_sold[temp['product']]['converted_amount'] += temp['converted_amount']
                        most_sold[temp['product']]['publisher_earnings'] += temp['publisher_earnings']
                        most_sold[temp['product']]['publisher_click_earnings'] += temp['publisher_click_earnings']
                        most_sold[temp['product']]['network_earnings'] += temp['network_earnings']

                        most_sold[temp['product']]['total_earnings'] += temp['total_earnings']
                        most_sold[temp['product']]['total_network_earnings'] += temp['total_network_earnings']
                        if temp['product']:
                            if not temp['product'] in temp_product_prod:
                                most_sold[temp['product']]['clicks'] += temp['clicks']
                                temp_product_prod.append(temp['product'])
                    else:
                        most_sold[temp['product']] = dict(temp)
                        if earnings:
                            most_sold[temp['product']]['sales'] = 1
                        else:
                            most_sold[temp['product']]['sales'] = 0
                        if most_sold[temp['product']]['clicks'] > 0:
                            temp_product_prod.append(temp['product'])
        if user_dict:
            top_publishers.append(user_dict)
        elif not user_dict and see_all:
            temp = {
                'converted_amount': decimal.Decimal(0.00),
                'currency': 'EUR',
                'clicks': 0,
                'sales': 0,
                'publisher_earnings': decimal.Decimal(0.00),
                'total_network_earnings': decimal.Decimal(0.00),
                'publisher_click_earnings': decimal.Decimal(0.00),
                'network_earnings': decimal.Decimal(0.00),
                'user': publisher.name if publisher.name else '%s' % (publisher.username),
                'publisher_image': publisher_image,
                'publisher_link': reverse('profile-likes', args=[publisher.username]),
            }
            top_publishers.append(temp)
    sorted_top_publishers = sorted(top_publishers, key=operator.itemgetter('total_network_earnings'), reverse=True)[:limit]
    most_sold_products = [x for x in sorted(most_sold.values(), key=lambda x: (x['sales'], x['total_earnings']), reverse=True)[:limit] if x['sales'] > 0]
    return sorted_top_publishers, most_sold_products

def get_publishers_admin(start_date, end_date, limit=5, see_all=True):
    top_publishers = {}
    most_sold = {}
    temp_product_prod = []
    temp_users = []
    sales = get_model('dashboard','Sale').objects.filter(sale_date__range=(start_date, end_date))
    for sale in sales:
        try:
            product = get_model('apparel', 'Product').objects.get(id=sale.product_id)
            product_link = None
        except get_model('apparel', 'Product').DoesNotExist:
            product = None

        if not sale.is_promo:
            product_name = ''
            product_image = ''
            product_link = ''

            if product:
                product_name = '%s %s' % (product.static_brand, product.product_name) if product.product_name else _('Unknown')
                product_image, product_link = get_product_thumbnail_and_link(product)

            temp = {
                'converted_amount': sale.converted_amount,
                'currency': sale.currency,
                'sales': 0,
                'total_earnings': sale.converted_commission,
                'publisher_earnings': decimal.Decimal(0.00),
                'publisher_click_earnings': decimal.Decimal(0.00),
                'network_earnings': decimal.Decimal(0.00),
                'total_network_earnings': decimal.Decimal(0.00),
                'product': product_name,
                'user': '',
                'product_image': product_image,
                'product_link': product_link,
                'publisher_image': '',
                'publisher_link': '',
                'clicks': 0
            }

            earnings = get_model('dashboard', 'UserEarning').objects.filter(sale=sale)
            for earning in earnings:

                if earning.user_earning_type != "apprl_commission" and earning.user:
                    earning_user = earning.user
                    publisher_earnings = 0
                    publisher_click_earnings = 0
                    network_earnings = 0
                    network_click_earnings = 0
                    if earning.user_earning_type == 'publisher_network_tribute':
                        network_earnings = earning.amount
                    elif earning.user_earning_type == 'publisher_network_click_tribute':
                        network_click_earnings = earning.amount
                    elif earning.user_earning_type == 'publisher_sale_commission':
                        publisher_earnings = earning.amount
                    elif earning.user_earning_type == 'publisher_sale_click_commission':
                        publisher_click_earnings = earning.amount

                    publisher_image = ''
                    try:
                        publisher_image = get_thumbnail(ImageField().to_python(earning_user.image), '50', crop='noop').url
                    except:
                        pass
                    temp['publisher_earnings'] = publisher_earnings
                    temp['publisher_click_earnings'] = publisher_click_earnings
                    temp['network_earnings'] = network_earnings + network_click_earnings
                    temp['publisher_image'] = publisher_image
                    temp['publisher_link'] = reverse('profile-likes', args=[earning_user.username])
                    temp['clicks'] = 0
                    temp['total_network_earnings'] = temp['publisher_earnings'] + temp['publisher_click_earnings']
                    temp['user'] = earning_user.name if earning_user.name else '%s' % (earning_user.username)

                    # save publisher data
                    if temp['user'] in top_publishers:
                        if earning.user_earning_type == "publisher_sale_commission":
                            top_publishers[temp['user']]['sales'] += 1
                        top_publishers[temp['user']]['converted_amount'] += temp['converted_amount']
                        top_publishers[temp['user']]['publisher_earnings'] += temp['publisher_earnings']
                        top_publishers[temp['user']]['publisher_click_earnings'] += temp['publisher_click_earnings']
                        top_publishers[temp['user']]['network_earnings'] += temp['network_earnings']
                        top_publishers[temp['user']]['total_network_earnings'] += temp['total_network_earnings']
                        if not temp['user'] in temp_users and earning.user_earning_type == "publisher_sale_commission":
                            temp_users.append(temp['user'])
                    else:
                        temp_users.append(temp['user'])
                        top_publishers[temp['user']] = dict(temp)
                        publisher_clicks = get_model('statistics', 'ProductStat').objects.\
                        filter(user_id=earning_user.id, created__range=(start_date, end_date)).aggregate(total=Count('user_id'))['total']
                        top_publishers[temp['user']]['clicks'] = publisher_clicks
                        if earning.user_earning_type == "publisher_sale_commission":
                            top_publishers[temp['user']]['sales'] = 1
                        else:
                            top_publishers[temp['user']]['sales'] = 0

            # if product, save product information
            if product and product.product_name:
                if temp['product'] in most_sold:
                    if earnings:
                        most_sold[temp['product']]['sales'] += 1
                        most_sold[temp['product']]['converted_amount'] += temp['converted_amount']
                        most_sold[temp['product']]['publisher_earnings'] += temp['publisher_earnings']
                        most_sold[temp['product']]['publisher_click_earnings'] += temp['publisher_click_earnings']
                        most_sold[temp['product']]['network_earnings'] += temp['network_earnings']
                        most_sold[temp['product']]['total_earnings'] += temp['total_earnings']
                        most_sold[temp['product']]['total_network_earnings'] += temp['total_network_earnings']
                        if not temp['product'] in temp_product_prod:
                            temp_product_prod.append(temp['product'])
                else:
                    most_sold[temp['product']] = dict(temp)
                    product_clicks = get_model('statistics', 'ProductStat').objects.\
                        filter(product=product.slug, created__range=(start_date, end_date)).aggregate(total=Count('product'))['total']
                    most_sold[temp['product']]['clicks'] = product_clicks
                    if earnings:
                        most_sold[temp['product']]['sales'] = 1
                    else:
                        most_sold[temp['product']]['sales'] = 0
                    if most_sold[temp['product']]['clicks'] > 0:
                        temp_product_prod.append(temp['product'])


    all_users = get_user_model().objects.filter(is_partner=True)
    for user in all_users:
        user_name = user.name if user.name else '%s' % (user.username)
        if not user_name in top_publishers:
            publisher_image = ''
            try:
                publisher_image = get_thumbnail(ImageField().to_python(user.image), '50', crop='noop').url
            except:
                pass
            temp = {
                'converted_amount': decimal.Decimal(0.00),
                'currency': 'EUR',
                'clicks': 0,
                'sales': 0,
                'publisher_earnings': decimal.Decimal(0.00),
                'publisher_click_earnings': decimal.Decimal(0.00),
                'network_earnings': decimal.Decimal(0.00),
                'user': user_name,
                'publisher_image': publisher_image,
                'publisher_link': reverse('profile-likes', args=[user.username]),
                'total_earnings': decimal.Decimal(0.00),
                'total_network_earnings': decimal.Decimal(0.00),
            }
            top_publishers[temp['user']] = dict(temp)
    sorted_top_publishers = [x for x in sorted(top_publishers.values(), key=lambda x: (x['total_network_earnings'], x['network_earnings']), reverse=True)[:limit]]
    most_sold_products = [x for x in sorted(most_sold.values(), key=lambda x: (x['sales'], x['publisher_earnings']), reverse=True)[:limit] if x['sales'] > 0]
    return sorted_top_publishers, most_sold_products

def get_sales(start_date, end_date, user_id=None, limit=5):
    user_criteria = ''
    values = [start_date, end_date, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]
    if user_id:
        user_criteria = 'ds.user_id = %s AND'
        values = [start_date, end_date, user_id, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]

    sale_table = Sale.objects.raw("""
            SELECT ds.id, ds.created, ds.commission, ds.currency, ds.placement, ds.converted_commission, ds.user_id,
                   ds.is_referral_sale, ds.referral_user_id, ds.is_promo, ds.converted_amount,
                   ap.slug, ap.product_name, ap.product_image, ab.name AS brand_name, COUNT(sp.id) AS clicks, pu.name
            FROM dashboard_sale ds
            LEFT OUTER JOIN profile_user pu ON pu.id = ds.user_id
            LEFT OUTER JOIN apparel_product ap ON ds.product_id = ap.id
            LEFT OUTER JOIN apparel_brand ab ON ab.id = ap.manufacturer_id
            LEFT OUTER JOIN statistics_productstat sp
                ON ds.user_id = sp.user_id AND ap.slug = sp.product AND sp.created BETWEEN %s AND %s
            WHERE
                {0}
                ds.status BETWEEN %s AND %s AND
                ds.sale_date BETWEEN %s AND %s
            GROUP BY ds.id, ap.product_name, ap.product_image, ap.slug, ab.name, pu.name
            ORDER BY ds.created DESC
        """.format(user_criteria), values)
    sales = []
    temp_products = []
    most_sold = {}
    for sale in sale_table:
        product_image, product_link = get_product_thumbnail_and_link(sale)
        apprl_commission = sale.converted_commission if sale.user_id == 0 else sale.converted_commission - sale.commission
        referral_user = None
        if sale.is_referral_sale:
            try:
                referral_user = get_user_model().objects.get(pk=sale.referral_user_id)
            except get_user_model().DoesNotExist:
                pass

            apprl_commission = decimal.Decimal('0')

        amount = 0
        total_earnings = 0
        if user_id:
            sale_user = get_user_model().objects.get(pk=sale.user_id)
            try:
                earnings = get_model('dashboard', 'UserEarning').objects.get(user=sale_user, sale=sale)
                amount = earnings.amount
                total_earnings = amount
            except get_model('dashboard', 'UserEarning').DoesNotExist:
                pass
        else:
            try:
                earnings = get_model('dashboard', 'UserEarning').objects.get(sale=sale, user_earning_type="apprl_commission")
                amount = earnings.amount
            except get_model('dashboard', 'UserEarning').DoesNotExist:
                pass
        temp = {
            'id': sale.id,
            'is_promo': sale.is_promo,
            'is_referral_sale': sale.is_referral_sale,
            'referral_user': referral_user,
            'converted_amount': sale.converted_amount,
            'link': map_placement(sale.placement),
            'placement': sale.placement,
            'vendor': sale.vendor,
            'link_raw': sale.placement,
            'commission': 0 if sale.user_id == 0 else sale.commission,
            'apprl_commission': apprl_commission,
            'currency': sale.currency,
            'created': sale.created,
            'product_image': product_image,
            'product_link': product_link,
            'product': '%s %s' % (sale.brand_name, sale.product_name) if sale.product_name else _('Unknown'),
            'clicks': sale.clicks,
            'sales': 0,
            'user': sale.name if sale.name else '(%s)' % (sale.user_id,),
            'publisher_earnings': amount,
            'network_earnings': 0,
            'total_earnings': total_earnings,
        }
        if sale.product_name:
            if temp['product'] in most_sold:
                most_sold[temp['product']]['sales'] += 1
                most_sold[temp['product']]['commission'] += temp['commission']
                most_sold[temp['product']]['apprl_commission'] += temp['apprl_commission']
                most_sold[temp['product']]['publisher_earnings'] += temp['publisher_earnings']
                most_sold[temp['product']]['converted_amount'] += temp['converted_amount']
                most_sold[temp['product']]['total_earnings'] += temp['total_earnings']
                if temp['product']:
                    if not temp['product'] in temp_products:
                        most_sold[temp['product']]['clicks'] += temp['clicks']
                        temp_products.append(temp['product'])
            else:
                temp['sales'] = 1
                most_sold[temp['product']] = dict(temp)
                if temp['clicks'] > 0:
                    temp_products.append(temp['product'])
        sales.append(temp)
    most_sold_products = [x for x in sorted(most_sold.values(), key=lambda x: x['sales'], reverse=True)[:limit]
                          if x['sales'] > 0]
    return sales, most_sold_products

def merge_top_products(most_sold_products, network_publishers, limit=5):
    network_total_publishers = {}
    temp_products = []
    for temp in most_sold_products:
        if temp['product'] in network_total_publishers:
            network_total_publishers[temp['product']]['sales'] += temp['sales']
            network_total_publishers[temp['product']]['commission'] += temp['commission']
            network_total_publishers[temp['product']]['apprl_commission'] += temp['apprl_commission']
            network_total_publishers[temp['product']]['publisher_earnings'] += temp['publisher_earnings']
            network_total_publishers[temp['product']]['converted_amount'] += temp['converted_amount']
            network_total_publishers[temp['product']]['total_earnings'] += temp['total_earnings']
            network_total_publishers[temp['product']]['clicks'] += temp['clicks']
        else:
            network_total_publishers[temp['product']] = dict(temp)
            if temp['clicks'] > 0:
                temp_products.append(temp['product'])

    for temp in network_publishers:
        if temp['product'] in network_total_publishers:
            network_total_publishers[temp['product']]['sales'] += temp['sales']
            network_total_publishers[temp['product']]['publisher_earnings'] += temp['publisher_earnings']
            network_total_publishers[temp['product']]['network_earnings'] += temp['network_earnings']
            network_total_publishers[temp['product']]['converted_amount'] += temp['converted_amount']
            network_total_publishers[temp['product']]['total_earnings'] += temp['total_earnings']
            network_total_publishers[temp['product']]['clicks'] += temp['clicks']
        else:
            network_total_publishers[temp['product']] = dict(temp)
            if temp['clicks'] > 0:
                temp_products.append(temp['product'])

    network_total_products = [x for x in sorted(network_total_publishers.values(),
                                                key=lambda x: (x['total_earnings'], x['sales']),
                                                reverse=True)[:limit]]
    return network_total_products

def get_network_clicks(publisher_list=None):
    network_clicks = 0
    if publisher_list:
        for publisher in publisher_list:
            network_clicks += publisher['clicks']
    return network_clicks


class SignupForm(ModelForm):

    def __init__(self, *args, **kwargs):
        is_store_form = False
        if 'is_store_form' in kwargs:
            is_store_form = True
            del kwargs['is_store_form']

        super(SignupForm, self).__init__(*args, **kwargs)

        if is_store_form:
            self.fields['blog'].label = 'Store URL'
        else:
            self.fields['blog'].label = 'URL'

    class Meta:
        model = Signup
        fields = ('name', 'email', 'blog', 'traffic')

def dashboard_group_admin(request, pk):
    if request.user.is_authenticated() and (request.user.is_superuser or request.user.pk == int(pk)):
        group = None
        try:
            group = get_model('dashboard', 'Group').objects.get(owner=pk)
        except:
            raise Http404

        users = []
        for user in get_user_model().objects.filter(partner_group__owner=pk, is_partner=True):
            sales_total = decimal.Decimal('0')
            sales_pending = Sale.objects.filter(user_id=user.pk, status=Sale.PENDING,
                                                paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
            if sales_pending:
                sales_total += sales_pending
            else:
                sales_pending = decimal.Decimal('0')
            sales_confirmed = Sale.objects.filter(user_id=user.pk, status=Sale.CONFIRMED,
                                                  paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
            if sales_confirmed:
                sales_total += sales_confirmed
            else:
                sales_confirmed = decimal.Decimal('0')

            # Pending payment
            pending_payment = 0
            payments = Payment.objects.filter(cancelled=False, paid=False, user=user).order_by('-created')
            if payments:
                pending_payment = payments[0].amount

            users.append({
                'user': user,
                'total': sales_total,
                'confirmed': sales_confirmed,
                'pending_payment': pending_payment,
            })

        sum_total = sum(user['total'] for user in users)
        sum_confirmed = sum(user['confirmed'] for user in users)
        sum_pending_payment = sum(user['pending_payment'] for user in users)

        owner = get_user_model().objects.get(pk=pk)
        owner_total = sum_total * group.owner_cut
        owner_confirmed = sum_confirmed * group.owner_cut
        owner_pending_payment = sum_confirmed * group.owner_cut

        context = {
            'users': users,
            'owner': owner,
            'sum_total': sum_total,
            'sum_confirmed': sum_confirmed,
            'sum_pending_payment': sum_pending_payment,
            'owner_total': owner_total,
            'owner_confirmed': owner_confirmed,
            'owner_pending_payment': owner_pending_payment,
            'total_total': sum_total + owner_total,
            'total_confirmed': sum_confirmed + owner_confirmed,
            'total_pending_payment': sum_pending_payment + owner_pending_payment,
        }

        return render(request, 'dashboard/publisher_group.html', context)

    raise Http404

#@cache_page(60 * 15)
def dashboard_admin(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.is_superuser:
        if year is None and month is None:
            start_date = datetime.date.today().replace(day=1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        else:
            start_date = datetime.date(int(year), int(1), 1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)

            if month != "0":
                start_date = datetime.date(int(year), int(month), 1)

                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        year = start_date.year
        if month != "0":
            month = start_date.month

        # Enumerate months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        years_choices = range(dt1.year, dt2.year+1)
        month_display = ""

        months_choices = [(0, _('All year'))]
        for i in range(1,13):
            months_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))
            if month == i:
                month_display = datetime.date(2008, i, 1).strftime('%B')

        # Per month
        data_per_month = {}
        for day in range(0, (end_date - start_date).days + 2):
            data_per_month[start_date+datetime.timedelta(day)] = [0, 0, 0, 0, 0, 0, 0, 0]

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        # Commission per month
        month_commission = decimal.Decimal('0.0')
        partner_commission = decimal.Decimal('0.0')

        # Clicks per month
        clicks = get_model('statistics', 'ProductStat')\
            .objects.filter(created__range=(start_date_query, end_date_query)).values('created', 'user_id')
        for click in clicks:
            data_per_month[click['created'].date()][2] += 1
            if click['user_id']:
                data_per_month[click['created'].date()][3] += 1

        click_total = sum([x[2] for x in data_per_month.values()])
        click_partner = sum([x[3] for x in data_per_month.values()])
        click_apprl = click_total - click_partner

        # Enumerate months
        dt1 = datetime.date(2012, 1, 1)
        dt2 = datetime.date.today()
        start_month = dt1.month
        end_months = (dt2.year - dt1.year) * 12 + dt2.month + 1
        dates = [datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
            ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
        )]

        # Sales top products and top publishers
        sales, most_sold_products = get_sales(start_date_query, end_date_query, limit=50)
        top_publishers, network_publishers = get_publishers_admin(start_date_query, end_date_query, limit=50)

        # Most clicked products
        most_clicked_products = get_most_clicked_products(start_date_query, end_date_query, limit=50)

        earnings = get_model('dashboard', 'UserEarning').objects\
            .filter(date__range=(start_date_query, end_date_query), status__gte=Sale.PENDING)\
            .order_by('-date')
        for earning in earnings:
            earning.extra_sale = None
            for sale in sales:
                if earning.sale.id == sale['id']:
                    earning.extra_sale = sale
            sale = get_model('dashboard', 'Sale').objects.get(id=earning.sale.id)
            earning.product_image = ''
            earning.product_link = ''
            earning.product_name= ''
            try:
                product = get_model('apparel', 'Product').objects.get(id=sale.product_id)
                product_image, product_link = get_product_thumbnail_and_link(product)
                earning.product_image = product_image
                earning.product_link = product_link
                earning.product_name = product.product_name
            except get_model('apparel', 'Product').DoesNotExist:
                pass
            earning.from_user_link = ''
            if earning.user:
                earning.from_user_link = reverse('profile-likes', args=[earning.user.slug])
                earning.from_user_name = earning.user.slug
                earning.from_user_avatar = earning.user.avatar_small
                if earning.user.name:
                    earning.from_user_name = earning.user.name
            else:
                earning.from_user_name = "APPRL"

            earning.clicks = get_clicks_from_sale(earning.sale)


        sales_count = [0, 0, 0] #total, publisher, apprl
        total_apprl_earnings = 0
        total_publisher_earnings = 0
        total_cpo_publisher_earnings = 0
        cpo_publisher_earnings = 0
        apprl_ppc_earnings = 0
        absolute_total_earnings = 0

        sales_result = Sale.objects.filter(status__gte=Sale.PENDING,
                                           sale_date__range=(start_date_query, end_date_query))
        for sale in sales_result:
            sale_earnings = get_model('dashboard', 'UserEarning').objects.filter(sale=sale, status__gte=Sale.PENDING)
            for earning in sale_earnings:
                absolute_total_earnings += earning.amount
                if sale.type == Sale.COST_PER_CLICK:
                    data_per_month[earning.date.date()][6] += earning.amount
                    if earning.user:
                        data_per_month[earning.date.date()][4] += earning.amount
                    else:
                        apprl_ppc_earnings += earning.amount
                elif sale.type == Sale.COST_PER_ORDER:
                    data_per_month[earning.date.date()][0] += earning.amount
                    total_cpo_publisher_earnings += earning.amount
                    if earning.user:
                        data_per_month[earning.date.date()][1] += earning.amount
                        cpo_publisher_earnings += earning.amount

                if earning.user_earning_type == 'apprl_commission':
                    total_apprl_earnings += earning.amount
                else:
                    total_publisher_earnings += earning.amount


            # Clicks
            if sale.type == Sale.COST_PER_CLICK:
                if sale.user_id != 0:
                    data_per_month[sale.sale_date.date()][5] += get_clicks_from_sale(sale)
                else:
                    data_per_month[sale.sale_date.date()][7] += get_clicks_from_sale(sale)

            if sale.type == Sale.COST_PER_ORDER:
                sales_count[0] += 1
                if sale.user_id:
                    sales_count[1] += 1
                else:
                    sales_count[2] += 1

        ppc_clicks_publisher = sum([x[5] for x in data_per_month.values()])
        ppc_clicks_apprl = sum([x[7] for x in data_per_month.values()])

        # Calculate CPC earnings
        publisher_ppc_earnings = sum([x[4] for x in data_per_month.values()])
        total_ppc_earnings = sum([x[6] for x in data_per_month.values()])

        # Calculate CPO clicks
        commission_clicks_publisher = click_partner - ppc_clicks_publisher
        commission_clicks_apprl = click_apprl - ppc_clicks_apprl
        commission_clicks_total = commission_clicks_publisher + commission_clicks_apprl

        # Build table in the dashboard admin top
        headings = ['Earnings', 'Commission', 'PPC earnings', 'PPC clicks', 'Commission clicks', 'Commission sales',
                    'Commission CR']
        total_top = ['%.2f EUR' % (absolute_total_earnings),
                     '%.2f EUR' % total_cpo_publisher_earnings,
                     ('%.2f EUR' % total_ppc_earnings),
                     (ppc_clicks_publisher + ppc_clicks_apprl),
                     commission_clicks_total,
                     sales_count[0],
                     get_conversion_rate(sales_count[0], commission_clicks_total)]
        publisher_top = ['%.2f EUR' % (total_publisher_earnings),
                         '%.2f EUR' % cpo_publisher_earnings,
                         '%.2f EUR' % publisher_ppc_earnings,
                         ppc_clicks_publisher,
                         commission_clicks_publisher,
                         sales_count[1],
                         get_conversion_rate(sales_count[1], commission_clicks_publisher)]
        apprl_top = ['%.2f' % (total_apprl_earnings),
                     '%.2f' % (total_cpo_publisher_earnings - cpo_publisher_earnings),
                     '%.2f' % apprl_ppc_earnings,
                     ppc_clicks_apprl,
                     commission_clicks_apprl,
                     sales_count[2],
                     get_conversion_rate(sales_count[2], commission_clicks_apprl)]

        monthly_array = zip(headings, total_top, publisher_top, apprl_top)

        return render(request, 'dashboard/admin.html', {'sales': data_per_month,
                                                        'sales_count': sales_count,
                                                        'click_total': click_total,
                                                        'click_partner': click_partner,
                                                        'click_apprl': click_apprl,
                                                        'dates': dates,
                                                        'month_display': month_display,
                                                        'years_choices': years_choices,
                                                        'months_choices': months_choices,
                                                        'year': year,
                                                        'month': month,
                                                        'currency': 'EUR',
                                                        'sales_table': sales,
                                                        'most_sold_products': network_publishers,
                                                        'top_publishers': top_publishers,
                                                        'most_clicked_products': most_clicked_products,
                                                        'currency': 'EUR',
                                                        'earnings': earnings,
                                                        'monthly_array': monthly_array})

    return HttpResponseNotFound()

def get_top_summary(current_user):
    pending_earnings = get_model('dashboard', 'UserEarning').objects\
            .filter(user=current_user, status=Sale.PENDING, paid=Sale.PAID_PENDING)\
            .aggregate(total=Sum('amount'))['total']

    confirmed_earnings = get_model('dashboard', 'UserEarning')\
            .objects.filter(user=current_user, status=Sale.CONFIRMED, paid=Sale.PAID_PENDING)\
            .aggregate(total=Sum('amount'))['total']

    pending_payment = 0
    payments = Payment.objects.filter(cancelled=False, paid=False, user=current_user).order_by('-created')
    if payments:
        pending_payment = payments[0].amount

    total_earned = 0
    payments = Payment.objects.filter(paid=True, user=current_user)
    default_currency = 'EUR'
    for pay in payments:
        rate = 1 if pay.currency == 'EUR' else currency_exchange(default_currency, pay.currency)
        total_earned += pay.amount * rate

    return pending_earnings, confirmed_earnings, pending_payment, total_earned

@cache_page(60 * 60 * 12)
def dashboard(request, year=None, month=None):
    """
    Display publisher data per month for logged in user.
    """
    if request.user.is_authenticated() and request.user.is_partner:
        if year is None and month is None:
            start_date = datetime.date.today().replace(day=1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        else:
            start_date = datetime.date(int(year), int(1), 1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)

            if month != "0":
                start_date = datetime.date(int(year), int(month), 1)

                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        year = start_date.year
        if month != "0":
            month = start_date.month

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))


        # Enumerate months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        years_choices = range(dt1.year, dt2.year+1)
        month_display = ""

        months_choices = [(0, _('All year'))]
        for i in range(1,13):
            months_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))
            if month == i:
                month_display = datetime.date(2008, i, 1).strftime('%B')

        # Total summary for user
        pending_earnings, confirmed_earnings, pending_payment, total_earned = get_top_summary(request.user)

        # Sales top products and top publishers
        sales, most_sold_products = get_sales(start_date_query, end_date_query, user_id=request.user.pk, limit=50)

        is_owner = get_user_model().objects.filter(owner_network=request.user).exists()

        top_publishers = None
        network_publishers = []
        if is_owner:
            top_publishers, network_publishers = get_publishers(start_date_query, end_date_query,
                                                                user_id=request.user.pk, limit=50)

        network_clicks = get_network_clicks(top_publishers)
        network_total_products = merge_top_products(most_sold_products, network_publishers, limit=50)

        # Most clicked products
        most_clicked_products = get_most_clicked_products(start_date_query, end_date_query, user_id=request.user.pk)

        # Sales count
        sales_count = 0
        referral_sales_count = 0
        tribute_sales_count = 0

        # Sales and commission per day
        data_per_day = {}
        for day in range(0, (end_date - start_date).days + 2):
            data_per_day[start_date+datetime.timedelta(day)] = [0, 0, 0, 0, 0, 0]

        # User Earnings
        user_earnings = get_model('dashboard', 'UserEarning').objects\
            .filter(user=request.user, date__range=(start_date_query, end_date_query), status__gte=Sale.PENDING)\
            .order_by('-date')
        for earning in user_earnings:
            day_start = datetime.datetime.combine(earning.date, datetime.time(0, 0, 0, 0))
            day_end = datetime.datetime.combine(earning.date, datetime.time(23, 59, 59, 999999))
            earning.clicks = get_clicks_from_sale(earning.sale)
            earning.extra_sale = None
            for sale in sales:
                if earning.sale.id == sale['id']:
                    earning.extra_sale = sale
            sale = get_model('dashboard', 'Sale').objects.get(id=earning.sale.id)
            earning.product_image = ''
            earning.product_link = ''
            earning.product_name = ''
            try:
                product = get_model('apparel', 'Product').objects.get(id=sale.product_id)
                product_image, product_link = get_product_thumbnail_and_link(product)
                earning.product_image = product_image
                earning.product_link = product_link
                earning.product_name = product.product_name
            except get_model('apparel', 'Product').DoesNotExist:
                pass

            if earning.from_user:
                earning.from_user_name = earning.from_user.slug
                earning.from_user_avatar = earning.from_user.avatar_small
                if earning.from_user.name:
                    earning.from_user_name = earning.from_user.name

            # Summarize per day
            if earning.user_earning_type == "publisher_sale_commission":
                data_per_day[earning.date.date()][0] += earning.amount
                sales_count += 1
            elif earning.user_earning_type == "referral_signup_commission" or \
                            earning.user_earning_type == "referral_sale_commission":
                data_per_day[earning.date.date()][2] += earning.amount
                referral_sales_count += 1
            elif earning.user_earning_type == "publisher_network_tribute":
                data_per_day[earning.date.date()][3] += earning.amount
                tribute_sales_count += 1
            elif earning.user_earning_type == "publisher_sale_click_commission" or earning.user_earning_type == "publisher_network_click_tribute":
                data_per_day[earning.date.date()][4] += earning.amount
                data_per_day[earning.date.date()][5] += get_clicks_from_sale(earning.sale)

        # Clicks per day
        clicks = get_model('statistics', 'ProductStat').objects\
            .filter(created__range=(start_date_query, end_date_query)).filter(user_id=request.user.pk)\
            .values_list('created', flat=True)
        for click in clicks:
            data_per_day[click.date()][1] += 1

        # Conversion rate
        conversion_rate = 0
        month_clicks = sum([x[1] for x in data_per_day.values()])
        if month_clicks > 0:
            conversion_rate = decimal.Decimal(sales_count) / decimal.Decimal(month_clicks)
            conversion_rate = str(conversion_rate.quantize(decimal.Decimal('0.0001')) * 100)

        # Enable sales listing after 2013-06-01 00:00:00
        is_after_june = False if (year <= 2013 and month <= 5) and not request.GET.get('override') else True

        # Summary earning
        ppc_clicks = sum([x[5] for x in data_per_day.values()])
        month_earnings = sum([x[0] for x in data_per_day.values()])
        network_earnings = sum([x[3] for x in data_per_day.values()])
        referral_earnings = sum([x[2] for x in data_per_day.values()])
        ppc_earnings = sum([x[4] for x in data_per_day.values()])

        if not is_owner:
            month_clicks -= ppc_clicks

        total_earnings = month_earnings + network_earnings + referral_earnings + ppc_earnings

        # Get aggregated data per day
        aggregated_per_day = get_model('dashboard', 'AggregatedData').objects.\
            filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                   type='aggregated_from_total').\
            values('date', 'sale_earnings', 'referral_earnings', 'click_earnings', 'total_clicks',
                   'network_sale_earnings')

        data_per_day = {}
        for day in range(0, (end_date - start_date).days + 2):
            data_per_day[start_date+datetime.timedelta(day)] = [0, 0, 0, 0, 0, 0]

        for row in aggregated_per_day:
            data_per_day[row['date'].date()][0] += row['sale_earnings']
            data_per_day[row['date'].date()][1] += row['referral_earnings']
            data_per_day[row['date'].date()][2] += row['click_earnings']
            data_per_day[row['date'].date()][3] += row['total_clicks']
            data_per_day[row['date'].date()][4] += row['network_sale_earnings']

        # Aggregated sum per month
        sum_data = get_model('dashboard', 'AggregatedData').objects.\
            filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                   type='aggregated_from_total').\
            aggregate(Sum('sale_earnings'), Sum('click_earnings'), Sum('referral_earnings'),
                      Sum('network_sale_earnings'), Sum('network_click_earnings'), Sum('sales'),
                      Sum('network_sales'), Sum('referral_sales'))

        total_aggregated_earnings = 0
        if sum_data['sale_earnings__sum'] is not None:
            total_aggregated_earnings = sum_data['sale_earnings__sum'] + sum_data['click_earnings__sum'] \
                                        + sum_data['referral_earnings__sum'] + \
                                        sum_data['network_sale_earnings__sum'] + \
                                        sum_data['network_click_earnings__sum']

        network_earning = 0
        if sum_data['network_sale_earnings__sum'] is not None:
            network_earning = sum_data['network_sale_earnings__sum'] + sum_data['network_click_earnings__sum']

        return render(request, 'dashboard/publisher.html', {#'data_per_day': data_per_day,
                                                            #'total_sales': sales_total,
                                                            'pending_earnings': pending_earnings, #aggregated_data['pending_earnings__sum'],
                                                            'confirmed_earnings': confirmed_earnings, #aggregated_data['confirmed_earnings__sum'],
                                                            'pending_payment': pending_payment, #aggregated_data['pending_payment__sum'],
                                                            'month_commission': sum_data['sale_earnings__sum'],
                                                            'month_clicks': month_clicks,
                                                            'month_sales': sum_data['sales__sum'], #month_sales,
                                                            'month_conversion_rate': conversion_rate,
                                                            'years_choices': years_choices,
                                                            'months_choices': months_choices,
                                                            'year': year,
                                                            'month': month,
                                                            'month_display': month_display,
                                                            'sales': sales,
                                                            'user_earnings': user_earnings,
                                                            'total_earned': total_earned,
                                                            'is_after_june': is_after_june,
                                                            'most_sold_products': network_total_products,
                                                            'top_publishers': top_publishers,
                                                            'most_clicked_products': most_clicked_products,
                                                            'referral_sales': sum_data['referral_sales__sum'], #referral_sales_count,
                                                            'network_sales': sum_data['network_sales__sum'], #tribute_sales_count,
                                                            'network_clicks': network_clicks,
                                                            'network_commission': network_earning, #network_earnings),
                                                            'referral_commission': sum_data['referral_earnings__sum'], #('%.2f' % referral_earnings),
                                                            'total_commission': ('%.2f' % total_aggregated_earnings), #total_earnings),
                                                            'currency': 'EUR',
                                                            'ppc_earnings': sum_data['click_earnings__sum'] ,#('%.2f' % ppc_earnings),
                                                            'ppc_clicks': ppc_clicks,
                                                            'is_owner': is_owner,
                                                            'data_per_day': data_per_day,
                                                            })
    return HttpResponseRedirect(reverse('index-publisher'))

def dashboard_info(request):
    return render(request, 'dashboard/info.html')

#
# Referral
#
def referral(request):
    if request.user.is_authenticated() and request.user.is_partner and request.user.referral_partner:
        referrals = get_user_model().objects.filter(referral_partner_parent=request.user, is_partner=True)
        return render(request, 'dashboard/referral.html', {'referrals': referrals})

    return HttpResponseRedirect(reverse('index-publisher'))

def referral_mail(request):
    emails = request.POST.get('emails')
    emails = re.split(r'[\s,]+', emails)

    referral_code = request.user.get_referral_domain_url()
    referral_name = request.user.display_name
    referral_email = request.user.email
    referral_language = get_language()

    template = 'dashboard/referral_mail_en.html'
    # TODO: fix when we have swedish email
    #if referral_language == 'sv':
        #template = 'dashboard/referral_mail_sv.html'

    body = render_to_string(template, {'referral_code': referral_code, 'referral_name': referral_name})

    for email in emails:
        send_email_task.delay('Invitation from %s' % (referral_name,), body, email, '%s <%s>' % (referral_name, referral_email))

    messages.add_message(request, messages.SUCCESS, 'Sent mail to %s' % (', '.join(emails),))

    return HttpResponseRedirect(reverse('dashboard-referral'))

def referral_signup(request, code):
    user_id = None
    try:
        user = get_user_model().objects.get(referral_partner_code=code)
        user_id = user.pk
    except:
        pass
    response = redirect(reverse('publisher-contact'))
    if user_id:
        expires_datetime = timezone.now() + datetime.timedelta(days=15)
        response.set_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, user_id, expires=expires_datetime,
                                   httponly=True)

    return response

#
# Commissions
#
def commissions(request):
    if not request.user.is_authenticated() or not request.user.is_partner:
        log.error('Unauthorized user trying to access store commission page. Returning 404.')
        raise Http404

    if not request.user.partner_group:
        log.error('User %s is partner but has no partner group. Disallowing viewing of store commissions page.'
                  % request.user)
        raise Http404

    cookie_value = request.COOKIES.get(settings.APPAREL_LOCATION_COOKIE, None) or request.session.get('location','ALL')
    vendors = get_available_stores(cookie_value)
    user_id = request.user.id
    stores = {}
    for vendor in vendors:
        try:
            temp = {}
            vendor_obj = get_model('apparel', 'Vendor').objects.get(name=vendor)
            store = get_model('dashboard', 'StoreCommission').objects.get(vendor=vendor_obj)
            store.calculated_commissions(store.commission, *get_cuts_for_user_and_vendor(user_id, store.vendor))
            temp['vendor_pk'] = vendor_obj.pk
            temp['vendor_name'] = vendor_obj.name
            temp['link'] = store.link
            temp['store_pk'] = store.pk
            if vendor_obj.is_cpc:
                _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(user_id, vendor_obj)
                click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=vendor_obj)
                temp['amount'] = "%.2f" % (click_cost.locale_price * publisher_cut * normal_cut)
                temp['currency'] = click_cost.locale_currency
                temp['type'] = "is_cpc"
            elif vendor_obj.is_cpo:
                temp['amount'] = store.commission
                temp['type'] = "is_cpo"
            stores[vendor] = temp
        except get_model('dashboard', 'ClickCost').DoesNotExist:
            log.warning("ClickCost for vendor %s does not exist" % vendor)
        except get_model('dashboard', 'StoreCommission').DoesNotExist:
            log.warning("StoreCommission for vendor %s does not exist" % vendor)
    stores = [x for x in sorted(stores.values(), key=lambda x: x['vendor_name'])]
    return render(request, 'dashboard/commissions.html', {'stores': stores})

def commissions_popup(request, pk):
    if not request.user.is_authenticated() or not request.user.is_partner:
        raise Http404

    store = get_object_or_404(get_model('dashboard', 'StoreCommission'), pk=pk)
    link = None
    if store.link:
        link = '{}{}/'.format(store.link, request.user.pk)

    return render(request, 'dashboard/commissions_popup.html', {'link': link, 'name': store.vendor.name})

#
# Publisher / Store signup
#
def index_complete(request, view):
    analytics_identifier = 'Publisher'
    if view == 'store':
        analytics_identifier = 'Store'

    return render(request, 'dashboard/publisher_complete.html', {'analytics_identifier': analytics_identifier})

def retailer(request):
    return render(request, 'apparel/retailers.html')

def retailer_form(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, is_store_form=True)
        if form.is_valid():
            # Save name and blog URL on session, for Google Analytics
            request.session['index_complete_info'] = u"%s %s" % (form.cleaned_data['name'], form.cleaned_data['blog'])
            instance = form.save(commit=False)
            instance.store = True
            instance.save()

            mail_managers_task.delay('New store signup: %s' % (form.cleaned_data['name'],),
                    'Name: %s\nEmail: %s\nURL: %s' % (form.cleaned_data['name'],
                                                      form.cleaned_data['email'],
                                                      form.cleaned_data['blog']))

            return HttpResponseRedirect(reverse('index-store-complete'))
    else:
        form = SignupForm(is_store_form=True)

    return render(request, 'apparel/retailer_contact.html', {'form': form})

def index(request):
    return render(request, 'dashboard/index.html')

def publisher_contact(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Save name and blog URL on session, for Google Analytics
            request.session['index_complete_info'] = u"%s %s" % (form.cleaned_data['name'], form.cleaned_data['blog'])
            instance = form.save(commit=False)
            instance.referral_user = get_referral_user_from_cookie(request)
            instance.save()

            if instance.referral_user:
                site_object = Site.objects.get_current()
                referral_user_url = 'http://%s%s' % (site_object.domain, instance.referral_user.get_absolute_url())

                mail_managers_task.delay('New publisher signup by referral: %s' % (form.cleaned_data['name'],),
                        'Name: %s\nEmail: %s\nBlog: %s\nReferral User: %s - %s\n' % (form.cleaned_data['name'],
                                                           form.cleaned_data['email'],
                                                           form.cleaned_data['blog'],
                                                           instance.referral_user.display_name,
                                                           referral_user_url))
            else:
                mail_managers_task.delay('New publisher signup: %s' % (form.cleaned_data['name'],),
                        'Name: %s\nEmail: %s\nBlog: %s' % (form.cleaned_data['name'],
                                                           form.cleaned_data['email'],
                                                           form.cleaned_data['blog']))

            return HttpResponseRedirect(reverse('index-dashboard-complete'))
    else:
        form = SignupForm()

    referral_user = get_referral_user_from_cookie(request)

    return render(request, 'dashboard/publisher_contact.html', {'form': form, 'referral_user': referral_user})

def publisher_tools(request):
    return render(request, 'dashboard/publisher_tools.html')

def products(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.is_partner:
        if year is None and month is None:
            start_date = datetime.date.today().replace(day=1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        else:
            start_date = datetime.date(int(year), int(1), 1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)

            if month != "0":
                start_date = datetime.date(int(year), int(month), 1)

                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        year = start_date.year
        if month != "0":
            month = start_date.month

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))


        # Enumerate months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        years_choices = range(dt1.year, dt2.year+1)

        months_choices = [(0, _('All year'))]
        for i in range(1,13):
            months_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))

        # Total sales counts
        sales_total = decimal.Decimal('0')
        sales_pending = get_model('dashboard', 'UserEarning').objects\
            .filter(user=request.user, status=Sale.PENDING, paid=Sale.PAID_PENDING).aggregate(total=Sum('amount'))['total']
        if sales_pending:
            sales_total += sales_pending
        else:
            sales_pending = decimal.Decimal('0')
        sales_confirmed = get_model('dashboard', 'UserEarning').objects\
            .filter(user=request.user, status=Sale.CONFIRMED, paid=Sale.PAID_PENDING).aggregate(total=Sum('amount'))['total']
        if sales_confirmed:
            sales_total += sales_confirmed
        else:
            sales_confirmed = decimal.Decimal('0')

        # Pending payment
        pending_payment = 0
        payments = Payment.objects.filter(cancelled=False, paid=False, user=request.user).order_by('-created')
        if payments:
            pending_payment = payments[0].amount

        total_earned = 0
        payments = Payment.objects.filter(paid=True, user=request.user)
        for pay in payments:
            total_earned += pay.amount

        # Sales and most sold products
        sales, most_sold_products = get_sales(start_date_query, end_date_query, user_id=request.user.pk, limit=None)

        top_publishers = None
        network_publishers = []

        is_owner = get_user_model().objects.filter(owner_network=request.user).exists()
        if is_owner:
            top_publishers, network_publishers = get_publishers(start_date_query, end_date_query, user_id=request.user.pk, limit=None)

        network_total_products = merge_top_products(most_sold_products, network_publishers, limit=None)

        # Sales count
        sales_count = 0
        referral_sales_count = 0
        tribute_sales_count = 0

        # Sales and commission per day
        data_per_day = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_day[start_date+datetime.timedelta(day)] = [0, 0, 0, 0]


        # Clicks per day
        clicks = get_model('statistics', 'ProductStat').objects.filter(created__range=(start_date_query, end_date_query)) \
                                                               .filter(user_id=request.user.pk) \
                                                               .values_list('created', flat=True)
        for click in clicks:
            data_per_day[click.date()][1] += 1

        # Conversion rate
        conversion_rate = 0
        month_clicks = sum([x[1] for x in data_per_day.values()])
        if month_clicks > 0:
            conversion_rate = decimal.Decimal(sales_count) / decimal.Decimal(month_clicks)
            conversion_rate = str(conversion_rate.quantize(decimal.Decimal('0.0001')) * 100)

        # Enable sales listing after 2013-06-01 00:00:00
        is_after_june = False if (year <= 2013 and month <= 5) and not request.GET.get('override') else True

        return render(request, 'dashboard/products.html', {'data_per_day': data_per_day,
                                                            'total_sales': sales_total,
                                                            'sales_pending': sales_pending,
                                                            'total_confirmed': sales_confirmed,
                                                            'pending_payment': pending_payment,
                                                            'month_commission': ('%.2f' % sum([x[0] for x in data_per_day.values()])),
                                                            'month_clicks': month_clicks,
                                                            'month_sales': sales_count,
                                                            'month_conversion_rate': conversion_rate,
                                                            'years_choices': years_choices,
                                                            'months_choices': months_choices,
                                                            'year': year,
                                                            'month': month,
                                                            'sales': sales,
                                                            'total_earned': total_earned,
                                                            'is_after_june': is_after_june,
                                                            'most_sold_products': network_total_products,
                                                            'referral_sales': referral_sales_count,
                                                            'network_sales': tribute_sales_count,
                                                            'network_commission': ('%.2f' % sum([x[3] for x in data_per_day.values()])),
                                                            'referral_commission': ('%.2f' % sum([x[2] for x in data_per_day.values()])),
                                                            'currency': 'EUR'})
    return HttpResponseRedirect(reverse('index-publisher'))

def publishers(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.is_partner:
        if year is None and month is None:
            start_date = datetime.date.today().replace(day=1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        else:
            start_date = datetime.date(int(year), int(1), 1)
            end_date = start_date
            end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)

            if month != "0":
                start_date = datetime.date(int(year), int(month), 1)

                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        year = start_date.year
        if month != "0":
            month = start_date.month

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))


        # Enumerate months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        years_choices = range(dt1.year, dt2.year+1)

        months_choices = [(0, _('All year'))]
        for i in range(1,13):
            months_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))

        # Total sales counts
        sales_total = decimal.Decimal('0')
        sales_pending = get_model('dashboard', 'UserEarning').objects.filter(user=request.user, status=Sale.PENDING, paid=Sale.PAID_PENDING).aggregate(total=Sum('amount'))['total']
        if sales_pending:
            sales_total += sales_pending
        else:
            sales_pending = decimal.Decimal('0')
        sales_confirmed = get_model('dashboard', 'UserEarning').objects.filter(user=request.user, status=Sale.CONFIRMED, paid=Sale.PAID_PENDING).aggregate(total=Sum('amount'))['total']
        if sales_confirmed:
            sales_total += sales_confirmed
        else:
            sales_confirmed = decimal.Decimal('0')

        # Pending payment
        pending_payment = 0
        payments = Payment.objects.filter(cancelled=False, paid=False, user=request.user).order_by('-created')
        if payments:
            pending_payment = payments[0].amount

        total_earned = 0
        payments = Payment.objects.filter(paid=True, user=request.user)
        for pay in payments:
            total_earned += pay.amount

        # Sales and most sold products
        sales, most_sold_products = get_sales(start_date_query, end_date_query, user_id=request.user.pk, limit=None)

        top_publishers = None

        is_owner = get_user_model().objects.filter(owner_network=request.user).exists()
        if is_owner:
            top_publishers, net_product = get_publishers(start_date_query, end_date_query, user_id=request.user.pk, limit=None)


        # Sales count
        sales_count = 0
        referral_sales_count = 0
        tribute_sales_count = 0

        # Sales and commission per day
        data_per_day = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_day[start_date+datetime.timedelta(day)] = [0, 0, 0, 0]


        # Clicks per day
        clicks = get_model('statistics', 'ProductStat').objects.filter(created__range=(start_date_query, end_date_query)) \
                                                               .filter(user_id=request.user.pk) \
                                                               .values_list('created', flat=True)
        for click in clicks:
            data_per_day[click.date()][1] += 1

        # Conversion rate
        conversion_rate = 0
        month_clicks = sum([x[1] for x in data_per_day.values()])
        if month_clicks > 0:
            conversion_rate = decimal.Decimal(sales_count) / decimal.Decimal(month_clicks)
            conversion_rate = str(conversion_rate.quantize(decimal.Decimal('0.0001')) * 100)

        # Enable sales listing after 2013-06-01 00:00:00
        is_after_june = False if (year <= 2013 and month <= 5) and not request.GET.get('override') else True

        return render(request, 'dashboard/publishers_network.html', {'data_per_day': data_per_day,
                                                            'total_sales': sales_total,
                                                            'sales_pending': sales_pending,
                                                            'total_confirmed': sales_confirmed,
                                                            'pending_payment': pending_payment,
                                                            'month_commission': ('%.2f' % sum([x[0] for x in data_per_day.values()])),
                                                            'month_clicks': month_clicks,
                                                            'month_sales': sales_count,
                                                            'month_conversion_rate': conversion_rate,
                                                            'years_choices': years_choices,
                                                            'months_choices': months_choices,
                                                            'year': year,
                                                            'month': month,
                                                            'sales': sales,
                                                            'is_owner': is_owner,
                                                            'total_earned': total_earned,
                                                            'is_after_june': is_after_june,
                                                            'top_publishers': top_publishers,
                                                            'referral_sales': referral_sales_count,
                                                            'network_sales': tribute_sales_count,
                                                            'network_commission': ('%.2f' % sum([x[3] for x in data_per_day.values()])),
                                                            'referral_commission': ('%.2f' % sum([x[2] for x in data_per_day.values()])),
                                                            'currency': 'EUR'})
    return HttpResponseRedirect(reverse('index-publisher'))

def get_clicks_from_sale(sale):
    """
        Returns number of clicks generated from the given sale
    """
    user_id = sale.user_id
    start_date_query = datetime.datetime.combine(sale.sale_date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(sale.sale_date, datetime.time(23, 59, 59, 999999))
    vendor_name = sale.vendor
    clicks = get_model('statistics', 'ProductStat').objects.filter(vendor=vendor_name, user_id=user_id,
                                                          created__range=[start_date_query, end_date_query]).count()
    return clicks

def clicks_detail(request):
    """
        Returns a list of click details given an user, vendor and date
    """
    if request.method == 'POST' and request.is_ajax():
        user_id = request.POST.get('user_id', None)
        vendor = request.POST.get('vendor', None)
        currency = request.POST.get('currency', 'EUR')
        num_clicks = request.POST.get('clicks', 0)
        amount_for_clicks = request.POST.get('amount', 0).replace(',', '.')
        if num_clicks > 0:
            click_cost = decimal.Decimal(amount_for_clicks)/int(num_clicks)
            query_date = datetime.datetime.fromtimestamp(int(request.POST['date']))
            data = get_clicks_list(vendor, query_date, currency, click_cost, user_id)
            json_data = json.dumps(data)
            return HttpResponse(json_data)

class DashboardView(TemplateView):
    template_name = "dashboard/new_dashboard.html"


    def get(self, request, *args, **kwargs):
        month = None if not 'month' in self.kwargs else self.kwargs['month']
        year =  None if not 'year' in self.kwargs else self.kwargs['year']

        currency = 'EUR'
        AggregatedData = get_model('dashboard', 'AggregatedData')



        if request.user.is_authenticated() and request.user.is_partner:
            if year is None and month is None:
                start_date = datetime.date.today().replace(day=1)
                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
            else:
                start_date = datetime.date(int(year), int(1), 1)
                end_date = start_date
                end_date = end_date.replace(day=calendar.monthrange(start_date.year, 12)[1], month=12)

                if month != "0":
                    start_date = datetime.date(int(year), int(month), 1)

                    end_date = start_date
                    end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

            year = start_date.year
            if month != "0":
                month = start_date.month

            start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
            end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

            # Enumerate months
            dt1 = request.user.date_joined.date()
            dt2 = datetime.date.today()
            years_choices = range(dt1.year, dt2.year+1)
            month_display = ""

            months_choices = [(0, _('All year'))]
            for i in range(1,13):
                months_choices.append((i, datetime.date(2008, i, 1).strftime('%B')))
                if month == i:
                    month_display = datetime.date(2008, i, 1).strftime('%B')

             # Determine if the user is the owner of a publisher network
            is_owner = get_user_model().objects.filter(owner_network=request.user).exists()
            # Enable sales listing after 2013-06-01 00:00:00
            is_after_june = False if (year <= 2013 and month <= 5) and not request.GET.get('override') else True

            products = AggregatedData.objects.all()


            # Total summary for user
            pending_earnings, confirmed_earnings, pending_payment, total_earned = get_top_summary(request.user)



            # Get aggregated data per day
            aggregated_per_day = AggregatedData.objects.\
                filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                       type='aggregated_from_total').\
                values('date', 'sale_earnings', 'referral_earnings', 'click_earnings', 'total_clicks',
                       'network_sale_earnings')


            data_per_day = {}
            for day in range(0, (end_date - start_date).days + 2):
                data_per_day[start_date+datetime.timedelta(day)] = [0, 0, 0, 0, 0, 0]

            for row in aggregated_per_day:
                data_per_day[row['date'].date()][0] += row['sale_earnings']
                data_per_day[row['date'].date()][1] += row['referral_earnings']
                data_per_day[row['date'].date()][2] += row['click_earnings']
                data_per_day[row['date'].date()][3] += row['total_clicks']
                data_per_day[row['date'].date()][4] += row['network_sale_earnings']

            # Summary earning
            ppc_clicks = sum([x[5] for x in data_per_day.values()])
            month_earnings = sum([x[0] for x in data_per_day.values()])
            network_earnings = sum([x[3] for x in data_per_day.values()])
            referral_earnings = sum([x[2] for x in data_per_day.values()])
            ppc_earnings = sum([x[4] for x in data_per_day.values()])

            #if not is_owner:
            #    month_clicks -= ppc_clicks

            total_earnings = month_earnings + network_earnings + referral_earnings + ppc_earnings

            # Aggregated sum per month
            sum_data = AggregatedData.objects.\
                filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                       type='aggregated_from_total').\
                aggregate(Sum('sale_earnings'), Sum('click_earnings'), Sum('referral_earnings'),
                          Sum('network_sale_earnings'), Sum('network_click_earnings'), Sum('sales'),
                          Sum('network_sales'), Sum('referral_sales'))

            total_aggregated_earnings = 0
            if sum_data['sale_earnings__sum'] is not None:
                total_aggregated_earnings = sum_data['sale_earnings__sum'] + sum_data['click_earnings__sum'] \
                                            + sum_data['referral_earnings__sum'] + \
                                            sum_data['network_sale_earnings__sum'] + \
                                            sum_data['network_click_earnings__sum']

            # Aggregate publishers per month
            top_publishers = AggregatedData.objects.\
                filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                       type='aggregated_from_publisher').\
                values('aggregated_from_id', 'aggregated_from_name', 'aggregated_from_slug', 'aggregated_from_image',
                       'aggregated_from_link').\
                annotate(sale_earnings=Sum('sale_earnings'), click_earnings=Sum('click_earnings'),
                         network_sale_earnings=Sum('network_sale_earnings'),
                         network_click_earnings=Sum('network_click_earnings'), sales=Sum('sales'),
                         total_earnings=Sum('sale_plus_click_earnings'),
                         total_network_earnings=Sum('total_network_earnings'),
                         total_clicks=Sum('total_clicks')).order_by('-total_network_earnings', '-sale_plus_click_earnings')

            # Aggregate products per month
            top_products = AggregatedData.objects.\
                filter(user_id=request.user.id, date__range=(start_date_query, end_date_query),
                       type='aggregated_from_product').\
                values('aggregated_from_id', 'aggregated_from_name', 'aggregated_from_slug', 'aggregated_from_image',
                       'aggregated_from_link').\
                annotate(total_earnings=Sum('sale_plus_click_earnings'),
                         total_network_earnings=Sum('total_network_earnings'),
                         total_clicks=Sum('total_clicks')).order_by('-total_network_earnings', '-sale_plus_click_earnings')

            network_earning = 0
            if sum_data['network_sale_earnings__sum'] is not None:
                network_earning = sum_data['network_sale_earnings__sum'] + sum_data['network_click_earnings__sum']

            context_data = {'pending_earnings': pending_earnings, 'confirmed_earnings': confirmed_earnings,
                            'pending_payment': pending_payment, 'total_earned': total_earned,
                            'years_choices': years_choices, 'months_choices': months_choices,
                            'data_per_day': data_per_day, 'currency': currency,
                            'month_commission': sum_data['sale_earnings__sum'], #'month_clicks': month_clicks,
                            'month_sales': sum_data['sales__sum'], 'total_earnings': total_earnings, 'year': year,
                            'month': month, 'month_display': month_display,
                            'total_commission': ('%.2f' % total_aggregated_earnings),
                            'is_owner': is_owner, 'is_after_june': is_after_june,
                            'network_commission': network_earning,
                            'top_publishers': top_publishers,
                            'top_products': top_products,
                            }
            return render(request, 'dashboard/new_dashboard.html', context_data)
        return HttpResponseRedirect(reverse('new-dashboard'))