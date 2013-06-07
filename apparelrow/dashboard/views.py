import datetime
import calendar
import decimal

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.db.models import get_model, Sum, Count
from django.forms import ModelForm
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.fields import ImageField

from apparelrow.dashboard.models import Sale, Payment, Signup


def map_placement(placement):
    link = _('Your profile on Apprl.com')
    if placement == 'Ext-Shop':
        link = _('Shop on your site')
    elif placement == 'Ext-Look':
        link = _('Look on your site')
    elif placement == 'Ext-Link':
        link = _('Product link on your site')
    elif placement == 'Look':
        link = _('Look on Apprl.com')
    elif placement == 'Shop':
        link = _('Shop on Apprl.com')
    elif placement == 'Feed':
        link = _('Feed on Apprl.com')

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
        most_clicked_products.append({
            'product_image': product_image,
            'product_link': reverse('product-detail', args=[product.slug]),
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
            SELECT ds.id, ds.sale_date, ds.commission, ds.currency, ds.placement, ds.converted_commission, ds.user_id,
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
            ORDER BY ds.sale_date DESC
        """.format(user_criteria), values)
    sales = []
    most_sold = {}
    for sale in sale_table:
        product_image = ''
        if sale.product_image:
            product_image = get_thumbnail(ImageField().to_python(sale.product_image), '50', crop='noop').url

        temp = {
            'link': map_placement(sale.placement),
            'commission': sale.commission,
            'partner_commission': sale.converted_commission - sale.commission,
            'currency': sale.currency,
            'sale_date': sale.sale_date,
            'product_image': product_image,
            'product_link': reverse('product-detail', args=[sale.slug]),
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

    class Meta:
        model = Signup
        fields = ('name', 'email', 'blog')


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
                             .filter(sale_date__range=(start_date_query, end_date_query)) \
                             .order_by('sale_date') \
                             .values('sale_date', 'converted_commission', 'commission', 'user_id')
        for sale in result:
            data_per_month[sale['sale_date'].date()][0] += sale['converted_commission']
            if sale['user_id']:
                data_per_month[sale['sale_date'].date()][1] += sale['commission']
                partner_commission += sale['commission']
            month_commission += sale['converted_commission']

        apprl_commission = month_commission - partner_commission

        # Clicks per month
        clicks = get_model('statistics', 'ProductStat').objects.filter(created__range=(start_date_query, end_date_query)) \
                                                               .order_by('created')
        for click in clicks:
            data_per_month[click.created.date()][2] += 1
            if click.user_id:
                data_per_month[click.created.date()][3] += 1

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
                                                        'most_clicked_products': most_clicked_products})

    return HttpResponseNotFound()


def dashboard(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.is_partner:
        if year is not None and month is not None:
            start_date = datetime.date(int(year), int(month), 1)
        else:
            start_date = datetime.date.today().replace(day=1)

        year = start_date.year
        month = start_date.month

        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        # Commission per month
        data_per_day = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_day[start_date.replace(day=day)] = [0, 0]

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

        for sale in Sale.objects.filter(status__range=(Sale.PENDING, Sale.CONFIRMED)) \
                                .filter(sale_date__range=(start_date_query, end_date_query)) \
                                .filter(user_id=request.user.pk) \
                                .order_by('sale_date') \
                                .values('sale_date', 'commission'):
            data_per_day[sale['sale_date'].date()][0] += sale['commission']

        # Clicks
        clicks = get_model('statistics', 'ProductStat').objects.filter(created__range=(start_date_query, end_date_query)) \
                                                               .filter(user_id=request.user.pk) \
                                                               .order_by('created')
        for click in clicks:
            data_per_day[click.created.date()][1] += 1

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

        # Conversion rate
        conversion_rate = 0
        month_clicks = sum([x[1] for x in data_per_day.values()])
        month_sales = len(sales)
        if month_clicks > 0:
            conversion_rate = decimal.Decimal(month_sales) / decimal.Decimal(month_clicks)
            conversion_rate = str(conversion_rate.quantize(decimal.Decimal('0.0001')) * 100)

        # Enable sales listing after 2013-06-01 00:00:00
        is_after_june = True if (year >= 2013 and month >= 6) or request.GET.get('override') else False

        return render(request, 'dashboard/partner.html', {'data_per_day': data_per_day,
                                                          'total_sales': sales_total,
                                                          'total_confirmed': sales_confirmed,
                                                          'pending_payment': pending_payment,
                                                          'month_commission': sum([x[0] for x in data_per_day.values()]),
                                                          'month_clicks': month_clicks,
                                                          'month_sales': month_sales,
                                                          'month_conversion_rate': conversion_rate,
                                                          'dates': dates,
                                                          'year': year,
                                                          'month': month,
                                                          'sales': sales,
                                                          'is_after_june': is_after_june,
                                                          'most_sold_products': most_sold_products,
                                                          'most_clicked_products': most_clicked_products})

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Save name and blog URL on session, for Google Analytics
            request.session['partner_info'] = u"%s %s" % (form.cleaned_data['name'], form.cleaned_data['blog'])
            form.save()

        return HttpResponseRedirect(reverse('dashboard-complete'))

    form = SignupForm()

    return render(request, 'dashboard/partner_signup.html', {'form': form})


def dashboard_complete(request):
    return render(request, 'dashboard/partner_complete.html')


def dashboard_info(request):
    if request.user.is_authenticated():
        return render(request, 'dashboard/info.html')

    return render(request, 'dashboard/info_unauthenticated.html')

def dashboard_more_info(request):
    return render(request, 'dashboard/more_info.html')
