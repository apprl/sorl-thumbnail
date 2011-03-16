from django.http import HttpResponseRedirect
from django.conf import settings

class BetaMiddleware(object):
    """
    Require beta code session key in order to view any page.
    """
    def process_request(self, request):
        if request.path != '/beta/' and not request.path.startswith('/admin') and not request.path.startswith(settings.MEDIA_URL) and not request.COOKIES.get('in_beta'):
            return HttpResponseRedirect('%s?next=%s' % ('/beta/', request.path))
