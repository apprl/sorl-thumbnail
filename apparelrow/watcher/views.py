from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _
from watcher.models import *

# Create your views here.
from pprint import pprint

@login_required
def manage(request):
    """
    Updates or deletes collected watches.
    """
    
    user = request.user
    
    if request.method == 'POST':
        # Make changes
        
        if 'delete' in request.POST:
            for query_id in request.POST.getlist('query_id'):
                stored_query = get_object_or_404(StoredQuery, pk=query_id)
                stored_query.delete()
        
        elif 'query_id' in request.POST:
            watch = get_object_or_404(StoredQuery, pk=request.POST['query_id'])
            
            if 'name' in request.POST:
                stored_query.name = request.POST['name']
            
            # FIXME: Enable/Disable E-Mail functionalty here.
            
            stored_query.save()
    
    queries = StoredQuery.objects.filter(user=user)
    return render_to_response('profile/watcher.html', { 'queries': queries }, context_instance=RequestContext(request))

@login_required
def execute(request, name, format='site'):
    # Retrieve named query
    
    stored_query = get_object_or_404(StoredQuery, user=request.user, name=name)
    
    # If format is 'site', redirect to search result
    if format == 'site':
        return HttpResponseRedirect('/apparel/products/search?' + stored_query.query)
    
    if format == 'rss':
        return 'This is the RSS content'


@login_required
def save_query(request, query):
    """
    Save the given query to the database. Takes an optional 'name' HTTP parameter
    to specify the name of the new saved query
    """
    user = request.user
        
    # FIXME: Handle exception for duplicate key and return exception to user
    # if there was any error
    
    stored_query = StoredQuery(user=user, name=request.GET.get('name', None), query=query)
    stored_query.save()
    
    if request.is_ajax:
        # Return something that is good for ajax client
        HttpResponse(
           {'status': 'ok'},
            mimetype='application/json'
        )
    
    # Back to original page, or if not availble to the management page for
    # watches. If there was an error, go to that page aswell.
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/profile/watcher'))
