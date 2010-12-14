import logging
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext

from apparel.decorators import seamless_request_handling
from apparel.models import *
from apparel.forms import *




def profile(request):
    """
    Displays the profile page
    """
    user = request.user
    
    activity = []
    recent_looks = Look.objects.filter(user=user).order_by('-modified')[:4]
    
    context = {
        'activitiy': activity,
        'recent_looks': recent_looks,
        #'recent_likes': recent_likes
    }
    
    return render_to_response('profile/profile.html', context, context_instance=RequestContext(request))
    