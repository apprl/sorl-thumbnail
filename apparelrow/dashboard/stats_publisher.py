# -*- coding: utf-8 -*-

import logging

from dateutil.relativedelta import relativedelta
from django.db.models import Sum

from apparelrow.apparel.utils import currency_exchange
from apparelrow.dashboard.models import UserEarning, UE, Sale, Payment
from apparelrow.dashboard.stats_cache import stats_cache, mrange, flush_stats_cache, all_time
from apparelrow.profile.models import User
from apparelrow.statistics.models import ProductStat
from apparelrow.dashboard.stats_admin import ppo_vendors, ppc_vendors
from datetime import datetime

log = logging.getLogger(__name__)


@stats_cache
def total_earnings(time_range, user_id):
    return ppo_earnings(time_range, user_id) + ppc_earnings(time_range, user_id)

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
            raise Exception("A user shouldn't have more than one pending payment")
        else:
            return payments[0].amount
    else:
        return 0


def total_paid(user_id):
    total = 0
    payments = Payment.objects.filter(paid=True, user_id=user_id)   # TODO: this should check cancelled condition, change after db migrations
    for pay in payments:
        rate = 1 if pay.currency == 'EUR' else currency_exchange('EUR', pay.currency)
        total += pay.amount * rate
    return total



####################################################
# CLI
####################################################

def print_publisher_dashboard(year, month, user_id, flush_cache=True, months_back=3):
    from tabulate import tabulate       # install it if you want to run this function

    print ""
    print "Publisher stats for {} ({})".format(User.objects.get(id=user_id), user_id)

    if flush_cache:
        flush_stats_cache()

    stats = []
    for m in range(0, months_back):
        d = datetime(year, month, 1) - relativedelta(months=m)
        tr = mrange(d.year, d.month)
        stats.append([
            d.strftime('%Y %m'),
            ppo_earnings(tr, user_id),
            ppc_earnings(tr, user_id),
            total_earnings(tr, user_id)
        ])

    stats.reverse()

    print ""
    print tabulate(stats, headers=["Earnings",
                                   "PPO",
                                   "PPC",
                                   "Total",
                                   ""], numalign="right")
    print ""
    print "Paid or about to be paid"
    print "------------------------"
    print "Total paid: {}".format(total_paid(user_id))
    print "Pending payments: {}".format(pending_payments(user_id))
    print "Confirmed earnings: {}".format(confirmed_earnings(user_id))
    print "Pending earnings: {}".format(pending_earnings(user_id))

    paid_or_about_to_be_paid = total_paid(user_id) + pending_payments(user_id) + confirmed_earnings(user_id) + pending_earnings(user_id)
    earnings = total_earnings(all_time, user_id)
    diff = paid_or_about_to_be_paid - earnings
    if diff:
        print ""
        print "Payments ({}) does not equal total earnings ({}). Diff: ({})".format(
            paid_or_about_to_be_paid, earnings, diff
        )
        # print "WARNING. Total earnings ({}) does not add up to total paid ({}) + pending payments ({}) + confirmed earnings ({}) + pending_earnings ({}). Diff: ({})".format(
        #     a, total_paid(user_id), pending_payments(user_id), confirmed_earnings(user_id), pending_earnings(user_id), diff
        # )
    else:
        print ""
        print "OK. Payouts equal earnings."

