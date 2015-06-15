import datetime
import logging
import uuid
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve
from django.db.models import get_model
from django.http import HttpResponseRedirect
from django.utils import timezone, translation
from localeurl import utils
from apparelrow.apparel.utils import user_is_bot, save_location, has_user_location
from apparelrow.statistics.utils import get_country_by_ip


REFERRAL_COOKIE_NAME = 'aid_cookie'
REFERRAL_COOKIE_DAYS = 30

logger = logging.getLogger('apparelrow.apparel.middleware')


class UpdateLocaleSessionMiddleware(object):
    def process_request(self, request):
        if request.path.startswith('/da/'):
            return HttpResponseRedirect(request.get_full_path().replace('/da/', '/en/'))
        #elif request.path.startswith('/no/'):
        #    return HttpResponseRedirect(request.get_full_path().replace('/no/', '/en/'))

        try:
            language = request.LANGUAGE_CODE
        except AttributeError:
            language = translation.get_language()

        request.session['django_language'] = language
        if hasattr(request, 'user') and request.user.is_authenticated() and request.user.language != language:
            request.user.language = language
            request.user.save()


class GenderMiddleware(object):
    def process_request(self, request):
        cookie_value = request.COOKIES.get(settings.APPAREL_MULTI_GENDER_COOKIE, None)
        try:
            request.app_multi_gender = json.loads(cookie_value)
        except:
            shop_default = 'A'
            if hasattr(request, 'user') and request.user and request.user.is_authenticated() and request.user.gender:
                shop_default = request.user.gender
            request.app_multi_gender = {'feed': 'A', 'look': 'A', 'user': 'A', 'shop': shop_default}

    def process_response(self, request, response):
        if hasattr(request, 'app_multi_gender'):
            try:
                cookie_value = json.dumps(request.app_multi_gender, separators=(',', ':'))
                response.set_cookie(settings.APPAREL_MULTI_GENDER_COOKIE, value=cookie_value, max_age=365 * 24 * 60 * 60)
            except:
                pass

        return response

class LocationMiddleware(object):
    """
    Read market cookie and add it to request object
    """
    def process_request(self, request):
        cookie_value = request.COOKIES.get(settings.APPAREL_LOCATION_COOKIE, None)
        # If user is authenticated and has a stored location
        if request.user.is_authenticated():
            if has_user_location(request):
                # When user logs in
                try:
                    if request.session['location'] != request.user.location and \
                            request.session['location'] == cookie_value:
                        request.session['location'] = request.user.location
                    # When user change location on settings
                    elif request.session['location'] != cookie_value and \
                            request.session['location'] == request.user.location:
                        request.session['location'] = cookie_value
                        save_location(request, cookie_value)
                except KeyError:
                    pass
            else:
                save_location(request, cookie_value)
        else:
            if cookie_value:
                request.session['location'] = cookie_value
            elif not user_is_bot(request):
                request.session['location'] = get_country_by_ip(request)
        request.location = request.session.get('location','ALL')

    def process_response(self, request, response):
        cookie_value = request.COOKIES.get(settings.APPAREL_LOCATION_COOKIE, None)
        if not request.session.get('location',None) and not cookie_value:
            try:
                # Depending on localeurl strip path method
                location_choice = get_country_by_ip(request) if not user_is_bot(request) else 'ALL'
                locale, path = utils.strip_path(request.path)
                if locale:
                    for location, location_text, lang in settings.LOCATION_LANGUAGE_MAPPING:
                        if lang[0] == locale:
                            location_choice = location
                response.set_cookie(settings.APPAREL_LOCATION_COOKIE, value=location_choice, max_age=45 * 24 * 60 * 60)
            except:
                pass
        if request.session.get('location',None):
            if not cookie_value:
                response.set_cookie(settings.APPAREL_LOCATION_COOKIE, value=request.session.get('location'), max_age=45 * 24 * 60 * 60)
            elif not request.session.get('location') == cookie_value:
                response.set_cookie(settings.APPAREL_LOCATION_COOKIE, value=request.session['location'], max_age=45 * 24 * 60 * 60)
        return response

class InternalReferralMiddleware(object):
    def process_response(self, request, response):
        sid = request.GET.get('aid')
        page = request.GET.get('alink', 'Ext-Link')
        if sid and page:
            # Get previous cookie
            old_cookie = request.get_signed_cookie(REFERRAL_COOKIE_NAME, default=False)
            old_cookie_id = None
            if old_cookie:
                old_cookie_id, old_sid, old_page, _ = old_cookie.split('|')

            # Cookie content
            current_datetime = timezone.now()
            expires_datetime = current_datetime + datetime.timedelta(days=REFERRAL_COOKIE_DAYS)
            cookie_id = uuid.uuid4().hex
            cookie_data = '%s|%s|%s|%s' % (cookie_id, sid, page, str(current_datetime))

            # User
            user_id = None
            if hasattr(request, 'user') and request.user.is_authenticated():
                user_id = request.user.pk

            # Update database
            InternalReferral = get_model('apparel', 'InternalReferral')
            InternalReferral.objects.filter(cookie_id=old_cookie_id).update(expired=True)
            InternalReferral.objects.create(cookie_id=cookie_id,
                                            old_cookie_id=old_cookie_id,
                                            sid=sid,
                                            page=page,
                                            user_id=user_id,
                                            expires=expires_datetime,
                                            created=current_datetime)

            response.set_signed_cookie(REFERRAL_COOKIE_NAME, cookie_data, expires=expires_datetime, httponly=True)

        return response
