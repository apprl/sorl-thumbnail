from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature

from apparelrow.dashboard.utils import get_referral_user_from_cookie

class ReferralMiddleware(object):
    def process_response(self, request, response):
        if settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME in request.COOKIES and hasattr(request, 'user') and request.user and request.user.is_authenticated():
            if not request.user.referral_partner_parent:
                user = get_referral_user_from_cookie(request)
                if user and user.is_active and user.is_partner and user.referral_partner and request.user != user:
                    request.user.referral_partner_parent = user
                    request.user.save()

        return response
