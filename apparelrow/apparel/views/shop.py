import re
import math
import os.path
import decimal
import json

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.db.models import Max
from django.db.models import Min
from django.db.models.loading import get_model
from django.template import RequestContext
from django.template import loader
from django.core.cache import get_cache
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.core.urlresolvers import reverse
from django.utils import translation
from django.utils.translation import get_language, ugettext as _, ungettext
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from apparelrow.apparel.search import PRODUCT_SEARCH_FIELDS
from apparelrow.apparel.search import ApparelSearch
from apparelrow.apparel.models import Product
from apparelrow.apparel.models import Brand
from apparelrow.apparel.models import Option
from apparelrow.apparel.models import Category
from apparelrow.apparel.models import Vendor
from apparelrow.apparel.utils import get_pagination_page, select_from_multi_gender

from apparelrow.profile.models import Follow

BROWSE_PAGE_SIZE = 30

DEFAULT_SORT_ARGUMENTS = {
    'pop': 'popularity desc, created desc',
    'lat': 'created desc, popularity desc',
    'exp': 'price desc, popularity desc, created desc',
    'che': 'price asc, popularity desc, created desc'
}

def create_shop(request, template='apparel/create_shop.html', gender=None, user_gender=None, user_id=None, language=None, **kwargs):
    if not language:
        language = get_language()
    translation.activate(language)

    currency = settings.APPAREL_BASE_CURRENCY
    if language in settings.LANGUAGE_TO_CURRENCY:
        currency = settings.LANGUAGE_TO_CURRENCY.get(language)

    translation.deactivate()
    # Todo: how real data do we need here?
    return render(request, template, {
        'gender': gender,
        'pricerange': {'min': 0, 'max': 10000}
    })

class ShopCreateView(View):
    def delete(selfself, request, pk, *args, **kwargs):
        print "ShopCreateView: Delete"

    def put(self, request, pk, *args, **kwargs):
        print "ShopCreateView: Put"

    def post(self, request, *args, **kwargs):
        print "ShopCreateView: Post"