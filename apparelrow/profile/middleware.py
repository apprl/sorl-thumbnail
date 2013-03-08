import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve
from django.http import HttpResponseRedirect

logger = logging.getLogger('profile.middleware')

class ImpersonateMiddleware(object):
    def process_request(self, request):
        try:
            if request.user.is_superuser and '__imitera' in request.GET:
                request.user = get_user_model().objects.get(id=int(request.GET['__imitera']))
        except Exception as e:
            logger.error('ImpersonateMiddleware request: %s' % (str(e),))

    def process_response(self, request, response):
        try:
            if request.user.is_superuser and '__imitera' in request.GET:
                if isinstance(response, HttpResponseRedirect):
                    location = response['Location']
                    if '?' in location:
                        location += '&'
                    else:
                        location += '?'
                    location += '__imitera=%s' % request.GET['__imitera']
                    response['Location'] = location
        except Exception as e:
            logger.error('ImpersonateMiddleware response: %s' % (str(e),))

        return response


class LoginFlowMiddleware:
    def process_request(self, request):
        try:
            if request.user.is_authenticated() and request.user.login_flow != 'complete':
                resolved_url = resolve(request.path)
                if not request.path.startswith('/media') and \
                   not request.path.startswith('/static') and \
                   not request.path.startswith('/jsi18n') and \
                   not resolved_url.url_name.startswith('auth') and \
                   not resolved_url.url_name.startswith('login-flow'):
                    response = HttpResponseRedirect(reverse('profile.views.login_flow_%s' % (request.user.login_flow)))
                    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=request.user.gender, max_age=365 * 24 * 60 * 60)
                    return response

        except Exception as e:
            logger.error('LoginFlowMiddleware response: %s' % (str(e),))
