import datetime
import calendar

from django.shortcuts import render
from django.db.models import Sum

from dashboard.models import Sale


def dashboard(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.get_profile().is_partner:
        if year is not None and month is not None:
            start_date = datetime.date(int(year), int(month), 1)
        else:
            start_date = datetime.date.today().replace(day=1)

        year = start_date.year
        month = start_date.month

        end_date = start_date
        end_date = end_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])

        data_per_month = {}
        for day in range(1, (end_date - start_date).days + 2):
            data_per_month[start_date.replace(day=day)] = 0

        for sale in Sale.objects.filter(status__gte=Sale.PENDING, status__lte=Sale.CONFIRMED) \
                                .filter(sale_date__gte=start_date, sale_date__lte=end_date) \
                                .order_by('sale_date') \
                                .values('sale_date', 'commission'):
            data_per_month[sale['sale_date'].date()] += sale['commission']

        # Months
        dt1 = request.user.date_joined.date()
        dt2 = datetime.date.today()
        start_month = dt1.month
        end_months = (dt2.year - dt1.year) * 12 + dt2.month + 1
        dates = [datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
            ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
        )]

        # Total sales counts
        sales_pending = Sale.objects.filter(status=Sale.PENDING).aggregate(total=Sum('commission'))['total']
        sales_confirmed = Sale.objects.filter(status=Sale.CONFIRMED).aggregate(total=Sum('commission'))['total']
        sales_total = sales_pending + sales_confirmed

        return render(request, 'dashboard/partner.html', {'sales': data_per_month,
                                                          'total_sales': sales_total,
                                                          'total_confirmed': sales_confirmed,
                                                          'pending_payment': 0,
                                                          'dates': dates,
                                                          'year': year,
                                                          'month': month})

    return render(request, 'dashboard/partner_signup.html')


def dashboard_info(request):
    return render(request, 'dashboard/info.html')
