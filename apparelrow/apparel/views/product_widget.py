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
from apparelrow.apparel.models import ShopEmbed
from apparelrow.apparel.models import ShopProduct
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

def _to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

def create_shop(request, template='apparel/create_shop.html', shop_id=None, gender=None, user_gender=None, user_id=None, language=None, **kwargs):
    if not request.user.is_authenticated():
        return HttpResponse('Unauthorized', status=401)

    likes = []
    show_liked = False
    if shop_id is not None and shop_id is not 0:
        shop = get_object_or_404(get_model('apparel', 'Shop'), pk=shop_id)

        if shop.show_liked:
            likes = shop.user.product_likes.all()
            show_liked = True

        if request.user.pk is not shop.user.pk:
            return HttpResponse('Unauthorized', status=401)

    else:
        shop = False
        shop_id = 0
        show_liked = True

    if not language:
        language = get_language()

    translation.activate(language)

    # Todo: how real data do we need here?
    return render(request, template, {
        'gender': gender if gender is not None else 'A',
        'show_liked': str(show_liked).lower(),
        'product_picker': not show_liked,
        'likes': likes,
        'pricerange': {'min': 0, 'max': 10000},
        'external_shop_id': shop_id,
        'object': shop
    })

def shop_instance_to_dict(shop):
    shop_dict = {
        'id': shop.id,
        'title': shop.title,
        'show_liked': shop.show_liked,
        'user': shop.user.display_name,
        'url': shop.get_absolute_url(),
        'slug': shop.slug,
        'description': shop.description,
        'published': shop.published,
    }

    shop_dict['products'] = []
    if shop.show_liked:
        for like in shop.user.product_likes.select_related('product').all():
            product = like.product
            manufacturer_name = product.manufacturer.name if product.manufacturer else None
            shop_dict['products'].append({
                'id': product.id,
                'slug': product.slug,
                'image_small': get_thumbnail(product.product_image, '112x145', crop=False, format='PNG', transparent=True).url,
                'image_look': get_thumbnail(product.product_image, '224x291', crop=False, format='PNG', transparent=True).url,
                'product_name': product.product_name,
                'brand_name': manufacturer_name,
                'currency': product.default_vendor.locale_currency,
                'price': product.default_vendor.locale_price,
                'discount_price': product.default_vendor.locale_discount_price,
            })
    else:
        for product in shop.products.all():
            manufacturer_name = product.manufacturer.name if product.manufacturer else None
            shop_dict['products'].append({
                'id': product.id,
                'slug': product.slug,
                'image_small': get_thumbnail(product.product_image, '112x145', crop=False, format='PNG', transparent=True).url,
                'image_look': get_thumbnail(product.product_image, '224x291', crop=False, format='PNG', transparent=True).url,
                'product_name': product.product_name,
                'brand_name': manufacturer_name,
                'currency': product.default_vendor.locale_currency,
                'price': product.default_vendor.locale_price,
                'discount_price': product.default_vendor.locale_discount_price,
            })

    return shop_dict

class ShopCreateView(View):
    def get(self, request, pk, *args, **kwargs):
        if pk is not None:
            shop = get_object_or_404(get_model('apparel', 'Shop'), pk=pk)
            return JSONResponse(shop_instance_to_dict(shop))

    def delete(self, request, pk, *args, **kwargs):
        shop = get_object_or_404(get_model('apparel', 'Shop'), pk=pk)

        if request.user.is_authenticated() and request.user == shop.user:
            shop.delete()
            return JSONResponse(status=204)

        return JSONResponse({ 'message': 'Not authenticated'}, status=401)



    def put(self, request, pk=None, *args, **kwargs):
        if pk is not None and pk is not 0:
            shop = get_object_or_404(get_model('apparel', 'Shop'), pk=pk)
        else:
            shop = Shop()
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

        shop.published = json_data['published']

        print shop.published
        print shop.published

        if json_data['components']:

            # Remove components
            shop_components = get_model('apparel', 'ShopProduct').objects.filter(shop_embed_id=pk)
            updated_component_ids = [x['id'] for x in json_data['components'] if 'id' in x]
            for component in shop_components:
                if component.id not in updated_component_ids:
                    component.delete()

            # Add new components and update old
            ShopProduct = get_model('apparel', 'ShopProduct')
            for component in json_data['components']:
                component_id = None
                if 'id' in component:
                    component_id = component['id']
                    del component['id']

                product_id = component['product']['id']
                del component['product']

                shop_component, created = ShopProduct.objects.get_or_create(id=component_id,
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

        if 'components' in json_data:
            # Exclude components, handle later
            components = json_data['components']
            del json_data['components']
        if '0' in json_data:
            del json_data['0']

        show_liked = False
        if 'show_liked' in json_data:
            show_liked = json_data['show_liked']
            del json_data['show_liked']

        if show_liked:
            components = []
            try:
                shop = get_model('apparel', 'Shop').objects.filter(user=request.user, show_liked=True)[0]
            except:
                shop = get_model('apparel', 'Shop')(**json_data)
        else:
            shop = get_model('apparel', 'Shop')(**json_data)

        shop.show_liked = show_liked
        shop.save()

        for component in components:
            component['product_id'] = component['product']['id']
            del component['product']

            # TODO: Error handling
            shop_component = get_model('apparel', 'ShopProduct')(**component)
            shop_component.shop_embed = shop
            shop_component.save()

        response = JSONResponse(shop_instance_to_dict(shop), status=201)
        response['Location'] = reverse('create_shop', args=[shop.pk])

        return response


def shop_widget(request, shop_id=None):
    if request.method != 'POST':
        return HttpResponseNotAllowed()

    shop = get_object_or_404(get_model('apparel', 'Shop'), pk=shop_id)

    if request.user.pk is not shop.user.pk:
        return HttpResponseNotAllowed()


    content = {}
    content['width'] = int(request.POST.get('width', 100))
    content['width_type'] = request.POST.get('width_type', '%')
    content['height'] = int(request.POST.get('height', 600))
    content['language'] = request.POST.get('language', 'sv')
    show_product_brand = bool(int(request.POST.get('show_product_brand', 1)))
    show_filters = bool(int(request.POST.get('show_filters', 1)))
    show_filters_collapsed = bool(int(request.POST.get('show_filters_collapsed', 1)))

    if content['width_type'] == '%' and int(content['width']) > 100:
        content['width'] = 100
    elif content['width_type'] == 'px':
        if content['width'] < 600:
            content['width'] = 600
        elif content['width'] > 1200:
            content['width'] = 1200

    shop_embed = ShopEmbed(
        shop=shop,
        user=shop.user,
        width=content['width'],
        width_type=content['width_type'],
        height=content['height'],
        language=content['language'],
        show_product_brand=show_product_brand,
        show_filters=show_filters,
        show_filters_collapsed=show_filters_collapsed
    )

    shop_embed.save()
    content['object'] = shop_embed

    return render(request, 'apparel/fragments/shop_widget.html', content)


def dialog_embed(request, shop_id=None):
    shop = get_object_or_404(get_model('apparel', 'Shop'), pk=shop_id)

    max_width = 1200
    default_width = 600

    return render(request, 'apparel/dialog_shop_embed.html', {
        'shop': shop,
        'default_width': default_width,
        'max_width': max_width,
    })

#
# Embed
#
def embed_shop(request, template='apparel/shop_embed.html', embed_shop_id=None):
    if embed_shop_id is None:
        return HttpResponse('Not found', status=404)

    embed_shop = get_object_or_404(get_model('apparel', 'ShopEmbed'), pk=embed_shop_id)
    shop = embed_shop.shop

    #if shop.published is not True:
    #    return HttpResponse('Unauthorized', status=401)

    language = embed_shop.language

    response = browse_products(request, template, shop, embed_shop, language)

    return response

def browse_products(request, template='apparel/browse.html', shop=None, embed_shop=None, language=None, **kwargs):
    user_id = shop.user.id

    if not language:
        language = get_language()
    translation.activate(language)

    currency = settings.APPAREL_BASE_CURRENCY
    if language in settings.LANGUAGE_TO_CURRENCY:
        currency = settings.LANGUAGE_TO_CURRENCY.get(language)

    facet_fields = ['category', 'price', 'color', 'manufacturer', 'store']
    query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
    query_arguments = set_query_arguments(query_arguments, request, facet_fields, currency=currency)
    disable_availability = kwargs.get('disable_availability', False)
    if not disable_availability:
        query_arguments['fq'].append('availability:true')

    result = {}

    # Sort
    query_arguments['sort'] = DEFAULT_SORT_ARGUMENTS.get(request.GET.get('sort'), DEFAULT_SORT_ARGUMENTS['pop'])

    # Shop views
    view = request.GET.get('view', 'all')
    is_authenticated = request.user.is_authenticated()
    if view == 'friends' or 'f' in request.GET:
        user_ids = []
        if is_authenticated:
            user_ids = get_model('profile', 'Follow').objects.filter(user=request.user).values_list('user_follow_id', flat=True)
        else:
            result.update(extra_html=loader.render_to_string('apparel/fragments/browse_follow_user.html', {}, context_instance=RequestContext(request)))
        user_ids_or = ' OR '.join(str(x) for x in (list(user_ids) + [0]))
        query_arguments['fq'].append('user_likes:(%s)' % (user_ids_or,))
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

    elif view == 'brands':
        brand_ids = []
        if is_authenticated:
            brand_ids = get_model('apparel', 'Brand').objects.filter(user__followers__user=request.user, user__followers__active=True).values_list('id', flat=True)
        else:
            result.update(extra_html=loader.render_to_string('apparel/fragments/browse_follow_brand.html', {}, context_instance=RequestContext(request)))
        brand_ids_or = ' OR '.join(str(x) for x in (list(brand_ids) + [0]))
        query_arguments['fq'].append('manufacturer_id:(%s)' % (brand_ids_or,))
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))
    else:

        # If the shop is set to list liked product, then get the liked products only.
        if shop.show_liked:
            if user_id:
                if 'is_brand' in kwargs and kwargs['is_brand']:
                    query_arguments['sort'] = 'availability desc, created desc, popularity desc'
                    query_arguments['fq'].append('user_likes:%s OR manufacturer_id:%s' % (user_id, kwargs['is_brand']))
                else:
                    query_arguments['sort'] = 'availability desc, %s_uld desc, popularity desc, created desc' % (user_id,)
                    query_arguments['fq'].append('user_likes:%s' % (user_id,))
            else:
                query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

        # If shop is set to list chosen products then these are what we want.
        else:
            query_arguments['sort'] = 'availability desc, %s_spd desc, popularity desc, created desc' % (shop.id,)
            query_arguments['fq'].append('shop_products:%s' % (shop.id,))

    # Query string
    query_string = request.GET.get('q')
    if not query_string:
        query_string = '*:*'
    else:
        # If we have a query string use edismax search type and search in
        # specified fields
        query_arguments['qf'] = PRODUCT_SEARCH_FIELDS
        query_arguments['defType'] = 'edismax'

        sort_get = request.GET.get('sort')
        if not sort_get or sort_get == '':
            query_arguments['sort'] = 'score desc'

    query_arguments['f.manufacturer.facet.limit'] = 40
    query_arguments['f.manufacturer.facet.sort'] = 'index'

    brand_search = request.GET.get('brand_search', None)
    if brand_search:
        query_arguments['f.manufacturer.facet.prefix'] = brand_search.lower()

    brand_search_page = int(request.GET.get('brand_search_page', 0))
    if brand_search_page:
        query_arguments['f.manufacturer.facet.offset'] = brand_search_page * query_arguments['f.manufacturer.facet.limit']

    search = ApparelSearch(query_string, **query_arguments)

    facet = search.get_facet()['facet_fields']

    # Calculate manufacturer
    manufacturers = []
    for i, value in enumerate(facet['manufacturer']):
        if i % 2 == 0:
            split = value.split('|')
            manufacturers.append((int(split[-1]), split[-2]))

    if brand_search or brand_search_page:
        return HttpResponse(json.dumps({'manufacturers': manufacturers}), mimetype='application/json')

    # Calculate price range
    pricerange = {'min': 0, 'max': 10000}
    if language in settings.MAX_MIN_CURRENCY:
        pricerange['max'] = settings.MAX_MIN_CURRENCY.get(language)
    pricerange['selected'] = request.GET['price'] if 'price' in request.GET else '%s,%s' % (pricerange['min'], pricerange['max'])

    price = request.GET.get('price', '').split(',')
    if len(price) == 2:
        pricerange['selected_min'] = price[0]
        pricerange['selected_max'] = price[1]
    else:
        pricerange['selected_min'] = pricerange['min']
        pricerange['selected_max'] = pricerange['max']

    # Calculate store
    stores = []
    for i, value in enumerate(facet['store']):
        if i % 2 == 0:
            split = value.split('|')
            stores.append((int(split[1]), split[0]))

    # Calculate colors
    colors = [int(value) for i, value in enumerate(facet['color']) if i % 2 == 0]

    # Calculate category
    category_ids = map(int, facet['category'][::2])
    category_values = map(int, facet['category'][1::2])
    categories = dict(zip(category_ids, category_values))

    # Calculate paginator
    paged_result, pagination = get_pagination_page(search, BROWSE_PAGE_SIZE,
            request.GET.get('page', 1))

    result.update(pagination=pagination,
                  pricerange=pricerange,
                  manufacturers=manufacturers,
                  stores=stores,
                  colors=colors,
                  categories=categories)

    selected_discount = bool(request.GET.get('discount', None))
    if selected_discount:
        browse_text = ungettext('%(count)s product on sale',
                                '%(count)s products on sale',
                                paged_result.paginator.count) % {
                                    'count': paged_result.paginator.count
                                }
    else:
        browse_text = ungettext('%(count)s product',
                                '%(count)s products',
                                paged_result.paginator.count) % {
                                    'count': paged_result.paginator.count
                                }

    if request.GET.get('q', None):
        browse_text = '%s \'%s\', %s' % (_('Search result for'), request.GET.get('q'), browse_text)

    result.update(browse_text=browse_text)

    paged_result.html = [o.template for o in paged_result.object_list if o]
    paged_result.object_list = []

    if not paged_result.html:
        result.update(extra_html=loader.render_to_string('apparel/fragments/shop_empty.html', {}, context_instance=RequestContext(request)))

    # Update selected
    selected_colors = request.GET.get('color', None)
    if selected_colors:
        selected_colors = map(int, selected_colors.split(','))

    selected_patterns = request.GET.get('pattern', None)
    if selected_patterns:
        selected_patterns = map(int, selected_patterns.split(','))

    selected_price = request.GET.get('price', None)
    if selected_price:
        selected_price = selected_price.split(',', 1)
        try:
            selected_price = map(int, selected_price)
        except ValueError:
            selected_price = [0,0]

    selected_brands = filter(None, map(_to_int, request.GET.get('manufacturer', '').split(',')))
    selected_brands_data = {}
    for brand in Brand.objects.values('id', 'name').filter(pk__in=selected_brands):
        brand['href'] = '%s?manufacturer=%s' % (reverse('apparelrow.apparel.browse.browse_products'), brand['id'])
        selected_brands_data[brand['id']] = brand

    selected_stores = filter(None, map(_to_int, request.GET.get('store', '').split(',')))
    selected_stores_data = {}
    for store in Vendor.objects.values('id', 'name').filter(pk__in=selected_stores):
        store['href'] = '%s?store=%s' % (reverse('apparelrow.apparel.browse.browse_products'), store['id'])
        selected_stores_data[store['id']] = store

    result.update(
        selected_categories  = filter(None, map(_to_int, request.GET.get('category', '').split(','))),
        selected_colors      = selected_colors,
        selected_patterns    = selected_patterns,
        selected_brands      = selected_brands,
        selected_brands_data = selected_brands_data,
        selected_stores      = selected_stores,
        selected_stores_data = selected_stores_data,
        selected_price       = selected_price,
        selected_gender      = request.GET.get('gender', None),
        selected_discount    = selected_discount,
        selected_sort        = request.GET.get('sort', None),
        selected_view        = request.GET.get('view', None),
    )

    # Serve ajax request
    if request.is_ajax():
        result.update(get_pagination_as_dict(paged_result))
        result.update(
            html = loader.render_to_string('apparel/fragments/product_list.html',
                {
                    'current_page': paged_result,
                    'pagination': pagination
                },
                context_instance=RequestContext(request)
            ),
        )
        return HttpResponse(json.dumps(result), mimetype='application/json')

    # Default colors
    default_colors = Option.objects.filter(option_type__name='color').exclude(value__exact='').all()

    # Default patterns
    default_patterns = Option.objects.filter(option_type__name='pattern').exclude(value__exact='').all()

    # User id
    if user_id:
        result.update(user_id=user_id)

    # Serve non ajax request
    result.update(
        default_patterns = default_patterns,
        default_colors = default_colors,
        categories_all = Category.objects.all(),
        current_page = paged_result,
        show_product_brand = embed_shop.show_product_brand,
        show_filters = embed_shop.show_filters,
        show_filters_collapsed = embed_shop.show_filters_collapsed
    )

    # Added remaining kwargs for rendering
    result.update(kwargs)

    response = render_to_response(template, result, context_instance=RequestContext(request))

    translation.deactivate()

    return response

def select_from_multi_gender(request, gender_key, gender=None, default=None):
    """
    This utility function has two use cases, it either returns a gender from
    the multi gender cookie based on the gender_key or it sets a gender if the
    gender parameter is not None.
    """
    if gender is None:
        gender = request.app_multi_gender.get(gender_key, None)
        if gender is None:
            user_default = 'A'
            if request.user and request.user.is_authenticated() and request.user.gender:
                user_default = request.user.gender

            request.app_multi_gender[gender_key] = gender = default or user_default
    else:
        request.app_multi_gender[gender_key] = gender

    return gender

def set_query_arguments(query_arguments, request, facet_fields=None, currency=None):
    """
    Set query arguments that are common for every browse page access.
    """
    query_arguments['fl'] = 'template:{0}_template'.format(translation.get_language())

    query_arguments['facet'] = 'on'
    query_arguments['facet.limit'] = -1
    query_arguments['facet.mincount'] = 1
    query_arguments['facet.field'] = []

    for field in ['category', 'manufacturer', 'color', 'store']:
        if facet_fields and field in facet_fields:
            query_arguments['facet.field'].append('{!ex=%s}%s' % (field, field))

    if 'fq' not in query_arguments:
        query_arguments['fq'] = []

    query_arguments['fq'].append('published:true')
    query_arguments['fq'].append('django_ct:apparel.product')

    # Category
    if 'category' in request.GET:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('category', 'category', ' OR '.join([x for x in request.GET['category'].split(',')])))

    # Price
    if 'price' in request.GET:
        price = request.GET['price'].split(',')
        if len(price) == 2:
            try:
                min_price = decimal.Decimal(price[0])
                max_price = decimal.Decimal(price[1])
            except decimal.InvalidOperation:
                min_price = max_price = decimal.Decimal('0.00')

            min_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP)
            max_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP)
            # Set a large price that we should never encounter
            if max_price >= decimal.Decimal('10000'):
                max_price = decimal.Decimal('1000000000.00')

            if currency:
                query_arguments['fq'].append('{{!tag={0}}}{0}:[{2},{1} TO {3},{1}]'.format('price', currency, str(min_price), str(max_price)))
            else:
                query_arguments['fq'].append('{{!tag={0}}}{0}:[{1} TO {2}]'.format('price', str(min_price), str(max_price)))


    # Only discount
    if 'discount' in request.GET:
        query_arguments['fq'].append('{!tag=%s}discount:true' % ('price',))

    # Brand
    if 'manufacturer' in request.GET:
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('manufacturer', 'manufacturer_id', ' OR '.join([x for x in request.GET['manufacturer'].split(',')])))

    # Store
    if 'store' in request.GET:
        query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('store', 'store_id', ' OR '.join([x for x in request.GET['store'].split(',')])))

    # Color and pattern
    color_pattern_list = request.GET.get('color', '').split(',')
    color_pattern_list.extend(request.GET.get('pattern', '').split(','))
    color_pattern_list = [x for x in color_pattern_list if x]
    if color_pattern_list:
       query_arguments['fq'].append('{!tag=%s}%s:(%s)' % ('color', 'color', ' OR '.join(color_pattern_list)))

    return query_arguments

def get_pagination_as_dict(paged_result):
    # FIXME: This exists because the JSON exporter is unable to serialise
    # Page and Pagination objects. Perhaps this code could be moved to the
    # exporter module instead?
    try:
        previous_page_number = paged_result.previous_page_number()
    except EmptyPage:
        previous_page_number = None

    try:
        next_page_number = paged_result.next_page_number()
    except EmptyPage:
        next_page_number = None

    return {
        'previous_page_number': previous_page_number,
        'next_page_number': next_page_number,
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
    }