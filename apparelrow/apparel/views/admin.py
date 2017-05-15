# -*- coding: utf-8 -*-
import datetime
import decimal
import calendar

from django.shortcuts import render
from django.db.models import Sum, Count, Min
from django.http import Http404, HttpResponseNotFound, HttpResponse
from apparelrow.apparel.models import Vendor
from apparelrow.apparel.utils import get_pagination_page
from apparelrow.apparel.browse import get_pagination_as_dict
from apparelrow.dashboard.models import Sale
from apparelrow.dashboard.stats_admin import ppc_all_stores_stats
from apparelrow.dashboard.views import parse_date
from apparelrow.dashboard.utils import enumerate_months
from apparelrow.importer.models import VendorFeed
from apparelrow.statistics.models import ProductStat
from dateutil.relativedelta import relativedelta
from django.views.generic import TemplateView
from django.template import loader
from django.template import RequestContext




ZERO_DECIMAL = decimal.Decimal('0.00')
BROWSE_PAGE_SIZE = 30

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


def year_magic(d):
    return (d.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
            d.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999))


def get_date_interval(date, is_month=False, is_year=False, previous=False):
    if is_year:
        if previous:
            return year_magic(date - relativedelta(months=12))
        return year_magic(date)

    elif is_month:
        if previous:
            return month_magic(date - relativedelta(months=1))
        return month_magic(date)

    if previous:
        return week_magic(date - datetime.timedelta(days=7))

    return week_magic(date)




class PPCAllStoresView(TemplateView):

    template_name = 'apparel/admin/ppc_as.html'

    def get_context_data(self, **kwargs):
        context = super(PPCAllStoresView, self).get_context_data(**kwargs)
        month = None if not 'month' in kwargs else kwargs['month']
        year = None if not 'year' in kwargs else kwargs['year']
        start_date, end_date = parse_date(month, year)
        year = start_date.year
        if month != "0":
            month = start_date.month

        flush_cache = 'flush_cache' in self.request.GET

        month_display, month_choices, year_choices = enumerate_months(self.request.user, month)
        stats = ppc_all_stores_stats(year, month, flush_cache)

        context.update({
            'stats': stats,
            'month': month,
            'year': year,
            'month_display': month_display,
            'month_choices': month_choices,
            'year_choices': year_choices,
            'flush_cache': flush_cache
        })
        return context

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context)
        return HttpResponseNotFound()


def kpi_dashboard(request):
    if request.user.is_authenticated() and request.user.is_superuser:
        decimal.setcontext(decimal.ExtendedContext)

        # Date
        is_month = bool(request.GET.get('is_month', None))
        is_year = bool(request.GET.get('is_year', None))
        date = request.GET.get('date')
        if date:
            date = datetime.datetime(*[int(x) for x in date.split('-')])
        else:
            date = datetime.datetime.now()

        col1_start, col1_end = get_date_interval(date, is_month=is_month, is_year=is_year, previous=False)
        col3_start, col3_end = get_date_interval(date, is_month=is_month, is_year=is_year, previous=True)

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
        context['col1_conversion_rate'] = context['col1_sales'] / context['col1_clicks'] * 100
        context['col3_conversion_rate'] = context['col3_sales'] / context['col3_clicks'] * 100
        context['col2_conversion_rate'] = (context['col1_conversion_rate'] - context['col3_conversion_rate']) / context['col3_conversion_rate'] * 100

        # Avg commission
        context['col1_avg_commission'] = context['col1_total_commission'] / context['col1_total_sale'] * 100
        context['col3_avg_commission'] = context['col3_total_commission'] / context['col3_total_sale'] * 100
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


def stores(request, user_id=None):
    if request.user.is_authenticated() and (request.user.is_superuser or request.user.pk == user_id):
        decimal.setcontext(decimal.ExtendedContext)

        # Date
        is_month = bool(request.GET.get('is_month', None))
        is_year = bool(request.GET.get('is_year', None))
        date = request.GET.get('date')
        if date:
            date = datetime.datetime(*[int(x) for x in date.split('-')])
        else:
            date = datetime.datetime.now()

        date_start, date_end = get_date_interval(date, is_month=is_month, is_year=is_year)

        context = {'user_id': user_id,
                   'date_start': date_start,
                   'date_end': date_end,
                   'affiliates': {},
                   'clicks': 0,
                   'sales': 0,
                   'sales_sum': 0,
                   'commission': 0}

        # Group vendors by affiliate
        if user_id:
            vendors = Vendor.objects.filter(user_id=user_id)
        else:
            vendors = Vendor.objects.all()

        for vendor in vendors:
            try:
                affiliate_name = vendor.vendor_feed.provider_class
                if affiliate_name not in context['affiliates']:
                    context['affiliates'][affiliate_name] = {'vendors': [], 'clicks': 0, 'sales': 0, 'sales_sum': 0, 'commission': 0}

                vendor_data = {'vendor_object': vendor}

                # Clicks
                vendor_data['clicks'] = decimal.Decimal(ProductStat.objects.filter(vendor=vendor, created__range=(date_start, date_end)).count())
                context['affiliates'][affiliate_name]['clicks'] += vendor_data['clicks']
                context['clicks'] += vendor_data['clicks']

                # Sales
                sales_query = Sale.objects.filter(vendor=vendor, created__range=(date_start, date_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
                vendor_data['sales'] = decimal.Decimal(sales_query.count())
                vendor_data['sales_sum'] = sales_query.aggregate(Sum('converted_amount')).get('converted_amount__sum') or ZERO_DECIMAL
                context['affiliates'][affiliate_name]['sales'] += vendor_data['sales']
                context['affiliates'][affiliate_name]['sales_sum'] += vendor_data['sales_sum']
                context['sales'] += vendor_data['sales']
                context['sales_sum'] += vendor_data['sales_sum']

                # Commission
                commission_query = Sale.objects.filter(vendor=vendor, created__range=(date_start, date_end), status__range=(Sale.PENDING, Sale.CONFIRMED), is_promo=False, is_referral_sale=False)
                vendor_data['commission'] = commission_query.aggregate(Sum('converted_commission')).get('converted_commission__sum') or ZERO_DECIMAL
                context['affiliates'][affiliate_name]['commission'] += vendor_data['commission']
                context['commission'] += vendor_data['commission']

                # Actual commission
                vendor_data['actual_commission'] = vendor_data['commission'] / vendor_data['sales_sum'] * 100
                context['affiliates'][affiliate_name]['actual_commission'] = context['affiliates'][affiliate_name]['commission'] / context['affiliates'][affiliate_name]['sales_sum'] * 100
                context['actual_commission'] = context['commission'] / context['sales_sum'] * 100

                # Conversion
                vendor_data['conversion'] = vendor_data['sales'] / vendor_data['clicks'] * 100
                context['affiliates'][affiliate_name]['conversion'] = context['affiliates'][affiliate_name]['sales'] / context['affiliates'][affiliate_name]['clicks'] * 100
                context['conversion'] = context['sales'] / context['clicks'] * 100

                # EPC
                vendor_data['epc'] = vendor_data['commission'] / vendor_data['clicks']
                context['affiliates'][affiliate_name]['epc'] = context['affiliates'][affiliate_name]['commission'] / context['affiliates'][affiliate_name]['clicks']
                context['epc'] = context['commission'] / context['clicks']

                # Set vendor data
                context['affiliates'][affiliate_name]['vendors'].append(vendor_data)

            except VendorFeed.DoesNotExist:
                pass

        return render(request, 'apparel/admin/stores.html', context)

    raise Http404


class AdminPostsView(TemplateView):
    template_name = 'apparel/admin/posts.html'

    def get_context_data(self, request, **kwargs):
        context = super(AdminPostsView, self).get_context_data(**kwargs)
        month = None if not 'month' in kwargs else kwargs['month']
        year = None if not 'year' in kwargs else kwargs['year']
        vendor = "all" if not 'vendor' in kwargs else kwargs['vendor']

        sort_by = request.GET.get('sort_by', None)
        order = request.GET.get('order', None)

        if sort_by not in ['user_id', 'referer', 'created_date', 'posts']:
            sort_by = 'posts'

        if order not in ['asc', 'desc']:
            order = 'desc'

        start_date, end_date = parse_date(month, year)

        year = start_date.year
        if month != "0":
            month = start_date.month

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))
        month_display, month_choices, year_choices = enumerate_months(self.request.user, month)
        vendor_choices = Vendor.objects.values('name', 'pk')

        query = ProductStat.objects.filter(
            created__range=(start_date_query, end_date_query)
            ).exclude(user_id=0)

        if vendor != "all":
            vendor = int(vendor)
            vendor_name = Vendor.objects.get(pk=vendor).name
            query = query.filter(vendor=vendor_name)

        query = query.values('referer', 'user_id').annotate(posts=Count('referer'), created_date=Min('created'))
        product_stats = query.order_by("%s%s" % ("-" if order == "desc" else "", sort_by))

        paged_result, pagination = get_pagination_page(product_stats, BROWSE_PAGE_SIZE, self.request.GET.get('page', 1))

        context.update({
            'current_page': paged_result,
            'next': self.request.get_full_path(),
            'month': month,
            'year': year,
            'vendor': vendor,
            'month_display': month_display,
            'month_choices': month_choices,
            'year_choices': year_choices,
            'vendor_choices': vendor_choices,
            'sort_by': sort_by,
            'order': order,
        })
        return context

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            context = self.get_context_data(request=request, **kwargs)

            return render(request, self.template_name, context)
        return HttpResponseNotFound()