import datetime

from django.conf import settings
from django.db.models import get_model
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from apparelrow.statistics.utils import get_client_ip


AFFILIATE_COOKIE_NAME = 'aan_click'


def pixel(request):
    """
    Affiliate pixel
    """
    company_id = request.GET.get('company_id')
    order_id = request.GET.get('order_id')
    order_value = request.GET.get('order_value')
    currency = request.GET.get('currency')

    if not company_id or not order_id or not order_value or not currency:
        # TODO: incomplete, return http error or store it but as incomplete
        # data and notify admin which can contact company if company_id is set
        pass

    # Cookie data
    cookie_data = request.get_signed_cookie(AFFILIATE_COOKIE_NAME)
    if not cookie_data:
        status = get_model('affiliate', 'Transaction').INVALID

    print cookie_data
    print get_client_ip(request)

    # TODO: insert data in transaction model

    # TODO: insert optional product data
    product_sku = request.GET.get('sku')
    product_quantity = request.GET.get('quantity')
    product_price = request.GET.get('price')

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

    current_datetime = datetime.datetime.utcnow()
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
