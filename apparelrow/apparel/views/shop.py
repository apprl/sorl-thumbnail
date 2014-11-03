import re
import math
import os.path
import decimal
import json

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response
<<<<<<< HEAD
from django.shortcuts import get_object_or_404, render
=======
from django.shortcuts import render
>>>>>>> 7c92b8aab2ac0b7e053730af024ce31a454cc38e
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

<<<<<<< HEAD
from sorl.thumbnail import get_thumbnail
from apparelrow.apparel.utils import JSONResponse, set_query_parameter, select_from_multi_gender, currency_exchange

=======
>>>>>>> 7c92b8aab2ac0b7e053730af024ce31a454cc38e
from apparelrow.profile.models import Follow

BROWSE_PAGE_SIZE = 30

DEFAULT_SORT_ARGUMENTS = {
    'pop': 'popularity desc, created desc',
    'lat': 'created desc, popularity desc',
    'exp': 'price desc, popularity desc, created desc',
    'che': 'price asc, popularity desc, created desc'
}

<<<<<<< HEAD
def create_shop(request, template='apparel/create_shop.html', shop_id=None, gender=None, user_gender=None, user_id=None, language=None, **kwargs):

    if shop_id is not None:
        shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=shop_id)
    else:
        shop = None

=======
def create_shop(request, template='apparel/create_shop.html', gender=None, user_gender=None, user_id=None, language=None, **kwargs):
>>>>>>> 7c92b8aab2ac0b7e053730af024ce31a454cc38e
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
<<<<<<< HEAD
        'pricerange': {'min': 0, 'max': 10000},
        'external_shop_id': shop_id,
    })

def shop_instance_to_dict(shop):
    shop_dict = {
        'id': shop.id,
        'title': shop.title,
        'user': shop.user.display_name,
        #'url': shop.get_absolute_url(),
        'url': '/en/shop/create/api/1/',
        'slug': shop.slug,
        'description': shop.description,
        'published': shop.published,
    }

    if shop.products:
        shop_dict['products'] = []

        for product in shop.products.all():
            shop_dict['products'].append({
                'id': product.id,
                'slug': product.slug,
                'image_small': get_thumbnail(product.product_image, '112x145', crop=False, format='PNG', transparent=True).url,
                'image_look': get_thumbnail(product.product_image, '224x291', crop=False, format='PNG', transparent=True).url,
                'product_name': product.product_name,
                'brand_name': 'test',
            })
    return shop_dict

class ShopCreateView(View):
    def get(self, request, pk, *args, **kwargs):
        print "ShopCreateView: Get"

        if pk is not None:
            shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=pk)
            return JSONResponse(shop_instance_to_dict(shop))
    def delete(self, request, pk, *args, **kwargs):
=======
        'pricerange': {'min': 0, 'max': 10000}
    })

class ShopCreateView(View):
    def delete(selfself, request, pk, *args, **kwargs):
>>>>>>> 7c92b8aab2ac0b7e053730af024ce31a454cc38e
        print "ShopCreateView: Delete"

    def put(self, request, pk, *args, **kwargs):
        print "ShopCreateView: Put"

    def post(self, request, *args, **kwargs):
        print "ShopCreateView: Post"