import re
import math
import os.path
import decimal
import json

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response

from django.shortcuts import get_object_or_404, render
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

from sorl.thumbnail import get_thumbnail
from apparelrow.apparel.utils import JSONResponse, set_query_parameter, select_from_multi_gender, currency_exchange

from apparelrow.profile.models import Follow

BROWSE_PAGE_SIZE = 30

DEFAULT_SORT_ARGUMENTS = {
    'pop': 'popularity desc, created desc',
    'lat': 'created desc, popularity desc',
    'exp': 'price desc, popularity desc, created desc',
    'che': 'price asc, popularity desc, created desc'
}


def create_shop(request, template='apparel/create_shop.html', shop_id=None, gender=None, user_gender=None, user_id=None, language=None, **kwargs):

    if not request.user.is_authenticated():
        return HttpResponse('Unauthorized', status=401)

    if shop_id is not None:
        shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=shop_id)

        if request.user is not shop.user:
            return HttpResponse('Unauthorized', status=401)

    else:
        shop = False

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
        shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=pk)

        if request.user.is_authenticated() and request.user == shop.user:
            shop.delete()
            return JSONResponse(status=204)

        return JSONResponse({ 'message': 'Not authenticated'}, status=401)



    def put(self, request, pk, *args, **kwargs):
        if pk is not -1:
            shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=pk)
        else:
            shop = ShopEmbed()
            shop.save()

        try:
            json_data = json.loads(request.body)
        except ValueError:
            return JSONResponse({ 'message': 'Invalid json body' }, status=400)

        if not request.user.is_authenticated():
            return JSONResponse({ 'message': 'Not authenticated'}, status=401)

        required_keys = ['title', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return JSONResponse({ 'message': 'Missing key %s' % (key,) }, status=400)

        json_data['user'] = request.user

        if json_data['published']:
            request.session['shop_saved'] = True

        if json_data['components']:

            # Remove components
            shop_components = get_model('apparel', 'ShopEmbedProduct').objects.filter(shop_embed_id=pk)
            updated_component_ids = [x['id'] for x in json_data['components'] if 'id' in x]
            for component in shop_components:
                if component.id not in updated_component_ids:
                    component.delete()

            # Add new components and update old
            ShopEmbedProduct = get_model('apparel', 'ShopEmbedProduct')
            for component in json_data['components']:
                component_id = None
                if 'id' in component:
                    component_id = component['id']
                    del component['id']

                product_id = component['product']['id']
                del component['product']

                shop_component, created = ShopEmbedProduct.objects.get_or_create(id=component_id,
                                                                                 shop_embed_id=pk,
                                                                                 product_id=product_id)

                for key, value in component.items():
                    setattr(shop_component, key, value)

                shop_component.save()

            del json_data['components']

        # TODO: Handle errors
        shop.save()

        return JSONResponse(status=204)

    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(request.body)
        except ValueError:
            return JSONResponse({'message': 'Invalid json body'}, status=400)

        if not request.user.is_authenticated():
            return JSONResponse({'message': 'Not authenticated'}, status=401)

        required_keys = ['title', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return JSONResponse({ 'message': 'Missing key %s' % (key,) }, status=400)

        json_data['user'] = request.user

        if json_data['published']:
            request.session['shop_saved'] = True

        # Exclude components, handle later
        components = json_data['components']
        del json_data['components']

        shop = get_model('apparel', 'ShopEmbed')(**json_data)
        shop.save()

        for component in components:
            component['product_id'] = component['product']['id']
            del component['product']

            if 'component_of' not in component:
                component['component_of'] = shop.component

            component['shop_id'] = shop.pk

            # TODO: Error handling
            shop_component = get_model('apparel', 'ShopEmbedProduct')(**component)
            shop_component.shop_embed = shop
            shop_component.save()

        response = JSONResponse(shop_instance_to_dict(shop), status=201)
        response['Location'] = reverse('shop_create', args=[shop.pk])

        return response
