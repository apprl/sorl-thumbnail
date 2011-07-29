from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.template import RequestContext
from django.conf import settings
from django.utils import translation
from datetime import datetime, timedelta

from beta.models import *

# Create your views here.

def unlock(request):
    # Set language to user's browser language for beta view
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()

    if request.method == 'POST':
        try:
            invitee = Invitee.objects.get(email=request.POST.get('email'), invite__code=request.POST.get('code'))
            invitee.seen = datetime.utcnow()
            invitee.save() # Update seen attribute
            response = HttpResponseRedirect(request.POST.get('next', '/'))
            response.set_cookie('in_beta', value='1', max_age=365 * 24 * 60 * 60)
            return response
        except Invitee.DoesNotExist:
            return render_to_response('beta/beta.html', {'next': request.POST.get('next', '/')}, context_instance=RequestContext(request))
    else:
        return render_to_response('beta/beta.html', {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))

def about(request):
    return render_to_response('beta/about.html', context_instance=RequestContext(request))
