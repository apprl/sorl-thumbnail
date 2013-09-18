import datetime
import logging
import uuid
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve
from django.db.models import get_model
from django.http import HttpResponseRedirect
from django.utils import timezone


REFERRAL_COOKIE_NAME = 'aid_cookie'
REFERRAL_COOKIE_DAYS = 30

logger = logging.getLogger('apparelrow.apparel.middleware')


class GenderMiddleware(object):
    def process_request(self, request):
        cookie_value = request.COOKIES.get(settings.APPAREL_MULTI_GENDER_COOKIE, None)
        try:
            request.app_multi_gender = json.loads(cookie_value)
        except:
            request.app_multi_gender = {'feed': 'A', 'look': 'A', 'user': 'A', 'shop': 'A'}

    def process_response(self, request, response):
        if hasattr(request, 'app_multi_gender'):
            try:
                cookie_value = json.dumps(request.app_multi_gender, separators=(',', ':'))
                response.set_cookie(settings.APPAREL_MULTI_GENDER_COOKIE, value=cookie_value, max_age=365 * 24 * 60 * 60)
            except:
                pass

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
            if request.user.is_authenticated():
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
