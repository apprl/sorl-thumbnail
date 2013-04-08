import datetime
import decimal
import calendar

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import get_model, Sum
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.template.loader import render_to_string

import dateutil.parser

from apparelrow.statistics.utils import get_client_ip
from affiliate.tasks import send_text_email_task


AFFILIATE_COOKIE_NAME = 'aan_click'


def mail_superusers(subject, body):
    for user in get_user_model().objects.filter(is_superuser=True, email__isnull=False):
        if user.email:
            send_text_email_task.delay(subject, body, [user.email])


def pixel(request):
    """
    Affiliate pixel
    """
    store_id = request.GET.get('store_id')
    order_id = request.GET.get('order_id')
    order_value = request.GET.get('order_value')
    currency = request.GET.get('currency')

    if not store_id or not order_id or not order_value or not currency:
        email_body = render_to_string('affiliate/email_default_error.txt', locals())
        mail_superusers('Advertiser Pixel Error: missing required parameters', email_body)

        return HttpResponseBadRequest('Missing required parameters.')

    # Verify that order_value is a decimal value
    try:
        order_value = decimal.Decimal(order_value)
    except Exception as e:
        email_body = render_to_string('affiliate/email_default_error.txt', locals())
        mail_superusers('Advertiser Pixel Error: order value must be a number', email_body)

        return HttpResponseBadRequest('Order value must be a number.')

    # TODO: do we need to verify domain?

    Transaction = get_model('affiliate', 'Transaction')
    Product = get_model('affiliate', 'Product')
    Store = get_model('affiliate', 'Store')

    # Retrieve store object
    store = None
    try:
        store = Store.objects.get(identifier=store_id)
    except Store.DoesNotExist:
        pass

    # Cookie data
    status = Transaction.INVALID
    cookie_datetime = user_id = placement = None
    cookie_data = request.get_signed_cookie(AFFILIATE_COOKIE_NAME, default=False)
    if cookie_data and store:
        status = Transaction.TOO_OLD
        cookie_datetime, user_id, placement = cookie_data.split('|')
        cookie_datetime = dateutil.parser.parse(cookie_datetime)

        if cookie_datetime + datetime.timedelta(days=store.cookie_days) >= timezone.now():
            status = Transaction.PENDING

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
                                             user_id=user_id,
                                             placement=placement)

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
            email_body = render_to_string('affiliate/email_default_error.txt', locals())
            mail_superusers('Advertiser Pixel Warning: length of every product parameter is not consistent', email_body)

        try:
            prices = [decimal.Decimal(x) for x in prices]
            quantities = [int(x) for x in quantities]
        except Exception as e:
            email_body = render_to_string('affiliate/email_default_error.txt', locals())
            mail_superusers('Advertiser Pixel Error: could not convert price or quantity', email_body)
        else:
            calculated_order_value = decimal.Decimal(sum([x*y for x, y in zip(quantities, prices)]))
            calculated_order_value = calculated_order_value.quantize(decimal.Decimal('0.01'))

            if calculated_order_value != order_value:
                email_body = render_to_string('affiliate/email_default_error.txt', locals())
                mail_superusers('Advertiser Pixel Warning: order value and individual products value is not equal', email_body)

            for sku, quantity, price in zip(skus, quantities, prices):
                Product.objects.create(transaction=transaction,
                                       sku=sku,
                                       quantity=quantity,
                                       price=price)

    elif any(product_list) and not all(product_list):
        email_body = render_to_string('affiliate/email_default_error.txt', locals())
        mail_superusers('Advertiser Pixel Error: missing one or more product parameters', email_body)

    # Return 1x1 transparent pixel
    content = b'GIF89a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
    response = HttpResponse(content, mimetype='image/gif')
    response['Cache-Control'] = 'no-cache'
    response['Content-Length'] = len(content)

    return response


def link(request):
    """
    Affiliate link

    Here we set a cookie and then redirect to the product url.
    """
    url = request.GET.get('url')
    if not url:
        return HttpResponseBadRequest('Missing url parameter.')

    current_datetime = timezone.now()
    expires_datetime = current_datetime + datetime.timedelta(days=60)

    # TODO: datetime, unique_id, extra: (user_id, page position)
    # TODO: might set it using an extra field like all the other networks
    # TODO: store it in a database and only store a reference to the row in the cookie
    cookie_data = '%s|%s|%s' % (current_datetime.isoformat(),
                                request.GET.get('user_id', 0),
                                request.GET.get('page', 'Default'))

    response = redirect(url)
    response.set_signed_cookie(AFFILIATE_COOKIE_NAME, cookie_data,
            expires=expires_datetime, httponly=True)

    return response


@login_required
def store_admin(request, year=None, month=None):
    """
    Administration panel for a store.
    """
    try:
        store = request.user.affiliate_store
    except get_model('affiliate', 'Store').DoesNotExist:
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

    Transaction = get_model('affiliate', 'Transaction')
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

    return render(request, 'affiliate/store_admin.html', {'transactions': transactions,
                                                          'store': request.user.affiliate_store,
                                                          'dates': dates,
                                                          'selected_date': 'abc',
                                                          'year': year,
                                                          'month': month,
                                                          'accepted_commission': accepted_commission,
                                                          'total_accepted_commission': total_accepted_commission})


@login_required
def store_admin_accept(request, transaction_id):
    try:
        store = request.user.affiliate_store
    except get_model('affiliate', 'Store').DoesNotExist:
        raise Http404()

    try:
        transaction = get_model('affiliate', 'Transaction').objects.get(pk=transaction_id)
    except get_model('affiliate', 'Transaction').DoesNotExist:
        raise Http404

    if request.method == 'POST':
        transaction.status = get_model('affiliate', 'Transaction').ACCEPTED
        transaction.save()

        request.user.affiliate_store.balance += transaction.commission
        request.user.affiliate_store.save()

    return render(request, 'affiliate/dialog_accept.html', {'transaction': transaction})


@login_required
def store_admin_reject(request, transaction_id):
    try:
        store = request.user.affiliate_store
    except get_model('affiliate', 'Store').DoesNotExist:
        raise Http404()

    try:
        transaction = get_model('affiliate', 'Transaction').objects.get(pk=transaction_id)
    except get_model('affiliate', 'Transaction').DoesNotExist:
        raise Http404

    if request.method == 'POST':
        message = request.POST.get('message')

        transaction.status_message = message
        transaction.status = get_model('affiliate', 'Transaction').REJECTED
        transaction.save()

        email_body = render_to_string('affiliate/email_rejected.txt', {'transaction_id': transaction.pk,
                                                                       'message': message,
                                                                       'store_id': transaction.store_id,
                                                                       'order_id': transaction.order_id})
        mail_superusers('Transaction rejected', email_body)

    return render(request, 'affiliate/dialog_reject.html', {'transaction': transaction})
