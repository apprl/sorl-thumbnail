# -*- coding: utf-8 -*-

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum

from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.models import Sale, UserEarning, UE
from apparelrow.dashboard.stats.stats_cache import flush_stats_cache_by_month, stats_cache, mrange
from apparelrow.statistics.models import ProductStat

log = logging.getLogger(__name__)


####################################################
# Earnings
#
####################################################


@stats_cache
def earnings_total(time_range):
    return ppo_commission_total(time_range) + ppc_commission_total(time_range)

    # This can also be calculated this way. I keep it here for reference:
    # result = Sale.objects.filter(
    #     sale_date__range=mrange(year, month),
    #     status__gte=Sale.PENDING,
    #     is_promo=False,                 # Promotions aren't Apprl incomes
    # ).exclude(
    #     affiliate='cpc_all_stores',
    # ).aggregate(
    #     total=Sum('converted_commission')
    # )
    # return result['total'] or 0


@stats_cache
def earnings_publisher(time_range):
    result = UserEarning.objects.filter(
        date__range=time_range,
        status__gte=Sale.PENDING,
        user_id__gt=0,
    ).exclude(
        user_earning_type__in=(
            UE.REFERRAL_SIGNUP_COMMISSION,
            UE.REFERRAL_SALE_COMMISSION
        ),
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_cache
def earnings_apprl(time_range):
    return earnings_total(time_range) - earnings_publisher(time_range)


####################################################
# Referral earnings
####################################################


@stats_cache
def referral_earnings_total(time_range):
    return 0


@stats_cache
def referral_earnings_publisher(time_range):
    result = UserEarning.objects.filter(
        date__range=time_range,
        status__gte=Sale.PENDING,
        user_earning_type__in=(
            UE.REFERRAL_SIGNUP_COMMISSION,
            UE.REFERRAL_SALE_COMMISSION
        )
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_cache
def referral_earnings_apprl(time_range):
    return -1 * referral_earnings_publisher(time_range)


####################################################
# PPO Commission
####################################################


@stats_cache
def ppo_commission_total(time_range):
    result = Sale.objects.filter(
        sale_date__range=time_range,
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_ORDER,
        is_promo=False,
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total'] or 0


@stats_cache
def ppo_commission_publisher(time_range):
    return 0


@stats_cache
def ppo_commission_apprl(time_range):
    return 0


####################################################
# PPC Commission
####################################################


@stats_cache
def ppc_commission_total(time_range):
    result = Sale.objects.filter(
        sale_date__range=time_range,
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_CLICK,
        is_promo=False,
        vendor__in=ppc_vendors('id')
    ).exclude(
        affiliate='cpc_all_stores'
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total'] or 0


@stats_cache
def ppc_commission_publisher(time_range):
    return 0


@stats_cache
def ppc_commission_apprl(time_range):
    return 0


####################################################
# PPC Clicks
####################################################


@stats_cache
def ppc_clicks_total(time_range):
    return ppc_clicks_publisher(time_range) + ppc_clicks_apprl(time_range)


@stats_cache
def ppc_clicks_publisher(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppc_vendors()
    ).exclude(
        user_id=0
    ).count()


@stats_cache
def ppc_clicks_apprl(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppc_vendors(),
        user_id=0
    ).count()


####################################################
# PPO Clicks
####################################################


@stats_cache
def ppo_clicks_total(time_range):
    return ppo_clicks_publisher(time_range) + ppo_clicks_apprl(time_range)


@stats_cache
def ppo_clicks_publisher(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppo_vendors(),
        user_id__gt=0
    ).count()


@stats_cache
def ppo_clicks_apprl(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppo_vendors(),
        user_id=0
    ).count()


####################################################
# PPO Sales
####################################################


@stats_cache
def ppo_sales_total(time_range):
    return ppo_sales_publisher(time_range) + ppo_sales_apprl(time_range)


@stats_cache
def ppo_sales_publisher(time_range):
    return Sale.objects.filter(
        sale_date__range=time_range,
        status__gte=Sale.PENDING,
        vendor__in=ppo_vendors('id'),
        type=Sale.COST_PER_ORDER,
        is_promo=False,
        user_id__gt=0
    ).count()


@stats_cache
def ppo_sales_apprl(time_range):
    return Sale.objects.filter(
        sale_date__range=time_range,
        vendor__in=ppo_vendors('id'),
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_ORDER,
        user_id=0
    ).count()


####################################################
# Commission CR
####################################################


@stats_cache
def commission_cr_total(time_range):
    clicks = ppo_clicks_total(time_range)
    if clicks:
        return Decimal(ppo_sales_total(time_range)) / clicks
    else:
        return 0


@stats_cache
def commission_cr_publisher(time_range):
    clicks = ppo_clicks_publisher(time_range)
    if clicks:
        return Decimal(ppo_sales_publisher(time_range)) / clicks
    else:
        return 0


@stats_cache
def commission_cr_apprl(time_range):
    clicks = ppo_clicks_apprl(time_range)
    if clicks:
        return Decimal(ppo_sales_apprl(time_range)) / clicks
    else:
        return 0


####################################################
# Average EPC
####################################################


@stats_cache
def average_epc_total(time_range):
    clicks = ppc_clicks_total(time_range) + ppo_clicks_total(time_range)
    if clicks:
        return Decimal(ppo_commission_total(time_range) + ppc_commission_total(time_range)) / clicks
    else:
        return 0


@stats_cache
def average_epc_ppc(time_range):
    clicks = ppc_clicks_total(time_range)
    if clicks:
        return Decimal(ppc_commission_total(time_range)) / clicks
    else:
        return 0


@stats_cache
def average_epc_ppo(time_range):
    clicks = ppo_clicks_total(time_range)
    if clicks:
        return Decimal(ppo_commission_total(time_range)) / clicks
    else:
        return 0


####################################################
# Valid clicks
####################################################


@stats_cache
def valid_clicks_total(time_range):
    return valid_clicks_ppc(time_range) + valid_clicks_ppo(time_range)


@stats_cache
def valid_clicks_ppc(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppc_vendors(),
        is_valid=True
    ).count()


@stats_cache
def valid_clicks_ppo(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppo_vendors(),
        is_valid=True
    ).count()


####################################################
# Invalid clicks
####################################################


@stats_cache
def invalid_clicks_total(time_range):
    return invalid_clicks_ppc(time_range) + invalid_clicks_ppo(time_range)


@stats_cache
def invalid_clicks_ppc(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppc_vendors(),
        is_valid=False
    ).count()


@stats_cache
def invalid_clicks_ppo(time_range):
    return ProductStat.objects.filter(
        created__range=time_range,
        vendor__in=ppo_vendors(),
        is_valid=False
    ).count()


####################################################
# PPC all stores publishers
####################################################


@stats_cache
def ppc_all_stores_publishers_income(time_range):
    result = Sale.objects.filter(
        sale_date__range=time_range,
        status__gte=Sale.PENDING,
        user_id__in=ppc_all_stores_users(),
        is_promo=False,
    ).exclude(
        affiliate='cpc_all_stores',
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total'] or 0


@stats_cache
def ppc_all_stores_publishers_cost(time_range):
    result = Sale.objects.filter(
        sale_date__range=time_range,
        status__gte=Sale.PENDING,
        is_promo=False,
        affiliate='cpc_all_stores',
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total'] or 0


@stats_cache
def ppc_all_stores_publishers_result(time_range):
    income = ppc_all_stores_publishers_income(time_range)
    cost = ppc_all_stores_publishers_cost(time_range)
    return income - cost


@stats_cache
def ppc_all_stores_publishers_by_vendor(time_range):
    ppc_as_users = ppc_all_stores_users()
    stats = {}
    for vendor in Vendor.objects.all():
        res = Sale.objects.filter(
            vendor=vendor,
            sale_date__range=time_range,
            status__gte=Sale.PENDING,
            is_promo=False,
            user_id__in=ppc_as_users
        ).exclude(
            affiliate='cpc_all_stores'
        ).aggregate(
            total=Sum('converted_commission')
        )
        income = res['total'] or 0

        res = Sale.objects.filter(
            vendor=vendor,
            sale_date__range=time_range,
            status__gte=Sale.PENDING,
            is_promo=False,
            affiliate='cpc_all_stores'
        ).aggregate(
            total=Sum('converted_commission')
        )
        cost = res['total'] or 0
        stats[vendor.name] = {'income': income, 'cost': cost, 'result': income - cost, 'ppo': vendor.is_cpo, 'ppc': vendor.is_cpc}
    return stats

####################################################
# Misc internal utils
####################################################


def ppc_all_stores_users():
    return get_user_model().objects.filter(is_partner=True, partner_group__has_cpc_all_stores=True).values_list('id', flat=True)


# NOTE: We assume that is_cpc and is_cpo is mutually exclusive. If this changes in the future, ie. if a Vendor
# is both cpc and cpo - this code will have to be changed
def ppc_vendors(key='name'):
    return Vendor.objects.filter(is_cpc=True, is_cpo=False).values_list(key, flat=True)


def ppo_vendors(key='name'):
    return Vendor.objects.filter(is_cpc=False, is_cpo=True).values_list(key, flat=True)


####################################################
# Used by admin dashboards
####################################################


def admin_top_stats(year, month, flush_cache=False):

    if flush_cache:
        flush_stats_cache_by_month(year, month)

    tr = mrange(year, month)
    return [
        [
            "Earnings",
            earnings_total(tr), earnings_publisher(tr), earnings_apprl(tr)
        ],
        [
            "Referral earnings",
            referral_earnings_total(tr), referral_earnings_publisher(tr), referral_earnings_apprl(tr)
        ],
        [
            "PPO commission",
            ppo_commission_total(tr), ppo_commission_publisher(tr), ppo_commission_apprl(tr)
        ],
        [
            "PPC commission",
            ppc_commission_total(tr), ppc_commission_publisher(tr), ppc_commission_apprl(tr)
        ],
        [
            "PPC clicks",
            ppc_clicks_total(tr), ppc_clicks_publisher(tr), ppc_clicks_apprl(tr)
        ],
        [
            "PPO clicks",
            ppo_clicks_total(tr), ppo_clicks_publisher(tr), ppo_clicks_apprl(tr)
        ],
        [
            "PPO sales",
            ppo_sales_total(tr), ppo_sales_publisher(tr), ppo_sales_apprl(tr)
        ],
        [
            "Commission CR",
            commission_cr_total(tr), commission_cr_publisher(tr), commission_cr_apprl(tr)
        ]
    ]


def admin_clicks(year, month, flush_cache=False):

    if flush_cache:
        flush_stats_cache_by_month(year, month)

    tr = mrange(year, month)
    return [
        [
            "Average EPC",
            average_epc_total(tr), average_epc_ppc(tr), average_epc_ppo(tr)
        ],
        [
            "Valid clicks",
            valid_clicks_total(tr), valid_clicks_ppc(tr), valid_clicks_ppo(tr)
        ],
        [
            "Invalid clicks",
            invalid_clicks_total(tr), invalid_clicks_ppc(tr), invalid_clicks_ppo(tr)
        ]
    ]


def ppc_all_stores_stats(year, month, flush_cache=False):
    if flush_cache:
        flush_stats_cache_by_month(year, month)

    tr = mrange(year, month)
    return {
        'total': {
            'result': ppc_all_stores_publishers_result(tr),
            'income': ppc_all_stores_publishers_income(tr),
            'cost': ppc_all_stores_publishers_cost(tr),
        },
        'by_vendor': ppc_all_stores_publishers_by_vendor(tr)
    }


####################################################
# CLI functions
####################################################

def print_admin_dashboard(year, month, flush_cache=True):
    from tabulate import tabulate       # install it if you want to run this function

    print ""
    print "Admin stats for {} {}".format(year, month)

    print ""
    print tabulate(admin_top_stats(year, month, flush_cache), headers=["Top", "Total", "Publisher", "Apprl"], numalign="right")

    print ""
    print tabulate(admin_clicks(year, month, flush_cache), headers=["Clicks", "Total", "PPC", "PPO"], numalign="right")
    ppc_stats = ppc_all_stores_stats(year, month, flush_cache)

    print ""
    print "PPC all stores publishers - only looking att PPO vendors"
    print "Total {} = Income {} - Cost {}".format(ppc_stats[0], ppc_stats[1], ppc_stats[2])


def print_non_paid_publishers():
    d = datetime.now() - relativedelta(months=3)
    earnings_per_user = defaultdict(int)
    print 'All users that have earnings marked as PAID_READY earlier than %s' % d
    total = 0
    for earning in UserEarning.objects.filter(
        status__gte=Sale.CONFIRMED,
        paid=Sale.PAID_READY,
        user__id__gt=0,
        date__lt=d).iterator():
        u = '%s (%d)' % (earning.user, earning.user_id)
        earnings_per_user[u] += earning.amount
        total += earning.amount
    print '\n'.join('%s: %s' % u for u in sorted(earnings_per_user.items(), key=lambda v: -v[1]))
    print '======================'
    print 'Total: %s' % total




def print_sanity_check(year, month):
    total_sales = 0
    total_earnings = 0
    for s in Sale.objects.filter(created__range=mrange(year, month)):
        total_sales += s.converted_commission
        for u in s.userearning_set.all():
            total_earnings += u.amount
    print "Total sales for %s %s: %s. Total earnings: %s. Diff: %s" % (year, month, total_sales, total_earnings, (total_earnings - total_sales))



# from django.db import connections
# print connections['default'].queries
