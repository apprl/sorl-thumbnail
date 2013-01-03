from django.shortcuts import render
from django.db.models import Sum

from dashboard.models import Sale


def dashboard(request, year=None, month=None):
    if request.user.is_authenticated() and request.user.get_profile().is_partner:
        sales = Sale.objects.filter(status__gte=Sale.PENDING, status__lt=Sale.PAID).order_by('sale_date')

        sales_total = Sale.objects.filter(status__gte=Sale.PENDING, status__lt=Sale.PAID).aggregate(total=Sum('commission'))

        return render(request, 'dashboard/partner.html', {'sales': sales,
                                                          'sales_total': sales_total['total']})

    return render(request, 'dashboard/partner_signup.html')


def dashboard_info(request):
    return render(request, 'dashboard/info.html')
