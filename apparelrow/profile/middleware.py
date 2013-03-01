import logging

from django.contrib.auth import get_user_model
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
