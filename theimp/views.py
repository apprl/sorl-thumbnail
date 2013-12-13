import logging

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.loading import get_model
from django.shortcuts import render


logger = logging.getLogger(__name__)


@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return render(request, 'index.html')
