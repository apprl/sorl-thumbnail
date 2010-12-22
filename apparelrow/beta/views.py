from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.template import RequestContext
from datetime import datetime

from beta.models import *

# Create your views here.

def unlock(request):
    if request.method == 'POST':
        try:
            invitee = Invitee.objects.get(email=request.POST.get('email'), invite__code=request.POST.get('code'))
            invitee.seen = datetime.utcnow()
            invitee.save() # Update seen attribute
            request.session['in_beta'] = True
            return HttpResponseRedirect(request.POST.get('next', '/'))
        except (DoesNotExist):
            return render_to_response('beta/beta.html', context_instance=RequestContext(request))
    else:
        return render_to_response('beta/beta.html', context_instance=RequestContext(request))
