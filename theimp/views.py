import logging

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.loading import get_model
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render

logger = logging.getLogger(__name__)

PER_PAGE = 15


@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return render(request, 'index.html')


@user_passes_test(lambda user: user.is_superuser)
def brand_mapper(request):
    brand_list = get_model('theimp', 'BrandMapping').objects.all()
    paginator = Paginator(brand_list, PER_PAGE)

    page = request.GET.get('page')
    try:
        mappings = paginator.page(page)
    except PageNotAnInteger:
        mappings = paginator.page(1)
    except EmptyPage:
        mappings = paginator.page(paginator.num_pages)

    return render(request, 'brand_mapper.html', {'mappings': mappings})


@user_passes_test(lambda user: user.is_superuser)
def category_mapper(request):
    vendor_list = get_model('theimp', 'Vendor').objects.all()
    category_list = get_model('theimp', 'CategoryMapping').objects.all()
    paginator = Paginator(category_list, PER_PAGE)

    page = request.GET.get('page')
    try:
        mappings = paginator.page(page)
    except PageNotAnInteger:
        mappings = paginator.page(1)
    except EmptyPage:
        mappings = paginator.page(paginator.num_pages)

    return render(request, 'category_mapper.html', {'mappings': mappings, 'vendors': vendor_list})


@user_passes_test(lambda user: user.is_superuser)
def messages(request):
    return render(request, 'index.html')
