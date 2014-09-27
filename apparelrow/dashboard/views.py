import datetime
import calendar
import decimal
import re

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseNotFound, Http404
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
from apparelrow.dashboard.utils import get_referral_user_from_cookie, get_cuts_for_user_and_vendor
from apparelrow.profile.tasks import mail_managers_task

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
        product_image = ''
        if product.product_image:
            product_image = get_thumbnail(ImageField().to_python(product.product_image), '50', crop='noop').url

        product_link = None
        if product.slug:
            product_link = reverse('product-detail', args=[product.slug])

        most_clicked_products.append({
            'product_image': product_image,
            'product_link': product_link,
            'product': '%s %s' % (product.brand_name, product.product_name) if product.product_name else _('Unknown'),
            'clicks': product.clicks
        })

    return most_clicked_products


def get_sales(start_date, end_date, user_id=None, limit=5):
    user_criteria = ''
    values = [start_date, end_date, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]
    if user_id:
        user_criteria = 'ds.user_id = %s AND'
        values = [start_date, end_date, user_id, Sale.PENDING, Sale.CONFIRMED, start_date, end_date]

    sale_table = Sale.objects.raw("""
            SELECT ds.id, ds.created, ds.commission, ds.currency, ds.placement, ds.converted_commission, ds.user_id,
                   ds.is_referral_sale, ds.referral_user_id, ds.is_promo,
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
                ds.created BETWEEN %s AND %s
            GROUP BY ds.id, ap.product_name, ap.product_image, ap.slug, ab.name, pu.name
            ORDER BY ds.created DESC
        """.format(user_criteria), values)
    sales = []
    most_sold = {}
    for sale in sale_table:
        product_image = ''
        if sale.product_image:
            product_image = get_thumbnail(ImageField().to_python(sale.product_image), '50', crop='noop').url

        product_link = None
        if sale.slug:
            product_link = reverse('product-detail', args=[sale.slug])

        apprl_commission = sale.converted_commission if sale.user_id == 0 else sale.converted_commission - sale.commission
        referral_user = None
        if sale.is_referral_sale:
            try:
                referral_user = get_user_model().objects.get(pk=sale.referral_user_id)
            except get_user_model().DoesNotExist:
                pass

            apprl_commission = decimal.Decimal('0')

        temp = {
            'is_promo': sale.is_promo,
            'is_referral_sale': sale.is_referral_sale,
            'referral_user': referral_user,
            'link': map_placement(sale.placement),
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
        }

        if sale.product_name:
            if temp['product'] in most_sold:
                most_sold[temp['product']]['sales'] += 1
            else:
                temp['sales'] = 1
                most_sold[temp['product']] = temp

        sales.append(temp)

    most_sold_products = [x for x in sorted(most_sold.values(), key=lambda x: x['sales'], reverse=True)[:limit] if x['sales'] > 0]

    return sales, most_sold_products


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
        fields = ('name', 'email', 'blog')


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
            sales_pending = Sale.objects.filter(user_id=user.pk, status=Sale.PENDING, paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
            if sales_pending:
                sales_total += sales_pending
            else:
                sales_pending = decimal.Decimal('0')
            sales_confirmed = Sale.objects.filter(user_id=user.pk, status=Sale.CONFIRMED, paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
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


def dashboard_admin(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.is_superuser:
        if year is not None and month is not None:
            start_date = datetime.date(int(year), int(month), 1)
        else:
            start_date = datetime.date.today().replace(day=1)

        year = start_date.year
        month = start_date.month

        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        # Per month
        data_per_month = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_month[start_date.replace(day=day)] = [0, 0, 0, 0]

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        # Commission per month
        month_commission = decimal.Decimal('0.0')
        partner_commission = decimal.Decimal('0.0')
        result = Sale.objects.filter(status__range=(Sale.PENDING, Sale.CONFIRMED)) \
                             .filter(created__range=(start_date_query, end_date_query)) \
                             .order_by('created') \
                             .values('created', 'converted_commission', 'commission', 'user_id')
        for sale in result:
            data_per_month[sale['created'].date()][0] += sale['converted_commission']
            if sale['user_id']:
                data_per_month[sale['created'].date()][1] += sale['commission']
                partner_commission += sale['commission']
            month_commission += sale['converted_commission']

        apprl_commission = month_commission - partner_commission

        # Clicks per month
        clicks = get_model('statistics', 'ProductStat').objects.filter(created__range=(start_date_query, end_date_query)) \
                                                               .values('created', 'user_id')
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

        sales_count = result.count()
        conversion_rate = 0
        if click_total > 0:
            conversion_rate = decimal.Decimal(sales_count) / decimal.Decimal(click_total)
            conversion_rate = str(conversion_rate.quantize(decimal.Decimal('0.0001')) * 100)

        # Sales and most sold products
        sales, most_sold_products = get_sales(start_date_query, end_date_query)

        # Most clicked products
        most_clicked_products = get_most_clicked_products(start_date_query, end_date_query)

        return render(request, 'dashboard/admin.html', {'sales': data_per_month,
                                                        'sales_count': sales_count,
                                                        'month_commission': month_commission,
                                                        'partner': partner_commission,
                                                        'apprl': apprl_commission,
                                                        'click_total': click_total,
                                                        'click_partner': click_partner,
                                                        'click_apprl': click_apprl,
                                                        'dates': dates,
                                                        'year': year,
                                                        'month': month,
                                                        'conversion_rate': conversion_rate,
                                                        'sales_table': sales,
                                                        'most_sold_products': most_sold_products,
                                                        'most_clicked_products': most_clicked_products,
                                                        'currency': 'EUR'})

    return HttpResponseNotFound()


def dashboard(request, year=None, month=None):
    """
    Display publisher data per month for logged in user.
    """
    if request.user.is_authenticated() and request.user.is_partner:
        if year is not None and month is not None:
            start_date = datetime.date(int(year), int(month), 1)
        else:
            start_date = datetime.date.today().replace(day=1)

        year = start_date.year
        month = start_date.month

        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        # Enumerate months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        start_month = dt1.month
        end_months = (dt2.year - dt1.year) * 12 + dt2.month + 1
        dates = [datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
            ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
        )]

        # Total sales counts
        sales_total = decimal.Decimal('0')
        sales_pending = Sale.objects.filter(user_id=request.user.pk, status=Sale.PENDING, paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
        if sales_pending:
            sales_total += sales_pending
        else:
            sales_pending = decimal.Decimal('0')
        sales_confirmed = Sale.objects.filter(user_id=request.user.pk, status=Sale.CONFIRMED, paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
        if sales_confirmed:
            sales_total += sales_confirmed
        else:
            sales_confirmed = decimal.Decimal('0')

        # Pending payment
        pending_payment = 0
        payments = Payment.objects.filter(cancelled=False, paid=False, user=request.user).order_by('-created')
        if payments:
            pending_payment = payments[0].amount

        # Sales and most sold products
        sales, most_sold_products = get_sales(start_date_query, end_date_query, user_id=request.user.pk)

        # Most clicked products
        most_clicked_products = get_most_clicked_products(start_date_query, end_date_query, user_id=request.user.pk)

        # Sales count
        sales_count = 0
        referral_sales_count = 0

        # Sales and commission per day
        data_per_day = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_day[start_date.replace(day=day)] = [0, 0, 0]

        for sale in sales:
            if sale['is_referral_sale']:
                data_per_day[sale['created'].date()][2] += sale['commission']
                referral_sales_count += 1
            else:
                data_per_day[sale['created'].date()][0] += sale['commission']
                sales_count += 1

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

        return render(request, 'dashboard/publisher.html', {'data_per_day': data_per_day,
                                                            'total_sales': sales_total,
                                                            'total_confirmed': sales_confirmed,
                                                            'pending_payment': pending_payment,
                                                            'month_commission': sum([x[0] for x in data_per_day.values()]),
                                                            'month_clicks': month_clicks,
                                                            'month_sales': sales_count,
                                                            'month_conversion_rate': conversion_rate,
                                                            'dates': dates,
                                                            'year': year,
                                                            'month': month,
                                                            'sales': sales,
                                                            'is_after_june': is_after_june,
                                                            'most_sold_products': most_sold_products,
                                                            'most_clicked_products': most_clicked_products,
                                                            'referral_sales': referral_sales_count,
                                                            'referral_commission': sum([x[2] for x in data_per_day.values()]),
                                                            'currency': 'EUR'})


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

    response = redirect(reverse('index-publisher'))
    if user_id:
        expires_datetime = timezone.now() + datetime.timedelta(days=15)
        response.set_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, user_id, expires=expires_datetime, httponly=True)

    return response


#
# Commissions
#

def commissions(request):
    if not request.user.is_authenticated() or not request.user.is_partner:
        log.error('Unauthorized user trying to access store commission page. Returning 404.')
        raise Http404

    if not request.user.partner_group:
        log.error('User %s is partner but has no partner group. Disallowing viewing of store commissions page.' % request.user)
        raise Http404

    stores = list(get_model('dashboard', 'StoreCommission').objects.select_related('vendor').order_by('vendor__name'))
    user_id = request.user.id
    stores = [store.calculated_commissions(store.commission,*get_cuts_for_user_and_vendor(user_id,store.vendor)) for store in stores]
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


def store(request):
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

    return render(request, 'apparel/store.html', {'form': form})

def index(request):
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

    return render(request, 'dashboard/index.html', {'form': form, 'referral_user': referral_user})
