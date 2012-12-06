import json
import decimal

from django.conf import settings
from django.views.generic import View
from django.utils.translation import get_language
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db.models.loading import get_model
from django.shortcuts import render, get_object_or_404

from apparel.search import PRODUCT_SEARCH_FIELDS, ApparelSearch, decode_manufacturer_facet
from apparel.browse import set_query_arguments
from apparel.utils import JSONResponse, set_query_parameter, get_gender_from_cookie, currency_exchange


options = get_model('apparel', 'Option').objects \
                                        .filter(Q(option_type__name='color') | Q(option_type__name='pattern')) \
                                        .exclude(value__exact='') \
                                        .values_list('id', 'value')
options = dict(options)

categories = {'en': dict(get_model('apparel', 'Category').objects.values_list('id', 'name_en')),
              'sv': dict(get_model('apparel', 'Category').objects.values_list('id', 'name_sv'))}


def product_detail_popup(request, pk):
    product = get_object_or_404(get_model('apparel', 'Product'), pk=pk)

    return render(request, 'apparel/fragments/product_detail.html', {'object': product})


class ProductList(View):

    def get(self, request, *args, **kwargs):
        language = get_language()
        currency = settings.APPAREL_BASE_CURRENCY
        if language in settings.LANGUAGE_TO_CURRENCY:
            currency = settings.LANGUAGE_TO_CURRENCY.get(language)
        gender = request.GET.get('gender', get_gender_from_cookie(request))
        facet_fields = request.GET.get('facet', '').split(',')

        try:
            limit = int(request.GET.get('limit', 10))
        except ValueError:
            return HttpResponseBadRequest('bad limit argument')

        clamped_limit = min(30, max(limit, 10))

        query_arguments = {'rows': clamped_limit, 'start': 0}
        query_arguments = set_query_arguments(query_arguments, request, facet_fields, gender=gender, currency=currency)
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

        # User
        user_id = request.GET.get('user_id', False)
        if user_id:
            query_arguments['fq'].append('user_likes:%s' % (user_id,))

        # Sort
        query_arguments['sort'] = request.GET.get('sort', 'popularity desc, created desc')

        # TODO: which fields, template?
        query_arguments['fl'] = ['id:django_id',
                                 'product_name:name',
                                 'brand_name:manufacturer_name',
                                 'price:stored_price',
                                 'discount_price:stored_discount',
                                 'slug',
                                 'image_small',
                                 'discount',
                                 'availability']

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

        if request.GET.get('facet', False):
            return self.get_facet(request, query_string, query_arguments, *args, **kwargs)

        return self.get_products(request, query_string, query_arguments, *args, **kwargs)

    def get_facet(self, request, query_string, query_arguments, *args, **kwargs):
        for key, value in request.GET.items():
            if key.startswith('f.'):
                if key == 'f.manufacturer.facet.prefix':
                    value = value.lower()
                query_arguments[key] = value

        search = ApparelSearch(query_string, **query_arguments)

        # Facet
        facet = search.get_facet()['facet_fields']
        result = {}

        # Calculate price range
        # TODO: price is not a real facet because solr does not support facet.range on currency field
        temp_facet_fields = request.GET.get('facet', '').split(',')
        language = get_language()
        if 'price' in temp_facet_fields:
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

            result.update(price=pricerange)

        # Calculate manufacturer
        if 'manufacturer' in facet:
            ids = facet['manufacturer'][::2]
            values = map(int, facet['manufacturer'][1::2])
            manufacturers = []
            for key, value in zip(ids, values):
                id, name, _ = decode_manufacturer_facet(key)
                manufacturers.append({'id': id,
                                      'name': name,
                                      'count': value})

            result.update(manufacturer=manufacturers)

        # Calculate colors
        if 'color' in facet:
            ids = map(int, facet['color'][::2])
            values = map(int, facet['color'][1::2])

            result.update(color=[{'id': oid, 'count': count, 'name': options[oid]} for oid, count in zip(ids, values)])

        # Calculate category
        if 'category' in facet:
            ids = map(int, facet['category'][::2])
            values = map(int, facet['category'][1::2])

            language = get_language()
            if language not in categories:
                language = 'en'

            result.update(category=[{'id': oid, 'count': count, 'name': categories[language][oid]} for oid, count in zip(ids, values)])

        return JSONResponse(result)


    def get_products(self, request, query_string, query_arguments, *args, **kwargs):
        query_arguments['facet'] = 'false'
        search = ApparelSearch(query_string, **query_arguments)

        # Calculate paginator
        paginator = Paginator(search, query_arguments['rows'])

        page = request.GET.get('page')
        try:
            paged_result = paginator.page(page)
        except PageNotAnInteger:
            paged_result = paginator.page(1)
        except EmptyPage:
            paged_result = paginator.page(paginator.num_pages)

        result = {}
        if paged_result.has_next():
            next_page = request.build_absolute_uri()
            next_page = set_query_parameter(next_page, 'page', paged_result.next_page_number())
            result.update(next_page=next_page)

        if paged_result.has_previous():
            prev_page = request.build_absolute_uri()
            prev_page = set_query_parameter(prev_page, 'page', paged_result.previous_page_number())
            result.update(prev_page=prev_page)


        # Language currency
        language_currency = settings.LANGUAGE_TO_CURRENCY.get(get_language(), settings.APPAREL_BASE_CURRENCY)

        result['products'] = []
        for product in paged_result.object_list:
            price, currency = product.price.split(',')
            discount_price, _ = product.discount_price.split(',')

            rate = currency_exchange(language_currency, currency)

            #product._original_price = product.price
            #product._original_discount_price = product.discount_price

            price = rate * decimal.Decimal(price)
            product.price = price.quantize(decimal.Decimal('1'),
                                           rounding=decimal.ROUND_HALF_UP)
            discount_price = rate * decimal.Decimal(discount_price)
            product.discount_price = discount_price.quantize(decimal.Decimal('1'),
                                                             rounding=decimal.ROUND_HALF_UP)
            product.currency = language_currency

            result['products'].append(product.__dict__)

        return JSONResponse(result)
