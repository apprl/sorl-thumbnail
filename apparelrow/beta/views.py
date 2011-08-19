import random
import string
from datetime import datetime, timedelta

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseNotFound
from django.template import RequestContext
from django.conf import settings
from django.utils import translation
from django.core.validators import email_re

from beta.models import Invitee, Invite
from beta.tasks import send_email_task

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
            invitee.used_count += 1
            invitee.save() # Update seen attribute
            response = HttpResponseRedirect(request.POST.get('next', '/'))
            response.set_cookie('in_beta', value='1', max_age=365 * 24 * 60 * 60)
            return response
        except Invitee.DoesNotExist:
            return render_to_response('beta/beta.html', {'next': request.POST.get('next', '/')}, context_instance=RequestContext(request))
    else:
        return render_to_response('beta/beta.html', {'next': request.GET.get('next', '/')}, context_instance=RequestContext(request))

def invite(request):
    if request.user and request.user.is_authenticated:
        if request.method == 'POST':
            redirect_page = request.POST.get('next', '/')
            emails = request.POST.getlist('email')
            email_count = 0
            for email in emails:
                if email_count >= request.user.get_profile().beta.invites:
                    break

                if email_re.match(email):
                    name = request.user.get_profile().display_name

                    try:
                        invitee = Invitee.objects.get(email=email)
                    except Invitee.DoesNotExist:
                        invite = Invite.objects.create(code=''.join(random.choice(string.letters + string.digits) for i in xrange(8)))
                        invitee = Invitee.objects.create(email=email, invite=invite)

                    send_email_task.delay(name, invitee.email, invitee.invite.code)
                    email_count += 1

            if email_count > 0:
                request.user.get_profile().beta.invites -= email_count
                request.user.get_profile().beta.save()

            return HttpResponseRedirect(redirect_page)

        if request.user.get_profile().beta and request.user.get_profile().beta.invites > 0:
            return render_to_response('beta/dialog_invite_user.html', {
                    'invites_count': request.user.get_profile().beta.invites,
                    'display_count': xrange(min(5, request.user.get_profile().beta.invites)),
                    'next': request.GET.get('next', '/'),
                }, context_instance=RequestContext(request))

    return HttpResponseNotFound()

def about(request):
    return render_to_response('beta/about.html', context_instance=RequestContext(request))
