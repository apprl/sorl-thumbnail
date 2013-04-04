import datetime
import decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import get_model
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.template.loader import render_to_string


import dateutil.parser

from apparelrow.statistics.utils import get_client_ip
from affiliate.tasks import send_text_email_task


AFFILIATE_COOKIE_NAME = 'aan_click'


def pixel(request):
    """
    Affiliate pixel
    """
    store_id = request.GET.get('store_id')
    order_id = request.GET.get('order_id')
    order_value = request.GET.get('order_value')
    currency = request.GET.get('currency')

    if not store_id or not order_id or not order_value or not currency:
        # TODO: incomplete pixel request, notify admin for further communication with store
        return HttpResponseBadRequest('Missing required parameters.')

    # Verify that order_value is a decimal value
    try:
        order_value = decimal.Decimal(order_value)
    except Exception as e:
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
    cookie_datetime = user_id = page = None
    cookie_data = request.get_signed_cookie(AFFILIATE_COOKIE_NAME, default=False)
    if cookie_data and store:
        status = Transaction.TOO_OLD
        cookie_datetime, user_id, page = cookie_data.split('|')
        cookie_datetime = dateutil.parser.parse(cookie_datetime)

        if cookie_datetime + datetime.timedelta(days=store.cookie_days) >= timezone.now():
            status = Transaction.PENDING

    # Calculate commission
    commission = 0
    if store:
        commission = store.commission_percentage * order_value

    # TODO: insert cookie data such as user_id and page
    transaction = Transaction.objects.create(store_id=store_id,
                                             order_id=order_id,
                                             order_value=order_value,
                                             currency=currency,
                                             ip_address=get_client_ip(request),
                                             status=status,
                                             cookie_date=cookie_datetime,
                                             commission=commission)

    # Insert optional product data
    product_sku = request.GET.get('sku')
    product_quantity = request.GET.get('quantity')
    product_price = request.GET.get('price')
    product_list = [product_sku, product_quantity, product_price]

    if all(product_list):
        skus = product_sku.split('^')
        quantities = product_quantity.split('^')
        price = product_price.split('^')
        if not (len(skus) == len(quantities) == len(price)):
            # TODO: notify admin, missing either sku, quantity or price
            pass

        for sku, quantity, price in zip(skus, quantities, price):
            Product.objects.create(transaction=transaction,
                                   sku=sku,
                                   quantity=quantity,
                                   price=price)

    elif any(product_list) and not all(product_list):
        # TODO: notify admin, all product variables are required or none
        pass

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
def store_admin(request):
    """
    Administration panel for a store.
    """
    try:
        store = request.user.affiliate_store
    except get_model('affiliate', 'Store').DoesNotExist:
        raise Http404()

    Transaction = get_model('affiliate', 'Transaction')
    transactions = Transaction.objects.filter(status__in=[Transaction.ACCEPTED, Transaction.PENDING, Transaction.REJECTED]) \
                                      .filter(store_id=store.identifier)

    return render(request, 'affiliate/store_admin.html', {'transactions': transactions})


@login_required
def store_admin_accept(request, transaction_id):
    try:
        transaction = get_model('affiliate', 'Transaction').objects.get(pk=transaction_id)
    except get_model('affiliate', 'Transaction').DoesNotExist:
        raise Http404

    if request.method == 'POST':
        transaction.status = get_model('affiliate', 'Transaction').ACCEPTED
        transaction.save()

    return render(request, 'affiliate/dialog_accept.html', {'transaction': transaction})


@login_required
def store_admin_reject(request, transaction_id):
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
        for user in get_user_model().objects.filter(is_superuser=True, email__isnull=False):
            if user.email:
                send_text_email_task.delay('Transaction rejected', email_body, [user.email])

    return render(request, 'affiliate/dialog_reject.html', {'transaction': transaction})
