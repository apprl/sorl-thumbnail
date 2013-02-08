from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models.loading import get_model

from hanssonlarsson.django.exporter import json

def seamless_request_handling(view_func):
    """
    Wraps a view to handle AJAX and standard HTTP requests simultaniously. It
    also handles common exceptions thrown from the view.
    
    The decorated view is expected to return a single value or a tuple. 
    
    In case of a tuple, the first argument will be processed for AJAX requests,
    the second for other requests.
    
    For AJAX requests:
     * Always returns a HttpResponse object containing JSON
     * The response always contains a "status" key that is a boolean
     * If the view returns a HttpResponse object and response code is anything
       else than 200, "status" will False and the code stored in "error_message"
       In addition, if the HttpResponse object has a Location header, a "location"
       key will also be added to the response
     * If the view returns something else, it will be serialised in the "data" key
    
    For HTTP requests:
     * Always 
     * If view returns a string, it is assumed to be a URL and a HttpResponseRedirect is returned
     * If the view returns HttpResponseForbidden, the user will be redirected to login page
     * Any other HttpResponse will be passed on
     
    Doctest and decorators aren't friends, so this is tested in the standard test
    script.
    
    When using this decorator with in combination with others, remember to declare
    this decorator first.
    """
    def _decorator(request, *args, **kwargs):
        def _handle_view(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            
            except ObjectDoesNotExist, e:
                return HttpResponseNotFound()
            
            # FIXME: Raise internal server error, or just leave it?
        
        referer   = request.META.get('HTTP_REFERER', '/')
        login_url = '%s?next=%s' % (settings.LOGIN_URL, referer)  # FIXME: Is it possible to get this from somewhere?
        
        rsp = _handle_view(request, *args, **kwargs)
        (ajax_rsp, http_rsp) = (rsp[0], rsp[1]) if isinstance(rsp, tuple) else (rsp, rsp)
        
        if request.is_ajax():
            rsp_dict = { 'success': True }
            
            if isinstance(ajax_rsp, HttpResponse):
                if rsp.status_code != 200:
                    rsp_dict['success'] = False
                    rsp_dict['error_message'] = rsp.status_code
                
                    if isinstance(ajax_rsp, HttpResponseForbidden):
                        rsp['Location'] = login_url
                
                    if rsp.has_header('Location'):
                        rsp_dict['location'] = ajax_rsp['Location']
                    
            else:
                rsp_dict['data'] = ajax_rsp
            
            return HttpResponse(
                json.encode(rsp_dict),
                mimetype='application/json'
            )
        
        if isinstance(http_rsp, HttpResponseForbidden):
            return HttpResponseRedirect(login_url)  # Redirect to login with next to redirect if set
        
        return http_rsp
    
    _decorator.__name__ = view_func.__name__
    _decorator.__dict__ = view_func.__dict__
    _decorator.__doc__  = view_func.__doc__
    
    return _decorator
