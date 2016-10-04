# -*- coding: utf-8 -*-

from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum

from apparelrow.apparel.models import Vendor
from apparelrow.dashboard.models import Sale, UserEarning
from apparelrow.dashboard.stats_cache import stats_month_cache, flush_stats_cache_by_one_month
from apparelrow.statistics.models import ProductStat

import logging
log = logging.getLogger(__name__)


####################################################
# Earnings
#
####################################################


@stats_month_cache
def earnings_total(year, month):
    return ppo_commission_total(year, month) + ppc_commission_total(year, month)

    # This can also be calculated this way. I keep it here for reference:
    # result = Sale.objects.filter(
    #     sale_date__range=month_range(year, month),
    #     status__gte=Sale.PENDING,
    #     is_promo=False,                 # Promotions aren't Apprl incomes
    # ).exclude(
    #     affiliate='cpc_all_stores',
    # ).aggregate(
    #     total=Sum('converted_commission')
    # )
    # return result['total'] or 0


@stats_month_cache
def earnings_publisher(year, month):
    result = UserEarning.objects.filter(
        date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        user_id__gt=0,
    ).exclude(
        user_earning_type__in=(
            'referral_signup_commission',   # we don't count them here, we calculated them separately in referral earnings
            'referral_sale_commission'
        ),
    ).aggregate(
        total=Sum('amount')
    )
    return result['total'] or 0


@stats_month_cache
def earnings_apprl(year, month):
    return earnings_total(year, month) - earnings_publisher(year, month)


####################################################
# Referral earnings
####################################################


@stats_month_cache
def referral_earnings_total(year, month):
    return 0


@stats_month_cache
def referral_earnings_publisher(year, month):
    result = UserEarning.objects.filter(
        date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        user_earning_type__in=(
            'referral_signup_commission',
            'referral_sale_commission'
        )
    ).aggregate(
        total=Sum('amount')
    )
    return result['total']


@stats_month_cache
def referral_earnings_apprl(year, month):
    return -1 * referral_earnings_publisher(year, month)


####################################################
# PPO Commission
####################################################


@stats_month_cache
def ppo_commission_total(year, month):
    result = Sale.objects.filter(
        sale_date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_ORDER,
        is_promo=False,
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total']


@stats_month_cache
def ppo_commission_publisher(year, month):
    return 0


@stats_month_cache
def ppo_commission_apprl(year, month):
    return 0


####################################################
# PPC Commission
####################################################


@stats_month_cache
def ppc_commission_total(year, month):
    result = Sale.objects.filter(
        sale_date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_CLICK,
        is_promo=False,
        vendor__in=ppc_vendors('id')
    ).exclude(
        affiliate='cpc_all_stores'
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total']


@stats_month_cache
def ppc_commission_publisher(year, month):
    return 0


@stats_month_cache
def ppc_commission_apprl(year, month):
    return 0


####################################################
# PPC Clicks
####################################################


@stats_month_cache
def ppc_clicks_total(year, month):
    return ppc_clicks_publisher(year, month) + ppc_clicks_apprl(year, month)


@stats_month_cache
def ppc_clicks_publisher(year, month):
    # print 'aaaaaaaaa'
    # print ppc_vendors()
    # print str(ProductStat.objects.filter(
    #     created__range=month_range(year, month),
    #     vendor__in=ppc_vendors()
    # ).query)

    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppc_vendors()
    ).exclude(
        user_id=0
    ).count()


@stats_month_cache
def ppc_clicks_apprl(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppc_vendors(),
        user_id=0
    ).count()




####################################################
# PPO Clicks
####################################################


@stats_month_cache
def ppo_clicks_total(year, month):
    return ppo_clicks_publisher(year, month) + ppo_clicks_apprl(year, month)


@stats_month_cache
def ppo_clicks_publisher(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppo_vendors(),
        user_id__gt=0
    ).count()


@stats_month_cache
def ppo_clicks_apprl(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppo_vendors(),
        user_id=0
    ).count()




####################################################
# PPO Sales
####################################################


@stats_month_cache
def ppo_sales_total(year, month):
    return ppo_sales_publisher(year, month) + ppo_sales_apprl(year, month)


@stats_month_cache
def ppo_sales_publisher(year, month):
    return Sale.objects.filter(
        sale_date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        vendor__in=ppo_vendors('id'),
        type=Sale.COST_PER_ORDER,
        is_promo=False,
        user_id__gt=0
    ).count()


@stats_month_cache
def ppo_sales_apprl(year, month):
    return Sale.objects.filter(
        sale_date__range=month_range(year, month),
        vendor__in=ppo_vendors('id'),
        status__gte=Sale.PENDING,
        type=Sale.COST_PER_ORDER,
        user_id=0
    ).count()


####################################################
# Commission CR
####################################################


@stats_month_cache
def commission_cr_total(year, month):
    clicks = ppo_clicks_total(year, month)
    if clicks:
        return Decimal(ppo_sales_total(year, month)) / clicks
    else:
        return 0


@stats_month_cache
def commission_cr_publisher(year, month):
    clicks = ppo_clicks_publisher(year, month)
    if clicks:
        return Decimal(ppo_sales_publisher(year, month)) / clicks
    else:
        return 0


@stats_month_cache
def commission_cr_apprl(year, month):
    clicks = ppo_clicks_apprl(year, month)
    if clicks:
        return Decimal(ppo_sales_apprl(year, month)) / clicks
    else:
        return 0


####################################################
# Average EPC
####################################################

@stats_month_cache
def average_epc_total(year, month):
    clicks = ppc_clicks_total(year, month) + ppo_clicks_total(year, month)
    if clicks:
        return Decimal(ppo_commission_total(year, month) + ppc_commission_total(year, month)) / clicks


@stats_month_cache
def average_epc_ppc(year, month):
    clicks = ppc_clicks_total(year, month)
    if clicks:
        return Decimal(ppc_commission_total(year, month)) / clicks
    else:
        return 0


@stats_month_cache
def average_epc_ppo(year, month):
    clicks = ppo_clicks_total(year, month)
    if clicks:
        return Decimal(ppo_commission_total(year, month)) / clicks
    else:
        return 0


####################################################
# Valid clicks
####################################################


@stats_month_cache
def valid_clicks_total(year, month):
    return valid_clicks_ppc(year, month) + valid_clicks_ppo(year, month)


@stats_month_cache
def valid_clicks_ppc(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppc_vendors(),
        is_valid=True
    ).count()


@stats_month_cache
def valid_clicks_ppo(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppo_vendors(),
        is_valid=True
    ).count()


####################################################
# Invalid clicks
####################################################


@stats_month_cache
def invalid_clicks_total(year, month):
    return invalid_clicks_ppc(year, month) + invalid_clicks_ppo(year, month)


@stats_month_cache
def invalid_clicks_ppc(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppc_vendors(),
        is_valid=False
    ).count()


@stats_month_cache
def invalid_clicks_ppo(year, month):
    return ProductStat.objects.filter(
        created__range=month_range(year, month),
        vendor__in=ppo_vendors(),
        is_valid=False
    ).count()


####################################################
# PPC all stores publishers
####################################################



@stats_month_cache
def ppc_all_stores_publishers_income(year, month):
    # We define this to be what we receive from PPO vendors from traffic driven by PPC-AS-publishers. They don't get
    # a cut from this incomes.
    result = Sale.objects.filter(
        sale_date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        vendor_id__in=ppo_vendors('id'),
        user_id__in=ppc_all_stores_users(),
        is_promo=False,
        type=Sale.COST_PER_ORDER
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total']


@stats_month_cache
def ppc_all_stores_publishers_cost(year, month):
    # We define this to be what we pay to PPC-AS-publishers because of clicks to PPO vendors. No income to Apprl
    # on these Sales, only costs
    result = Sale.objects.filter(
        sale_date__range=month_range(year, month),
        status__gte=Sale.PENDING,
        vendor_id__in=ppo_vendors('id'),
        user_id__in=ppc_all_stores_users(),
        is_promo=False,
        type=Sale.COST_PER_CLICK
    ).aggregate(
        total=Sum('converted_commission')
    )
    return result['total']


@stats_month_cache
def ppc_all_stores_publishers_result(year, month):
    income = ppc_all_stores_publishers_income(year, month)
    cost = ppc_all_stores_publishers_cost(year, month)
    return income - cost


####################################################
# Misc internal utils
####################################################


def month_range(year, month):
    start = datetime(year, month, 1)
    # Djangos range filter maps to BETWEEN which is inclusive so we need to subract a small amount so we stay within the month
    end = start + relativedelta(months=1) - relativedelta(microseconds=1)
    return start, end


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
        flush_stats_cache_by_one_month(year, month)

    return [
        [
            "Earnings",
            earnings_total(year, month), earnings_publisher(year, month), earnings_apprl(year, month)
        ],
        [
            "Referral earnings",
            referral_earnings_total(year, month), referral_earnings_publisher(year, month), referral_earnings_apprl(year, month)
        ],
        [
            "PPO commission",
            ppo_commission_total(year, month), ppo_commission_publisher(year, month), ppo_commission_apprl(year, month)
        ],
        [
            "PPC commission",
            ppc_commission_total(year, month), ppc_commission_publisher(year, month), ppc_commission_apprl(year, month)
        ],
        [
            "PPC clicks",
            ppc_clicks_total(year, month), ppc_clicks_publisher(year, month), ppc_clicks_apprl(year, month)
        ],
        [
            "PPO clicks",
            ppo_clicks_total(year, month), ppo_clicks_publisher(year, month), ppo_clicks_apprl(year, month)
        ],
        [
            "PPO sales",
            ppo_sales_total(year, month), ppo_sales_publisher(year, month), ppo_sales_apprl(year, month)
        ],
        [
            "Commission CR",
            commission_cr_total(year, month), commission_cr_publisher(year, month), commission_cr_apprl(year, month)
        ]
    ]


def admin_clicks(year, month, flush_cache=False):

    if flush_cache:
        flush_stats_cache_by_one_month(year, month)

    return [
        [
            "Average EPC",
            average_epc_total(year, month), average_epc_ppc(year, month), average_epc_ppo(year, month)
        ],
        [
            "Valid clicks",
            valid_clicks_total(year, month), valid_clicks_ppc(year, month), valid_clicks_ppo(year, month)
        ],
        [
            "Invalid clicks",
            invalid_clicks_total(year, month), invalid_clicks_ppc(year, month), invalid_clicks_ppo(year, month)
        ]
    ]


def ppc_all_stores_stats(year, month, flush_cache=False):
    if flush_cache:
        flush_stats_cache_by_one_month(year, month)

    return (
        ppc_all_stores_publishers_result(year, month),
        ppc_all_stores_publishers_income(year, month),
        ppc_all_stores_publishers_cost(year, month),
    )


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


def print_sanity_check(year, month):
    total_sales = 0
    total_earnings = 0
    for s in Sale.objects.filter(created__range=month_range(year, month)):
        total_sales += s.converted_commission
        for u in s.userearning_set.all():
            total_earnings += u.amount
    print "Total sales for %s %s: %s. Total earnings: %s. Diff: %s" % (year, month, total_sales, total_earnings, (total_earnings - total_sales))



# from django.db import connections
# print connections['default'].queries
