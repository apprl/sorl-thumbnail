# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from decimal import Decimal as D
from decimal import *

from dateutil.relativedelta import relativedelta
from django.db.models import Sum

from apparelrow.apparel.utils import currency_exchange
from apparelrow.dashboard.models import UserEarning, UE, Sale, Payment
from apparelrow.dashboard.stats.stats_admin import ppo_vendors, ppc_vendors
from apparelrow.dashboard.stats.stats_cache import stats_cache, mrange, flush_stats_cache, all_time
from apparelrow.profile.models import User
from apparelrow.statistics.models import ProductStat

logger = logging.getLogger(__name__)


@stats_cache
def total_earnings(time_range, user_id):
    return ppo_earnings(time_range, user_id) + \
           ppc_earnings(time_range, user_id) + \
           network_earnings(time_range, user_id) + \
           other_earnings(time_range, user_id)

####################################################
# PPO
####################################################

@stats_cache
def ppo_earnings(time_range, user_id):
    result = UserEarning.objects.filter(
        date__range=time_range,
        user_id=user_id,
        status__gte=Sale.PENDING,
        user_earning_type=UE.PUBLISHER_SALE_COMMISSION,
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_cache
def ppo_sales(time_range, user_id):
    return Sale.objects.filter(
        sale_date__range=time_range,
        user_id=user_id,
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_ORDER,
        is_promo=False,
    ).count()


@stats_cache
def ppo_clicks(time_range, user_id):
    return ProductStat.objects.filter(
        created__range=time_range,
        user_id=user_id,
        vendor__in=ppo_vendors(),
        is_valid=True
    ).count()


@stats_cache
def ppo_conversion_rate(time_range, user_id):
    clicks = ppo_clicks(time_range, user_id)
    if clicks:
        getcontext().prec = 4
        return D(100) * D(ppo_sales(time_range, user_id) / clicks)
    else:
        return 0


####################################################
# PPC
####################################################

@stats_cache
def ppc_earnings(time_range, user_id):
    # This should work regardless if the user is ppc_as, because if the user is given a ppc_as commission,
    # any click commission will be 0

    result = UserEarning.objects.filter(
        date__range=time_range,
        user_id=user_id,
        status__gte=Sale.PENDING,
        user_earning_type__in=(
            UE.PUBLISHER_SALE_CLICK_COMMISSION,
            UE.PUBLISHER_SALE_CLICK_COMMISSION_ALL_STORES,
        )
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_cache
def ppc_clicks(time_range, user_id):
    return ProductStat.objects.filter(
        created__range=time_range,
        user_id=user_id,
        vendor__in=ppc_vendors(),
        is_valid=True
    ).count()


####################################################
# Network & Other
####################################################

@stats_cache
def network_earnings(time_range, user_id):
    result = UserEarning.objects.filter(
        date__range=time_range,
        user_id=user_id,
        status__gte=Sale.PENDING,
        user_earning_type__in=(
            UE.PUBLISHER_NETWORK_TRIBUTE,
            UE.PUBLISHER_NETWORK_CLICK_TRIBUTE,
            UE.PUBLISHER_NETWORK_CLICK_TRIBUTE_ALL_STORES,
        )
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_cache
def other_earnings(time_range, user_id):
    result = UserEarning.objects.filter(
        date__range=time_range,
        user_id=user_id,
        status__gte=Sale.PENDING,
    ).exclude(
        user_earning_type__in=(
            UE.PUBLISHER_SALE_COMMISSION,

            UE.PUBLISHER_SALE_CLICK_COMMISSION,
            UE.PUBLISHER_SALE_CLICK_COMMISSION_ALL_STORES,

            UE.PUBLISHER_NETWORK_TRIBUTE,
            UE.PUBLISHER_NETWORK_CLICK_TRIBUTE,
            UE.PUBLISHER_NETWORK_CLICK_TRIBUTE_ALL_STORES,
        )
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


####################################################
# Referral earnings
####################################################


@stats_cache
def referral_earnings(time_range, user_id):
    result = referral_earnings_query(time_range, user_id).aggregate(total=Sum('amount'))
    return result['total'] or 0


@stats_cache
def referral_sales(time_range, user_id):
    return referral_earnings_query(time_range, user_id).count()


def referral_earnings_query(time_range, user_id):
    return UserEarning.objects.filter(
        user_id=user_id,
        date__range=time_range,
        status__gte=Sale.PENDING,
        user_earning_type__in=(
            UE.REFERRAL_SIGNUP_COMMISSION,
            UE.REFERRAL_SALE_COMMISSION
        )
    )


####################################################
# Payments
####################################################

def pending_earnings(user_id):
    result = UserEarning.objects.filter(
        user_id=user_id,
        status=Sale.PENDING,
        paid=Sale.PAID_PENDING
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


def confirmed_earnings(user_id):
    result = UserEarning.objects.filter(
        user_id=user_id,
        status=Sale.CONFIRMED,
        paid=Sale.PAID_PENDING
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


def pending_payments(user_id):
    payments = Payment.objects.filter(cancelled=False, paid=False, user_id=user_id)
    if payments:
        if len(payments) > 1:
            log.warn("A user shouldn't have more than one pending payment. User: %d" % user_id)
            return sum(p.amount for p in payments)
        else:
            return payments[0].amount
    else:
        return 0


def total_paid(user_id):
    total = 0
    payments = Payment.objects.filter(paid=True, user_id=user_id, cancelled=False)
    for pay in payments:
        rate = 1 if pay.currency == 'EUR' else currency_exchange('EUR', pay.currency)
        total += pay.amount * rate
    return total

def total_paid_via_user_earnings(user_id):
    result = UserEarning.objects.filter(
        date__range=all_time,
        user_id=user_id,
        paid=Sale.PAID_COMPLETE
    ).aggregate(
        total=Sum('amount')
    )

    return result['total'] or 0


# NOTE: don't cache this function, it uses current time
def old_user_earnings_still_marked_as_paid_ready(user_id, months_back=0):
    d = datetime.now() - relativedelta(months=months_back)
    result = UserEarning.objects.filter(
        date__range=[all_time[0], d],
        user_id=user_id,
        paid=Sale.PAID_READY
    ).aggregate(
        total=Sum('amount')
    )

    return result['total'] or 0

####################################################
# CLI
####################################################

def print_publisher_stats(user_id, flush_cache=True):
    print publisher_stats_as_str(user_id, flush_cache)

def publisher_stats_as_str(user_id, flush_cache=True):
    from tabulate import tabulate       # install it if you want to run this function
    user = User.objects.get(id=user_id)

    str = u"\n"
    str += u"Publisher stats for {} ({})\n".format(user, user_id)

    if flush_cache:
        flush_stats_cache()

    stats = []

    d = datetime(user.date_joined.year, user.date_joined.month, 1)
    while d < datetime.now():
        tr = mrange(d.year, d.month)
        stats.append([
            d.strftime('%Y %m'),
            ppo_earnings(tr, user_id),
            ppc_earnings(tr, user_id),
            network_earnings(tr, user_id),
            other_earnings(tr, user_id),
            total_earnings(tr, user_id)
        ])
        d += relativedelta(months=1)

    stats.append(['', '', '', '', '', '=============='])
    stats.append(['', '', '', '', '', total_earnings(all_time, user_id)])

    str += u"\n"
    str += tabulate(stats, headers=["Earnings",
                                   "PPO",
                                   "PPC",
                                   "Network",
                                   "Other",
                                   "Total",
                                   ""], numalign="right")

    paid_or_about_to_be_paid = total_paid(user_id) + pending_payments(user_id) + confirmed_earnings(user_id) + pending_earnings(user_id)

    str += u"\n\n"
    str += u"Paid or about to be paid\n"
    str += u"----------------------------------------\n"
    str += tabulate([
        ["Total paid", total_paid(user_id)],
        ["Pending payments", pending_payments(user_id)],
        ["Not yet paid confirmed earnings", confirmed_earnings(user_id)],
        ["Not yet paid pending earnings", pending_earnings(user_id)],
        ["", "============"],
        ["", paid_or_about_to_be_paid]
    ], numalign="right", tablefmt='plain')

    earnings = total_earnings(all_time, user_id)
    diff = paid_or_about_to_be_paid - earnings

    str += u"\n\n"
    if diff:
        str += u"WARNING: Payments ({}) does not equal earnings ({}). Diff: ({})\n".format(
            paid_or_about_to_be_paid, earnings, diff
        )
    else:
        str += u"OK. Payouts equal earnings.\n"

    return str

