import json
import decimal

from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import Http404
from django.http import HttpResponse
from django.template.loader import render_to_string

from apparel.models import Look
from apparel.models import Product
from apparel.models import ProductLike
from apparel.utils import get_gender_from_cookie

from pysolr import Solr

RESULTS_PER_PAGE = 10
PRODUCT_SEARCH_FIELDS = ['manufacturer_name', 'category_names^40', 'product_name', 'color_names^40', 'description']

#
# Apparel search
#

class ResultContainer:
    """
    Result container, used for converting from dict to object
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)

def more_like_this_product(product_id, product_gender, limit):
    kwargs = {'fq': ['django_ct:apparel.product', 'availability:true', 'gender:%s' % (product_gender,)],
              'rows': limit}
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    result = connection.more_like_this('id:apparel.product.%s' % (product_id,), 'text', **kwargs)
    return result

class ApparelSearch(object):
    """
    Our own interface with solr
    """
    def __init__(self, query_string, connection=None, **data):
        self.query_string = query_string
        self.data = data
        self.connection = connection

    def __len__(self):
        return self._get_results().hits

    def get_facet(self):
        """
        Get facet results
        """
        return self._get_results().facets

    def get_docs(self):
        """
        Get docs
        """
        return self._get_results().docs

    def get_grouped(self):
        """
        Get grouped
        """
        return self._get_results().grouped

    _result = None
    def _get_results(self, update=False):
        if self._result is None or update:
            if self.connection is None:
                self.connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
            self._result = self.connection.search(self.query_string, **self.data)
            self._result.docs = [ResultContainer(**element) for element in self._result.docs]

        return self._result

    def __getitem__(self, k):
        """
        Support both slice or single element access
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError

        if isinstance(k, slice):
            paginate_opts = {}

            if k.start is not None:
                paginate_opts['start'] = int(k.start)

            if k.stop is None:
                stop = len(self)
            else:
                stop = min(k.stop, len(self))

            paginate_opts['rows'] = stop - int(k.start)

            if self.data['start'] != paginate_opts['start'] or self.data['rows'] != paginate_opts['rows']:
                self.data.update(paginate_opts)
                return self._get_results(True)

            return self._get_results()

        return self._get_results()[k]

#
# ProductIndex
#

@receiver(post_save, sender=Product, dispatch_uid='product_save')
def product_save(instance, **kwargs):
    if hasattr(instance, 'published') and instance.published == False:
        product_delete(instance, **kwargs)
    elif hasattr(instance, 'category') and instance.category is None:
        product_delete(instance, **kwargs)
    elif instance.published == True and instance.category is not None:
        connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
        document, boost = get_product_document(instance)
        if 'commit' in kwargs and kwargs['commit']:
            connection.add([document], commit=True, boost=boost)
        else:
            connection.add([document], commit=False, boost=boost, commitWithin=getattr(settings, 'SOLR_COMMIT_WITHIN', 30000))

@receiver(post_delete, sender=Product, dispatch_uid='product_delete')
def product_delete(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

@receiver(post_save, sender=ProductLike, dispatch_uid='product_like_save')
def product_like_save(instance, **kwargs):
    product_save(instance.product, commit=True)

@receiver(post_delete, sender=ProductLike, dispatch_uid='product_like_delete')
def product_like_delete(instance, **kwargs):
    product_delete(instance.product)

def get_product_document(instance):
    availability = False
    discount = False
    price = decimal.Decimal('0.0')
    if instance.default_vendor:
        availability = instance.default_vendor.availability != 0
        discount = instance.default_vendor.discount_price is not None
        price = instance.default_vendor.price
        if instance.default_vendor.discount_price:
            price = instance.default_vendor.discount_price

    color_names = []
    color_ids = []
    color_data = instance.options.filter(option_type__name__in=['color', 'pattern']).exclude(value__exact='').values_list('pk', 'value')
    if color_data:
        color_ids, color_names = zip(*color_data)
    color_names = ' '.join(color_names)

    category_data = instance.category.get_ancestors(ascending=False, include_self=True).values_list('pk', 'name_en', 'name_sv')
    category_ids, category_en_names, category_sv_names = zip(*category_data)
    category_names = ' '.join(category_en_names + category_sv_names)

    user_likes = list(ProductLike.objects.filter(product=instance, active=True).values_list('user__id', flat=True))

    template_browse = render_to_string('apparel/fragments/product_small_content.html', {'object': instance})
    template_mlt = render_to_string('apparel/fragments/product_small_no_price.html', {'object': instance})

    document = {}
    document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
    document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
    document['django_id'] = instance.pk

    # Search fields
    document['product_name'] = instance.product_name
    document['description'] = instance.description
    document['manufacturer_name'] = instance.manufacturer.name
    document['color_names'] = color_names
    document['category_names'] = category_names

    # Facets
    document['color'] = color_ids
    document['price'] = int(price.quantize(decimal.Decimal('1.'), rounding=decimal.ROUND_HALF_UP))
    document['category'] = category_ids
    document['manufacturer_id'] = instance.manufacturer_id

    # Filters
    document['gender'] = instance.gender
    document['popularity'] = instance.popularity
    document['availability'] = availability
    document['discount'] = discount

    # Templates
    document['template'] = template_browse
    document['template_mlt'] = template_mlt

    # Dates
    document['created'] = instance.date_added

    # Users
    document['user_likes'] = user_likes

    # Manufacturer
    document['manufacturer_auto'] = instance.manufacturer.name
    document['manufacturer_data'] = '%s|%s' % (instance.manufacturer.name, instance.manufacturer_id)

    boost = {'product_name': '0.5', 'description': '0.4', 'manufacturer_name': '1.2'}

    return document, boost

#
# LookIndex
#

@receiver(post_save, sender=Look, dispatch_uid='look_save')
def look_save(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    document, boost = get_look_document(instance)
    connection.add([document], commit=False, boost=boost, commitWithin=getattr(settings, 'SOLR_COMMIT_WITHIN', 30000))

@receiver(post_delete, sender=Look, dispatch_uid='look_delete')
def look_delete(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

def get_look_document(instance):
    boost = {}
    document = {}
    document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
    document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
    document['django_id'] = instance.pk
    document['gender'] = instance.gender
    document['created'] = instance.created
    document['modified'] = instance.modified
    document['user'] = instance.user.username
    document['template'] = render_to_string('apparel/fragments/look_small_like_content.html', {'object': instance})
    document['text'] = render_to_string('search/indexes/apparel/look_text.txt', {'object': instance})

    return document, boost

#
# Generic search
#

def search_view(request, model_name):
    """
    Generic search view
    """
    try:
        limit = int(request.REQUEST.get('limit', RESULTS_PER_PAGE))
    except ValueError:
        limit = RESULTS_PER_PAGE

    query = request.REQUEST.get('q')
    if not query:
        raise Http404()

    model_name = model_name.lower()

    # Gender field
    gender = get_gender_from_cookie(request)
    if not gender:
        gender_field = 'gender:(U OR M OR W)'
    else:
        gender_field = 'gender:(U OR %s)' % (gender,)

    # Base arguments
    arguments = {'qf': ['text'],
                 'defType': 'edismax',
                 'fq': ['django_ct:apparel.%s' % (model_name,)],
                 'start': 0,
                 'rows': limit}

    # Filter query parameters based on model name
    if model_name == 'product':
        arguments['fq'].append('availability:true')
        arguments['fq'].append(gender_field)
        arguments['qf'] = PRODUCT_SEARCH_FIELDS
    elif model_name == 'look':
        arguments['qf'] = ['text']
        arguments['fq'].append(gender_field)
    elif model_name == 'manufacturer':
        # override fq cause we do not have a separate manufacturer index
        arguments['fq'] = ['django_ct:apparel.product', 'availability:true', gender_field]
        arguments['qf'] = ['manufacturer_auto']
        arguments['facet'] = 'on'
        arguments['facet.limit'] = -1
        arguments['facet.mincount'] = 1
        arguments['facet.field'] = ['manufacturer_data']

    # Used in look image to bring up popup with products
    ids = request.GET.get('ids', False)
    if ids:
        arguments['fq'].append(' django_id:(%s)' % (ids.replace(',', ' OR '),))

    results = ApparelSearch(query, **arguments)

    # If the model name is manufacturer get the result from a facet
    if model_name == 'manufacturer':
        facet = results.get_facet()['facet_fields']
        results = []
        for i, value in enumerate(facet['manufacturer_data']):
            if i % 2 == 0:
                split = value.rsplit('|', 1)
                results.append({'id': int(split[1]), 'name': split[0]})

    paginator = Paginator(results, limit)
    try:
        paged_result = paginator.page(int(request.GET.get('page', 1)))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    except ValueError:
        paged_result = paginator.page(1)

    # Return object list based on model name
    if model_name == 'product':
        object_list = [o.template for o in paged_result.object_list if o]
    elif model_name == 'look':
        object_list = [o.template for o in paged_result.object_list if o]
    elif model_name == 'manufacturer':
        object_list = [render_to_string('apparel/fragments/manufacturer_search.html', {'object': obj, 'gender': gender}) for obj in paged_result.object_list]

    return HttpResponse(
        json.dumps({
            'object_list': object_list,
            'previous_page_number': paged_result.previous_page_number(),
            'next_page_number': paged_result.next_page_number(),
            'number': paged_result.number,
            'paginator': {
                'num_pages': paged_result.paginator.num_pages,
                'count': paged_result.paginator.count,
            }
        }),
        mimetype='application/json'
    )
