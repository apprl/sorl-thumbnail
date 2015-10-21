import datetime
import decimal
import calendar
import uuid
import logging
import operator

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import get_model, Sum, Count
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.template.loader import render_to_string

import dateutil.parser

from apparelrow.statistics.utils import get_client_ip
from apparelrow.apparel.utils import exchange_amount
from apparelrow.dashboard.utils import get_clicks_amount, get_total_clicks_per_vendor, get_number_clicks

from advertiser.tasks import send_text_email_task
from advertiser.utils import make_advertiser_url


logger = logging.getLogger('advertiser')


def get_cookie_name(store_id):
    return 'aanclick%s' % (store_id,)


def mail_superusers(subject, body):
    for user in get_user_model().objects.filter(is_superuser=True, email__isnull=False):
        if user.email:
            send_text_email_task.delay(subject, body, [user.email])


def pixel(request):
    """
    Advertiser pixel
    """
    store_id = request.GET.get('store_id')
    order_id = request.GET.get('order_id')
    order_value = request.GET.get('order_value')
    currency = request.GET.get('currency')

    if not store_id or not order_id or not order_value or not currency:
        email_body = render_to_string('advertiser/email_default_error.txt', locals())
        logger.warn('Advertiser Pixel Error: missing required parameters: %s' % email_body)
        return HttpResponseBadRequest('Missing required parameters.')

    # Verify that order_value is a decimal value
    try:
        order_value = decimal.Decimal(order_value)
    except Exception as e:
        email_body = render_to_string('advertiser/email_default_error.txt', locals())
        logger.warn('Advertiser Pixel Error: order value must be a number %s' % email_body)

        return HttpResponseBadRequest('Order value must be a number.')

    # TODO: do we need to verify domain?

    # Load models
    Transaction = get_model('advertiser', 'Transaction')
    Product = get_model('advertiser', 'Product')
    Store = get_model('advertiser', 'Store')
    Cookie = get_model('advertiser', 'Cookie')

    # Retrieve store object
    store = None
    try:
        store = Store.objects.get(identifier=store_id)
    except Store.DoesNotExist:
        pass

    # Cookie data
    status = Transaction.INVALID
    cookie_datetime = custom = None
    cookie_data = request.get_signed_cookie(get_cookie_name(store_id), default=False)
    if cookie_data and store:
        status = Transaction.TOO_OLD
        cookie_datetime, cookie_id = cookie_data.split('|')
        cookie_datetime = dateutil.parser.parse(cookie_datetime)
        try:
            cookie_instance = Cookie.objects.get(cookie_id=cookie_id)

            if cookie_datetime + datetime.timedelta(days=store.cookie_days) >= timezone.now():
                custom = cookie_instance.custom
                status = Transaction.PENDING
        except Cookie.DoesNotExist as e:
            email_body = render_to_string('advertiser/email_default_error.txt', locals())
            mail_superusers('Advertiser Pixel Warning: could not find cookie in database', email_body)
            logger.exception('Could not find cookie in database')

    # Calculate commission
    commission = 0
    if store:
        commission = store.commission_percentage * order_value

    # Currency conversion
    original_commission = commission
    original_order_value = order_value
    original_currency = currency.upper()

    currency = 'EUR'
    commission, exchange_rate = exchange_amount(currency, original_currency, commission)
    order_value, _ = exchange_amount(currency, original_currency, order_value, fixed_rate=exchange_rate)

    defaults = {
        'ip_address': get_client_ip(request),
        'status': status,
        'cookie_date': cookie_datetime,
        'currency': currency,
        'original_currency': original_currency,
        'exchange_rate': exchange_rate,
        'order_value': order_value,
        'commission': commission,
        'original_order_value': original_order_value,
        'original_commission': original_commission,
        'custom': custom
    }

    created = False
    transaction = None

    # Handle exception when there is more than one transaction retrieved from the query
    try:
        transaction, created = Transaction.objects.get_or_create(store_id=store_id, order_id=order_id, defaults=defaults)
    except Transaction.MultipleObjectsReturned, ex:
        duplicates = Transaction.objects.filter(store_id=store_id, order_id=order_id)
        logger.warning('Multiple transactions returned for store %s and order %s. Ids for duplicates are [%s].' % (store_id, order_id, ",".join(duplicates.values_list('id',flat=True))) )
            # Return 1x1 transparent pixel
        content = b'GIF89a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
        response = HttpResponse(content, mimetype='image/gif')
        response['Cache-Control'] = 'no-cache'
        response['Content-Length'] = len(content)
        return response
        #transaction = duplicates[0]

    if not created:
        for attr, val in defaults.items():
            if hasattr(transaction, attr):
                setattr(transaction, attr, val)
        transaction.save()
    else:
        if transaction.status == Transaction.PENDING:
            defaults.update({'order_id': order_id, 'store_id': store_id, 'pk': transaction.pk})
            email_body = render_to_string('advertiser/email_success.txt',
                                          {'defaults': defaults, 'request': request})
            mail_superusers('Advertiser Pixel Info: new purchase on %s' % (store_id,), email_body)

    # Insert optional product data
    product_sku = request.GET.get('sku')
    product_quantity = request.GET.get('quantity')
    product_price = request.GET.get('price')
    product_list = [product_sku, product_quantity, product_price]

    if all(product_list):
        skus = product_sku.split('^')
        quantities = product_quantity.split('^')
        prices = product_price.split('^')
        if not (len(skus) == len(quantities) == len(prices)):
            email_body = render_to_string('advertiser/email_default_error.txt', locals())
            logger.warn('Advertiser Pixel Warning: length of every product parameter is not consistent: %s' % email_body)

        try:
            prices = [decimal.Decimal(x) for x in prices if x]
            quantities = [int(x) for x in quantities if x]
        except Exception as e:
            email_body = render_to_string('advertiser/email_default_error.txt', locals())
            logger.warn('Advertiser Pixel Error: could not convert price or quantity. %s' %  email_body)
        else:
            calculated_order_value = decimal.Decimal(sum([x*y for x, y in zip(quantities, prices)]))
            calculated_order_value = calculated_order_value.quantize(decimal.Decimal('0.01'))

            # Disabled sending out this mail because most stores send total order value with shipping costs
            #if calculated_order_value != original_order_value:
                #email_body = render_to_string('advertiser/email_default_error.txt', locals())
                #mail_superusers('Advertiser Pixel Warning: order value and individual products value is not equal', email_body)

            for sku, quantity, price in zip(skus, quantities, prices):
                Product.objects.create(transaction=transaction,
                                       sku=sku,
                                       quantity=quantity,
                                       price=price)

    elif any(product_list) and not all(product_list):
        email_body = render_to_string('advertiser/email_default_error.txt', locals())
        logger.warn('Advertiser Pixel Error: missing one or more product parameters: %s' % email_body)

    # Return 1x1 transparent pixel
    content = b'GIF89a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
    response = HttpResponse(content, mimetype='image/gif')
    response['Cache-Control'] = 'no-cache'
    response['Content-Length'] = len(content)

    return response


def link(request):
    """
    Advertiser link

    Here we set a cookie and then redirect to the product url.
    """
    url = request.GET.get('url')
    if not url:
        return HttpResponseBadRequest('Missing url parameter.')

    store_id = request.GET.get('store_id')
    if not store_id:
        return HttpResponseBadRequest('Missing store_id parameter.')

    # Old cookie ID
    old_cookie_id = None
    cookie_data = request.get_signed_cookie(get_cookie_name(store_id), default=False)
    if cookie_data:
        cookie_datetime, old_cookie_id = cookie_data.split('|')

    # Custom tracking data
    user_id = request.GET.get('user_id')
    product_id = request.GET.get('product_id', 0)
    placement = request.GET.get('placement')
    custom = request.GET.get('custom')
    if user_id and placement:
        custom = '%s-%s-%s' % (user_id, product_id, placement)

    # Cookie date
    current_datetime = timezone.now()
    expires_datetime = current_datetime + datetime.timedelta(days=60)

    # Insert into DB and set cookie
    cookie_id = uuid.uuid4().hex

    Cookie = get_model('advertiser', 'Cookie')
    Cookie.objects.create(cookie_id=cookie_id,
                          store_id=store_id,
                          old_cookie_id=old_cookie_id,
                          custom=custom,
                          created=current_datetime)

    cookie_data = '%s|%s' % (current_datetime.isoformat(), cookie_id)
    response = redirect(url)
    response.set_signed_cookie(get_cookie_name(store_id), cookie_data,
            expires=expires_datetime, httponly=True)

    return response

def get_original_currency_from_sales(vendor):
    currency = "EUR"
    click_cost_query = get_model('dashboard', 'ClickCost').objects.filter(vendor=vendor)

    if len(click_cost_query) > 0:
        currency = click_cost_query[0].currency
    return currency

def get_top_summary_store(store):
    Transaction = get_model('advertiser', 'Transaction')
    accepted_commission = decimal.Decimal(0.00)
    commission_to_be_invoiced = decimal.Decimal(0.00)

    if store.vendor.is_cpc:
        accepted_query = get_model('advertiser', 'StoreInvoice').objects.filter(is_paid=False, store=store)

        for row in accepted_query:
            total, _ = row.get_total()
            accepted_commission += total

        to_be_invoiced_query = Transaction.objects.filter(status=Transaction.ACCEPTED, store_id=store.identifier, invoice=None) \
                                              .aggregate(Sum('original_commission'))
        if to_be_invoiced_query['original_commission__sum']:
            commission_to_be_invoiced = to_be_invoiced_query['original_commission__sum']
    elif store.vendor.is_cpo:
        invoices = get_model('advertiser', 'StoreInvoice').objects.filter(is_paid=False, store=store)

        for row in invoices:
            total = row.transactions.aggregate(total=Sum('commission')).get('total', 0)
            accepted_commission += total

        to_be_invoiced_query = Transaction.objects.filter(status=Transaction.ACCEPTED,
                                                                store_id=store.identifier, invoice=None) \
                                              .aggregate(Sum('commission'))
        if to_be_invoiced_query['commission__sum']:
            commission_to_be_invoiced = to_be_invoiced_query['commission__sum']

    return accepted_commission, commission_to_be_invoiced

def get_monthly_click_value(store, start_date, end_date):
    Transaction = get_model('advertiser', 'Transaction')
    monthly_click_value = decimal.Decimal(0.00)
    if store.vendor.is_cpc:
        monthly_click_value_query = Transaction.objects.filter(status__in=[Transaction.ACCEPTED,
                                                                                 Transaction.PENDING],
                                                               cookie_date__gte=start_date,
                                                               cookie_date__lte=end_date,
                                                               store_id=store.identifier) \
                                              .aggregate(Sum('original_commission'))
        if monthly_click_value_query['original_commission__sum']:
            monthly_click_value = monthly_click_value_query['original_commission__sum']
    return monthly_click_value

@login_required
def store_admin(request, year=None, month=None):
    """
    Administration panel for a store.
    """
    Transaction = get_model('advertiser', 'Transaction')
    try:
        store = request.user.advertiser_store
    except get_model('advertiser', 'Store').DoesNotExist:
        raise Http404()

    # Start date and end date + current month and year
    if year is not None and month is not None:
        start_date = datetime.date(int(year), int(month), 1)
    else:
        start_date = datetime.date.today().replace(day=1)

    end_date = start_date
    end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

    year = start_date.year
    month = start_date.month
    month_display = start_date.strftime('%B')

    start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

    end_date_clicks_query = end_date_query
    if end_date >= datetime.date.today():
        end_date_clicks_query = datetime.datetime.combine(
            datetime.date.today() - datetime.timedelta(1), datetime.time(23, 59, 59, 999999))

    currency = "EUR"

    # Get top summary
    accepted_commission, commission_to_be_invoiced = get_top_summary_store(store)

    # Get clicks delivered under the given period for the store
    clicks = get_model('statistics', 'ProductStat').objects.filter(created__gte=start_date_query, created__lte=end_date_clicks_query) \
                                                           .filter(vendor=store.vendor) \
                                                           .order_by('created')

    # Initialize variables for CPC stores
    total_clicks_per_month = 0
    clicks_delivered_per_month = 0
    clicks_cost_per_month = 0
    clicks_per_day = {}
    click_cost = None

    if store.vendor.is_cpc:
        currency = get_original_currency_from_sales(store.vendor)
        total_clicks_per_month = get_total_clicks_per_vendor(store.vendor)
        clicks_delivered_per_month = get_number_clicks(store.vendor, start_date_query, end_date_clicks_query)
        clicks_cost_per_month, _ = get_clicks_amount(store.vendor, start_date_query, end_date_clicks_query)
        try:
            click_cost = get_model('dashboard', 'ClickCost').objects.get(vendor=store.vendor)
            for row in clicks:
                #if row.amount > 0 and row.clicks > 0:
                date_key = datetime.datetime.strftime(row.created, "%Y%m%d")
                if not date_key in clicks_per_day:
                    row_start_date = datetime.datetime.combine(row.created, datetime.time(0, 0, 0, 0))
                    row_end_date = datetime.datetime.combine(row.created, datetime.time(23, 59, 59, 999999))
                    amount, _ = get_clicks_amount(store.vendor, row_start_date, row_end_date)
                    product_name = row.product
                    try:
                        product = get_model('apparel', 'Product').objects.get(slug=row.product)
                        product_name  = product.product_name
                    except get_model('apparel', 'Product').DoesNotExist:
                        logger.warning("Product %s does not exist." % row.product)

                    temp_dict = {
                        'date': row.created,
                        'amount': amount,
                        'clicks': 0,
                        'name': product_name
                    }
                    if temp_dict['amount'] > 0:
                        clicks_per_day[date_key] = temp_dict
                if date_key in clicks_per_day:
                    clicks_per_day[date_key]['clicks'] += 1

            # Sort clicks per day
            clicks_per_day = sorted(clicks_per_day.items(), key=operator.itemgetter(0), reverse=True)
        except get_model('dashboard', 'ClickCost').DoesNotExist:
            logger.warning("No cost per click defined for vendor %s"%store.vendor)

    # Get monthly click value
    monthly_click_value = get_monthly_click_value(store, start_date_query, end_date_clicks_query)

    # Get all transactions for store for the given month - CPO
    transactions = Transaction.objects.filter(status__in=[Transaction.ACCEPTED, Transaction.PENDING,
                                                                Transaction.REJECTED]) \
                                      .filter(created__gte=start_date_query, created__lte=end_date_query) \
                                      .filter(store_id=store.identifier) \
                                      .prefetch_related('products')

    monthly_sales = decimal.Decimal(0.00)
    sales_generated = 0

    if store.vendor.is_cpo:
        accepted_per_month_query = Transaction.objects.filter(status__in=[Transaction.ACCEPTED,
                                                                                Transaction.PENDING],
                                                              created__gte=start_date_query, created__lte=end_date_query,
                                                              store_id=store.identifier) \
                                                  .aggregate(Sum('order_value'))

        if accepted_per_month_query['order_value__sum']:
            monthly_sales = accepted_per_month_query['order_value__sum']

        total_sales_query = get_model('dashboard', 'Sale').objects.filter(vendor=store.vendor,
                                                                    status__gte=get_model('dashboard', 'Sale').PENDING) \
                                                           .aggregate(amount=Sum('converted_amount'))
        if 'amount' in total_sales_query and total_sales_query['amount']:
            sales_generated = total_sales_query['amount']

    dt1 = request.user.date_joined.date()
    dt2 = datetime.date.today()
    start_month = dt1.month
    end_months = (dt2.year - dt1.year) * 12 + dt2.month + 1
    dates = [datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
        ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
    )]

    # Chart data (transactions and clicks)
    data_per_month = {}
    for day in range(1, (end_date - start_date).days + 2):
        data_per_month[start_date.replace(day=day)] = [0, 0]

    for transaction in transactions:
        if transaction.status in [Transaction.ACCEPTED, Transaction.PENDING]:
            data_per_month[transaction.created.date()][0] += transaction.order_value

    for click in clicks:
        data_per_month[click.created.date()][1] += 1

    return render(request, 'advertiser/store_admin.html', { # General data
                                                            'transactions': transactions,
                                                            'store': request.user.advertiser_store,
                                                            'dates': dates,
                                                            'year': year,
                                                            'month': month,
                                                            'month_display': month_display,
                                                            'vendor': store.vendor,
                                                            'currency': currency,
                                                            'accepted_commission': accepted_commission,
                                                            'commission_to_be_invoiced': commission_to_be_invoiced,
                                                            'data_per_month': data_per_month,

                                                            # CPO data
                                                            'sales_generated': sales_generated,
                                                            'monthly_sales': monthly_sales,

                                                            # CPC data
                                                            'click_cost': click_cost,
                                                            'clicks_delivered_per_month': clicks_delivered_per_month,
                                                            'monthly_click_value': monthly_click_value,
                                                            'clicks_cost_per_month': clicks_cost_per_month,
                                                            'total_clicks_per_month': total_clicks_per_month,
                                                            'clicks_per_day': clicks_per_day,
                                                          })

@login_required
def store_admin_accept(request, transaction_id):
    try:
        store = request.user.advertiser_store
    except get_model('advertiser', 'Store').DoesNotExist:
        raise Http404()

    try:
        transaction = get_model('advertiser', 'Transaction').objects.get(pk=transaction_id)
    except get_model('advertiser', 'Transaction').DoesNotExist:
        raise Http404

    if request.method == 'POST':
        transaction.accept()

    return render(request, 'advertiser/modal_accept.html', {'transaction': transaction})


@login_required
def store_admin_reject(request, transaction_id):
    try:
        store = request.user.advertiser_store
    except get_model('advertiser', 'Store').DoesNotExist:
        raise Http404()

    try:
        transaction = get_model('advertiser', 'Transaction').objects.get(pk=transaction_id)
    except get_model('advertiser', 'Transaction').DoesNotExist:
        raise Http404

    if request.method == 'POST':
        message = request.POST.get('message')

        transaction.status_message = message
        transaction.status = get_model('advertiser', 'Transaction').REJECTED
        transaction.save()

        email_body = render_to_string('advertiser/email_rejected.txt', {'transaction_id': transaction.pk,
                                                                       'message': message,
                                                                       'store_id': transaction.store_id,
                                                                       'order_id': transaction.order_id})
        mail_superusers('transaction_model rejected', email_body)

    return render(request, 'advertiser/modal_reject.html', {'transaction': transaction})


def test_link(request):
    if not request.user.is_superuser:
        raise Http404()

    url = request.GET.get('url')
    store_id = request.GET.get('store_id')

    link = make_advertiser_url(store_id, url, request)

    return HttpResponse('<a target="_blank" href="%s">Click me: %s</a>' % (link, link))
