import datetime
import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve
from django.db.models import get_model
from django.http import HttpResponseRedirect
from django.utils import timezone


COOKIE_NAME = 'acamp_cookie'
logger = logging.getLogger('apparelrow.apparel.middleware')


class InternalReferralMiddleware(object):
    def process_response(self, request, response):
        sid = request.GET.get('acamp_id')
        page = request.GET.get('acamp_page', 'Ext-Link')
        if sid and page:
            # Get previous cookie
            old_cookie = request.get_signed_cookie(COOKIE_NAME, default=False)
            old_cookie_id = None
            if old_cookie:
                old_cookie_id, old_sid, old_page, _ = old_cookie.split('|')

            # Cookie content
            current_datetime = timezone.now()
            expires_datetime = current_datetime + datetime.timedelta(days=15)
            cookie_id = uuid.uuid4().hex
            cookie_data = '%s|%s|%s|%s' % (cookie_id, sid, page, str(current_datetime))

            # User
            user_id = None
            if request.user.is_authenticated():
                user_id = request.user.pk

            # Update database
            InternalReferral = get_model('apparel', 'InternalReferral')
            try:
                InternalReferral.objects.get(cookie_id=old_cookie_id).update(expired=True)
            except InternalReferral.DoesNotExist:
                pass

            InternalReferral.objects.create(cookie_id=cookie_id,
                                            old_cookie_id=old_cookie_id,
                                            sid=sid,
                                            page=page,
                                            user_id=user_id,
                                            expires=expires_datetime,
                                            created=current_datetime)

            print 'winnnn', cookie_data

            response.set_signed_cookie(COOKIE_NAME, cookie_data, expires=expires_datetime, httponly=True)

        return response
