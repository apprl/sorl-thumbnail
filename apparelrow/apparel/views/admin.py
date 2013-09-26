# -*- coding: utf-8 -*-
import datetime
import decimal
import calendar

from django.conf import settings
from django.shortcuts import render
from django.db.models import Sum, Q
from django.db.models.loading import get_model
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.http import Http404

from dateutil.relativedelta import relativedelta


ZERO_DECIMAL = decimal.Decimal('0.00')


def week_magic(day):
    day_of_week = day.weekday()

    to_beginning_of_week = datetime.timedelta(days=day_of_week)
    beginning_of_week = day - to_beginning_of_week

    to_end_of_week = datetime.timedelta(days=6 - day_of_week)
    end_of_week = day + to_end_of_week

    return (beginning_of_week.replace(hour=0, minute=0, second=0, microsecond=0),
            end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999))


def month_magic(d):
    _, end_day = calendar.monthrange(d.year, d.month)

    return (d.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            d.replace(day=end_day, hour=23, minute=59, second=59, microsecond=999999))


def get_date_interval(is_month, date, last=False):
    if not is_month:
        if last:
            return week_magic(date - datetime.timedelta(days=7))

        return week_magic(date)

    if last:
        return month_magic(date - relativedelta(months=1))

    return month_magic(date)


def kpi_dashboard(request):
    if request.user.is_authenticated() and request.user.is_superuser:
        decimal.setcontext(decimal.ExtendedContext)

        # Models
        ProductStat = get_model('statistics', 'ProductStat')
        Sale = get_model('dashboard', 'Sale')

        # Date
        is_month = bool(request.GET.get('month', None))
        date = request.GET.get('date')
        if date:
            date = datetime.datetime(*[int(x) for x in date.split('-')])
        else:
            date = datetime.datetime.now()

        col1_start, col1_end = get_date_interval(is_month, date, last=False)
        col3_start, col3_end = get_date_interval(is_month, date, last=True)

        context = {'is_month': is_month}

        context['col1_week_start'] = col1_start
        context['col1_week_end'] = col1_end
        context['col3_week_start'] = col3_start
        context['col3_week_end'] = col3_end

        # Sales value selected week
        col1_base_sales_query = Sale.objects.filter(created__range=(col1_start, col1_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
        context['col1_total_sale'] = col1_base_sales_query.aggregate(Sum('converted_amount')).get('converted_amount__sum') or ZERO_DECIMAL
        context['col1_publisher_sale'] = col1_base_sales_query.filter(user_id__isnull=False, user_id__gt=0).aggregate(Sum('converted_amount')).get('converted_amount__sum') or ZERO_DECIMAL
        context['col1_apprl_sale'] = context['col1_total_sale'] - context['col1_publisher_sale']

        # Sales value last week
        col3_base_sales_query = Sale.objects.filter(created__range=(col3_start, col3_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
        context['col3_total_sale'] = col3_base_sales_query.aggregate(Sum('converted_amount')).get('converted_amount__sum') or ZERO_DECIMAL
        context['col3_publisher_sale'] = col3_base_sales_query.filter(user_id__isnull=False, user_id__gt=0).aggregate(Sum('converted_amount')).get('converted_amount__sum') or ZERO_DECIMAL
        context['col3_apprl_sale'] = context['col3_total_sale'] - context['col3_publisher_sale']

        # Sales values changes
        context['col2_total_sale'] = (context['col1_total_sale'] - context['col3_total_sale']) / context['col3_total_sale'] * 100
        context['col2_apprl_sale'] = (context['col1_apprl_sale'] - context['col3_apprl_sale']) / context['col3_apprl_sale'] * 100
        context['col2_publisher_sale'] = (context['col1_publisher_sale'] - context['col3_publisher_sale']) / context['col3_publisher_sale'] * 100

        # Commission value selected week
        col1_base_commission_query = Sale.objects.filter(created__range=(col1_start, col1_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
        col1_referral_commission_query = Sale.objects.filter(created__range=(col1_start, col1_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=True)
        context['col1_total_commission'] = col1_base_commission_query.aggregate(Sum('converted_commission')).get('converted_commission__sum') or ZERO_DECIMAL
        context['col1_publisher_commission'] = col1_base_commission_query.filter(user_id__isnull=False, user_id__gt=0).aggregate(Sum('commission')).get('commission__sum') or ZERO_DECIMAL
        context['col1_publisher_commission'] += col1_referral_commission_query.aggregate(Sum('commission')).get('commission__sum') or ZERO_DECIMAL
        context['col1_apprl_commission'] = context['col1_total_commission'] - context['col1_publisher_commission']

        # Commission value last week
        col3_base_commission_query = Sale.objects.filter(created__range=(col3_start, col3_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
        col3_referral_commission_query = Sale.objects.filter(created__range=(col3_start, col3_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=True)
        context['col3_total_commission'] = col3_base_commission_query.aggregate(Sum('converted_commission')).get('converted_commission__sum') or ZERO_DECIMAL
        context['col3_publisher_commission'] = col3_base_commission_query.filter(user_id__isnull=False, user_id__gt=0).aggregate(Sum('commission')).get('commission__sum') or ZERO_DECIMAL
        context['col3_publisher_commission'] += col3_referral_commission_query.aggregate(Sum('commission')).get('commission__sum') or ZERO_DECIMAL
        context['col3_apprl_commission'] = context['col3_total_commission'] - context['col3_publisher_commission']

        # Commission values changes
        context['col2_total_commission'] = (context['col1_total_commission'] - context['col3_total_commission']) / context['col3_total_commission'] * 100
        context['col2_apprl_commission'] = (context['col1_apprl_commission'] - context['col3_apprl_commission']) / context['col3_apprl_commission'] * 100
        context['col2_publisher_commission'] = (context['col1_publisher_commission'] - context['col3_publisher_commission']) / context['col3_publisher_commission'] * 100

        # Clicks
        context['col1_clicks'] = decimal.Decimal(ProductStat.objects.filter(created__range=(col1_start, col1_end)).count())
        context['col3_clicks'] = decimal.Decimal(ProductStat.objects.filter(created__range=(col3_start, col3_end)).count())
        context['col2_clicks'] = (context['col1_clicks'] - context['col3_clicks']) / context['col3_clicks'] * 100

        # Sales
        context['col1_sales'] = decimal.Decimal(col1_base_sales_query.count())
        context['col3_sales'] = decimal.Decimal(col3_base_sales_query.count())
        context['col2_sales'] = (context['col1_sales'] - context['col3_sales']) / context['col3_sales'] * 100

        # Conversion rate
        context['col1_conversion_rate'] = context['col1_sales'] / context['col1_clicks']
        context['col3_conversion_rate'] = context['col3_sales'] / context['col3_clicks']
        context['col2_conversion_rate'] = (context['col1_conversion_rate'] - context['col3_conversion_rate']) / context['col3_conversion_rate'] * 100

        # Avg commission
        context['col1_avg_commission'] = context['col1_total_commission'] / context['col1_total_sale']
        context['col3_avg_commission'] = context['col3_total_commission'] / context['col3_total_sale']
        context['col2_avg_commission'] = (context['col1_avg_commission'] - context['col3_avg_commission']) / context['col3_avg_commission'] * 100

        # Avg sale
        context['col1_avg_sale'] = context['col1_total_sale'] / context['col1_sales']
        context['col3_avg_sale'] = context['col3_total_sale'] / context['col3_sales']
        context['col2_avg_sale'] = (context['col1_avg_sale'] - context['col3_avg_sale']) / context['col3_avg_sale'] * 100

        # Active publishers
        context['col1_active_publishers'] = ProductStat.objects.filter(created__range=(col1_start, col1_end), user_id__isnull=False, user_id__gt=0).values('user_id').order_by('user_id').distinct().count()
        context['col1_active_publishers'] = decimal.Decimal(context['col1_active_publishers'])
        context['col3_active_publishers'] = ProductStat.objects.filter(created__range=(col3_start, col3_end), user_id__isnull=False, user_id__gt=0).values('user_id').order_by('user_id').distinct().count()
        context['col3_active_publishers'] = decimal.Decimal(context['col3_active_publishers'])
        context['col2_active_publishers'] = (context['col1_active_publishers'] - context['col3_active_publishers']) / context['col3_active_publishers'] * 100

        return render(request, 'apparel/admin/kpi_dashboard.html', context)

    raise Http404
