import decimal

from django.conf import settings
from django.contrib.auth import get_user_model


def get_referral_user_from_cookie(request):
    user = None
    user_id = request.get_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, None)
    if user_id:
        try:
            user = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            pass

    return user


def get_cuts_for_user_and_vendor(user_id, vendor):
    user = None
    normal_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_CUT_DEFAULT)
    referral_cut = decimal.Decimal(settings.APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT)
    publisher_cut = 1
    try:
        user = get_user_model().objects.get(pk=user_id)
        if user.partner_group:
            try:
                cuts = user.partner_group.cuts.get(vendor=vendor)
                normal_cut = cuts.cut
                referral_cut = cuts.referral_cut

                if user.owner_network:
                    if user.owner_network.owner_network_cut > 1:
                        user.owner_network.owner_network_cut = 1
                    publisher_cut -= user.owner_network.owner_network_cut

            except:
                pass
    except get_user_model().DoesNotExist:
        pass

    return user, normal_cut, referral_cut, publisher_cut
