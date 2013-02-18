from django.http import HttpResponseRedirect, HttpResponseNotFound

# TODO: should be removed or redirected to new /redirect/ or /track/
def product_click_count(request):
    url = request.GET.get('u', None)
    product_id = request.GET.get('i', None)
    s_id = request.GET.get('s', 0)
    page = request.GET.get('p', 'Default')
    if url and product_id:
        return HttpResponseRedirect(url)
    return HttpResponseNotFound()
