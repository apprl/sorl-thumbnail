from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.template import RequestContext
from django.conf import settings
from datetime import datetime, timedelta

from beta.models import *

# Create your views here.

def unlock(request):
    if request.method == 'POST':
        try:
            import pdb; pdb.set_trace()
            invitee = Invitee.objects.get(email=request.POST.get('email'), invite__code=request.POST.get('code'))
            invitee.seen = datetime.utcnow()
            invitee.save() # Update seen attribute
            response = HttpResponseRedirect(request.POST.get('next', '/'))
            expires = invitee.seen + timedelta(365)
            response.set_cookie('in_beta', value='1', expires=expires)
            return response
        except Invitee.DoesNotExist:
            return render_to_response('beta/beta.html', {'next': request.POST.get('next', '/')}, context_instance=RequestContext(request))
    else:
        return render_to_response('beta/beta.html', {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))
