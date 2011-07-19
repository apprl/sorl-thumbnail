from django.middleware.locale import LocaleMiddleware
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
