import datetime
import decimal
import calendar
import uuid
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import get_model, Sum
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse

import dateutil.parser

from apparelrow.statistics.utils import get_client_ip
from advertiser.tasks import send_text_email_task


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
        mail_superusers('Advertiser Pixel Error: missing required parameters', email_body)

        return HttpResponseBadRequest('Missing required parameters.')

    # Verify that order_value is a decimal value
    try:
        order_value = decimal.Decimal(order_value)
    except Exception as e:
        email_body = render_to_string('advertiser/email_default_error.txt', locals())
        mail_superusers('Advertiser Pixel Error: order value must be a number', email_body)

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

    transaction = Transaction.objects.create(store_id=store_id,
                                             order_id=order_id,
                                             order_value=order_value,
                                             currency=currency,
                                             ip_address=get_client_ip(request),
                                             status=status,
                                             cookie_date=cookie_datetime,
                                             commission=commission,
                                             custom=custom)

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
            mail_superusers('Advertiser Pixel Warning: length of every product parameter is not consistent', email_body)

        try:
            prices = [decimal.Decimal(x) for x in prices]
            quantities = [int(x) for x in quantities]
        except Exception as e:
            email_body = render_to_string('advertiser/email_default_error.txt', locals())
            mail_superusers('Advertiser Pixel Error: could not convert price or quantity', email_body)
        else:
            calculated_order_value = decimal.Decimal(sum([x*y for x, y in zip(quantities, prices)]))
            calculated_order_value = calculated_order_value.quantize(decimal.Decimal('0.01'))

            if calculated_order_value != order_value:
                email_body = render_to_string('advertiser/email_default_error.txt', locals())
                mail_superusers('Advertiser Pixel Warning: order value and individual products value is not equal', email_body)

            for sku, quantity, price in zip(skus, quantities, prices):
                Product.objects.create(transaction=transaction,
                                       sku=sku,
                                       quantity=quantity,
                                       price=price)

    elif any(product_list) and not all(product_list):
        email_body = render_to_string('advertiser/email_default_error.txt', locals())
        mail_superusers('Advertiser Pixel Error: missing one or more product parameters', email_body)

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


@login_required
def store_admin(request, year=None, month=None):
    """
    Administration panel for a store.
    """
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

    start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
    end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

    Transaction = get_model('advertiser', 'Transaction')
    transactions = Transaction.objects.filter(status__in=[Transaction.ACCEPTED, Transaction.PENDING, Transaction.REJECTED]) \
                                      .filter(created__gte=start_date_query, created__lte=end_date_query) \
                                      .filter(store_id=store.identifier) \
                                      .prefetch_related('products')

    accepted_commission = decimal.Decimal(0.00)
    accepted_query = Transaction.objects.filter(status=Transaction.ACCEPTED, store_id=store.identifier) \
                                        .filter(created__gte=start_date_query, created__lte=end_date_query) \
                                        .aggregate(Sum('commission'))
    if accepted_query['commission__sum']:
        accepted_commission = accepted_query['commission__sum']

    total_accepted_commission = decimal.Decimal(0.00)
    total_accepted_query = Transaction.objects.filter(status=Transaction.ACCEPTED, store_id=store.identifier) \
                                              .aggregate(Sum('commission'))
    if total_accepted_query['commission__sum']:
        total_accepted_commission = total_accepted_query['commission__sum']

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
        data_per_month[transaction.created.date()][0] += 1

    clicks = get_model('statistics', 'ProductStat').objects.filter(created__gte=start_date_query, created__lte=end_date_query) \
                                                           .filter(vendor=store.vendor) \
                                                           .order_by('created')
    for click in clicks:
        data_per_month[click.created.date()][1] += 1

    return render(request, 'advertiser/store_admin.html', {'transactions': transactions,
                                                          'store': request.user.advertiser_store,
                                                          'dates': dates,
                                                          'selected_date': 'abc',
                                                          'year': year,
                                                          'month': month,
                                                          'accepted_commission': accepted_commission,
                                                          'total_accepted_commission': total_accepted_commission,
                                                          'data_per_month': data_per_month})


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
        transaction.status = get_model('advertiser', 'Transaction').ACCEPTED
        transaction.save()

        request.user.advertiser_store.balance += transaction.commission
        request.user.advertiser_store.save()

    return render(request, 'advertiser/dialog_accept.html', {'transaction': transaction})


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
        mail_superusers('Transaction rejected', email_body)

    return render(request, 'advertiser/dialog_reject.html', {'transaction': transaction})


def test_link(request):
    if not request.user.is_superuser:
        raise Http404()

    url = request.GET.get('url')
    store_id = request.GET.get('store_id')

    link = request.build_absolute_uri('%s?url=%s&store_id=%s' % (reverse('advertiser-link'), url, store_id))

    return HttpResponse('<a href="%s">Click me: %s</a>' % (link, link))
