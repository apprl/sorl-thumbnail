from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required

import re
import math
# Create your views here.
from pprint import pprint

def manage(request):
    pass
    

@login_required
def watch_result(request, name, format='site'):
    # Retrieve named query
    
    watch = get_object_or_404(Watch, user=request.user, name=name)
    
    # If format is 'site', redirect to search result
    if format == 'site':
        return HttpResponseRedirect('/apparel/products/search?=' + watch.query)
    
    if format == 'rss':
        return 'This is the RSS content'


@login_required
def save_query(request, query):
    if request.is_ajax:
        # Return something that is good for ajax client
        HttpResponse(
           {'status': 'ok'},
            mimetype='text/json'
        )
    
    # Back to original page, or if not availble to the management page for
    # watches
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/profile/watch'))
