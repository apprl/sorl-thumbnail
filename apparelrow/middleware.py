from django.middleware.locale import LocaleMiddleware
from django.http import HttpResponseRedirect
from django.utils import translation
from django.conf import settings

class SwedishOnlyLocaleMiddleware(LocaleMiddleware):
    """
    Always select swedish (sv) as locale.
    """
    def process_request(self, request):
        supported = dict(settings.LANGUAGES)
        language = settings.LANGUAGE_CODE
        if hasattr(request, 'session'):
            lang_code = request.session.get('django_language', None)
            if lang_code in supported and lang_code is not None and translation.check_for_language(lang_code):
                language = lang_code

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

class GenderMiddleware(object):
    """
    Require a selected gender in order to view any page.
    """
    # TODO: update the cookie periodically
    def process_request(self, request):
        if not request.path.startswith('/gender') and not request.path.startswith('/beta') and \
           not request.path.startswith('/admin') and not request.path.startswith(settings.MEDIA_URL) and not request.COOKIES.get('gender'):
            return HttpResponseRedirect('%s?next=%s' % ('/gender/', request.path))
