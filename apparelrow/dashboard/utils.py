import decimal
import json

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
                data_exceptions = None

                # Handle exceptions for publisher cuts
                try:
                    data_exceptions = cuts.rules_exceptions
                    for data in data_exceptions:
                        if data['sid'] == user.id:
                            normal_cut = decimal.Decimal(data['cut'])
                except:
                    pass
                if user.owner_network:
                    owner = user.owner_network
                    if owner.owner_network_cut > 1:
                        owner.owner_network_cut = 1
                    publisher_cut -= owner.owner_network_cut

                    # Handle exceptions for Publisher Network owner
                    if data_exceptions:
                        data_exceptions = cuts.rules_exceptions
                        for data in data_exceptions:
                            if data['sid'] == user.id:
                                publisher_cut = 1 - decimal.Decimal(data['tribute'])
            except:
                pass
    except get_user_model().DoesNotExist:
        pass

    return user, normal_cut, referral_cut, publisher_cut