from django.http import HttpResponseRedirect, HttpResponseNotFound

from statistics.tasks import increment_click
from statistics.tasks import product_buy_click
from statistics.utils import get_client_referer, get_client_ip

def product_click_count(request):
    url = request.GET.get('u', None)
    product_id = request.GET.get('i', None)
    s_id = request.GET.get('s', 0)
    page = request.GET.get('p', 'Default')
    if url and product_id:
        product_buy_click.delay(product_id, get_client_referer(request), get_client_ip(request), s_id, page)
        increment_click.delay(product_id)
        return HttpResponseRedirect(url)
    return HttpResponseNotFound()
