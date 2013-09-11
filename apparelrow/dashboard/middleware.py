from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature


class ReferralMiddleware(object):
    def process_response(self, request, response):
        if settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME in request.COOKIES and request.user and request.user.is_authenticated():
            if not request.user.referral_partner_parent:
                try:
                    user_id = request.get_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME)
                    try:
                        user = get_user_model().objects.get(pk=user_id)
                        if user.is_active and user.is_partner and user.referral_partner:
                            request.user.referral_partner_parent = user
                            request.user.save()
                    except get_user_model().DoesNotExist:
                        pass
                except BadSignature:
                    pass

            response.delete_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME)

        return response
