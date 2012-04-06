from django.http import HttpResponseRedirect, HttpResponseNotFound

from statistics.tasks import increment_click

def product_click_count(request):
    url = request.GET.get('u', None)
    product_id = request.GET.get('i', None)
    if url and product_id:
        print 'here'
        increment_click.delay(product_id)
        return HttpResponseRedirect(url)
    return HttpResponseNotFound()
