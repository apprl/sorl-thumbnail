import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import get_model
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.utils import timezone

import dateutil.parser

from apparelrow.statistics.utils import get_client_ip


AFFILIATE_COOKIE_NAME = 'aan_click'


def pixel(request):
    """
    Affiliate pixel
    """
    store_id = request.GET.get('store_id')
    order_id = request.GET.get('order_id')
    order_value = request.GET.get('order_value')
    currency = request.GET.get('currency')

    Transaction = get_model('affiliate', 'Transaction')

    if not store_id or not order_id or not order_value or not currency:
        # TODO: incomplete pixel request, notify admin for further communication with store
        return HttpResponseBadRequest()

    # Cookie data
    status = Transaction.INVALID
    cookie_datetime = user_id = page = None
    cookie_data = request.get_signed_cookie(AFFILIATE_COOKIE_NAME)
    if cookie_data:
        status = Transaction.TOO_OLD
        cookie_datetime, user_id, page = cookie_data.split('|')
        cookie_datetime = dateutil.parser.parse(cookie_datetime)

        # TODO: verify that cookie_datetime is at most X days old based on store_id settings
        if cookie_datetime + datetime.timedelta(days=30) >= timezone.now():
            status = Transaction.PENDING

    # TODO: insert cookie data such as user_id and page
    transaction = Transaction.objects.create(store_id=store_id,
                                             order_id=order_id,
                                             order_value=order_value,
                                             currency=currency,
                                             ip_address=get_client_ip(request),
                                             status=status,
                                             cookie_date=cookie_datetime)

    # TODO: insert optional product data
    #product_sku = request.GET.get('sku')
    #product_quantity = request.GET.get('quantity')
    #product_price = request.GET.get('price')

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
        if not request.user.affiliate_store:
            raise Http404()
    except get_model('affiliate', 'Store').DoesNotExist:
        raise Http404()

    Transaction = get_model('affiliate', 'Transaction')
    transactions = Transaction.objects.filter(status__in=[Transaction.ACCEPTED, Transaction.PENDING, Transaction.REJECTED]) \
                                      .filter(store_id=request.user.affiliate_store.identifier)

    return render(request, 'affiliate/store_admin.html', {'transactions': transactions})
