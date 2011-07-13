from django.http import HttpResponseRedirect

from apparelrow.apparel.models import VendorProduct
from apparelrow.statistics.messaging import send_increment_clicks

def product_click_count(request):
    url = request.GET.get('u', None)
    product_id = request.GET.get('i', None)
    print product_id
    if url and product_id:
        send_increment_clicks(product_id)
        return HttpResponseRedirect(url)
    return HttpResponseNotFound()
