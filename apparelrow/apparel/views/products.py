import json

from django.http import HttpResponse
from django.conf import settings
from django.views.generic import View
from django.utils.translation import get_language
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apparel.search import PRODUCT_SEARCH_FIELDS
from apparel.search import ApparelSearch
from apparel.browse import set_query_arguments
from apparel.utils import set_query_parameter


BROWSE_PAGE_SIZE = 30


class ProductList(View):

    def get(self, request, *args, **kwargs):
        language = get_language()
        currency = settings.APPAREL_BASE_CURRENCY
        if language in settings.LANGUAGE_TO_CURRENCY:
            currency = settings.LANGUAGE_TO_CURRENCY.get(language)

        facet_fields = request.GET.get('facet', '')

        # TODO: better gender handling
        gender = request.GET.get('gender', 'W')

        query_arguments = {'rows': BROWSE_PAGE_SIZE, 'start': 0}
        query_arguments = set_query_arguments(query_arguments, request, facet_fields, gender=gender, currency=currency)
        query_arguments['fq'].append('availability:true')
        query_arguments['fq'].append('gender:(U OR %s)' % (gender,))

        # Sort
        query_arguments['sort'] = request.GET.get('sort', 'popularity desc, created desc')

        # TODO: which fields, template?
        query_arguments['fl'] = 'name'

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
        for key in request.GET.keys():
            if key.startswith('f.'):
                query_arguments[key] = request.GET.get(key)

        search = ApparelSearch(query_string, **query_arguments)

        # Facet
        facet = search.get_facet()['facet_fields']
        result = {}

        # Calculate price range
        if 'price' in facet:
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

            result.update(facet_price=pricerange)

        # Calculate manufacturer
        if 'manufacturer' in facet:
            ids = facet['manufacturer'][::2]
            values = map(int, facet['manufacturer'][1::2])
            manufacturers = []
            for key, value in zip(ids, values):
                split_key = key.rsplit('|', 1)
                manufacturers.append({'id': int(split_key[1]),
                                      'name': split_key[0],
                                      'count': value,})

            result.update(facet_manufacturer=manufacturers)

        # Calculate colors
        if 'color' in facet:
            result.update(facet_color=map_facets(facet['color']))

        # Calculate category
        if 'category' in facet:
            result.update(facet_category=map_facets(facet['category']))

        return HttpResponse(json.dumps(result), mimetype='application/json')


    def get_products(self, request, query_string, query_arguments, *args, **kwargs):
        query_arguments['facet'] = 'false'
        search = ApparelSearch(query_string, **query_arguments)

        # Calculate paginator
        paginator = Paginator(search, BROWSE_PAGE_SIZE)

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

        result.update(products=[x.__dict__ for x in paged_result.object_list])

        return HttpResponse(json.dumps(result), mimetype='application/json')


def map_facets(facet_data, func=int):
    ids = map(func, facet_data[::2])
    values = map(int, facet_data[1::2])
    return [{'id': id, 'count': count} for id, count in zip(ids, values)]
