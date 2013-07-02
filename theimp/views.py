import logging

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.loading import get_model
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.forms.models import modelformset_factory


logger = logging.getLogger(__name__)

PER_PAGE = 10


def get_unvalidated_count():
    return get_model('theimp', 'Product').objects.filter(is_manual_validated__isnull=True).count()


def get_changed_validated_count():
    # TODO: how to see if it has changed? Maybe a field that gets sets by parser if the value is changed if is_manual_validated is true
    return get_model('theimp', 'Product').objects.filter(is_manual_validated=True).count()


def get_vendor_list():
    return get_model('theimp', 'Vendor').objects.all()


def custom_render(request, template, data=None):
    if data is None:
        data = {}
    data.update({'unvalidated': get_unvalidated_count(), 'invalidated': get_changed_validated_count()})

    return render(request, template, data)


@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return custom_render(request, 'index.html')


@user_passes_test(lambda user: user.is_superuser)
def vendor(request):
    VendorFormSet = modelformset_factory(get_model('theimp', 'Vendor'))
    if request.method == 'POST':
        formset = VendorFormSet(request.POST, request.FILES)
        if formset.is_valid():
            formset.save()
    else:
        formset = VendorFormSet()

    return custom_render(request, 'vendor.html', {'vendors': get_vendor_list(), 'formset': formset})


@user_passes_test(lambda user: user.is_superuser)
def brand_mapper(request):
    vendors = get_vendor_list()
    try:
        vendor = int(request.GET.get('vendor'))
    except (TypeError, ValueError) as e:
        vendor = None

    brand_list = get_model('theimp', 'BrandMapping').objects.order_by('-modified')
    if vendor:
        brand_list = brand_list.filter(vendor_id=vendor)
    paginator = Paginator(brand_list, PER_PAGE)

    page = request.GET.get('page')
    try:
        mappings = paginator.page(page)
    except PageNotAnInteger:
        mappings = paginator.page(1)
    except EmptyPage:
        mappings = paginator.page(paginator.num_pages)

    return custom_render(request, 'brand_mapper.html', {'mappings': mappings, 'vendors': vendors, 'current_vendor': vendor})


@user_passes_test(lambda user: user.is_superuser)
def category_mapper(request):
    vendors = get_vendor_list()
    try:
        vendor = int(request.GET.get('vendor'))
    except (TypeError, ValueError) as e:
        vendor = None

    category_list = get_model('theimp', 'CategoryMapping').objects.order_by('-modified')
    if vendor:
        category_list = category_list.filter(vendor_id=vendor)
    paginator = Paginator(category_list, PER_PAGE)

    page = request.GET.get('page')
    try:
        mappings = paginator.page(page)
    except PageNotAnInteger:
        mappings = paginator.page(1)
    except EmptyPage:
        mappings = paginator.page(paginator.num_pages)

    return custom_render(request, 'category_mapper.html', {'mappings': mappings, 'vendors': vendors, 'current_vendor': vendor})


@user_passes_test(lambda user: user.is_superuser)
def post_category_mapper(request):
    pass


@user_passes_test(lambda user: user.is_superuser)
def messages(request):
    return custom_render(request, 'index.html')
