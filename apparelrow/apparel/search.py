import json
import decimal
import logging
import re

from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import Http404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models.loading import get_model
from django.utils import translation

from apparelrow.apparel.models import Product, ProductLike, Look
from apparelrow.apparel.utils import get_gender_from_cookie
from apparelrow.apparel.tasks import product_popularity

from sorl.thumbnail import get_thumbnail

from pysolr import Solr

logger = logging.getLogger('apparel.search')

RESULTS_PER_PAGE = 10
PRODUCT_SEARCH_FIELDS = ['manufacturer_name', 'category_names^40', 'product_name', 'color_names^40', 'description']

REGEX_STRIP = re.compile('[^\w ]', re.U)

#
# Apparel search
#

class ResultContainer:
    """
    Result container, used for converting from dict to object
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)

def more_like_this_product(body, gender, limit):
    kwargs = {'fq': ['django_ct:apparel.product', 'published:true', 'availability:true', 'gender:%s' % (gender,)], 'rows': limit}
    kwargs['stream.body'] = body
    mlt_fields = ['manufacturer_name', 'category_names', 'product_name', 'color_names', 'description']
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    result = connection.more_like_this('', mlt_fields, **kwargs)
    return result

def more_alternatives(product, limit):
    colors_pk = list(map(str, product.options.filter(option_type__name='color').values_list('pk', flat=True)))
    language_currency = settings.LANGUAGE_TO_CURRENCY.get(translation.get_language(), settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': limit, 'start': 0,
                       'fl': 'template_mlt',
                       'sort': 'price asc, popularity desc, created desc'}
    query_arguments['fq'] = ['availability:true', 'django_ct:apparel.product']
    query_arguments['fq'].append('gender:(%s OR U)' % (product.gender,))
    query_arguments['fq'].append('category:%s' % (product.category_id))
    if colors_pk:
        query_arguments['fq'].append('color:(%s)' % (' OR '.join(colors_pk),))
    search = ApparelSearch('*:*', **query_arguments)
    docs = search.get_docs()
    if docs:
        shop_reverse = 'shop-men' if product.gender == 'M' else 'shop-women'
        shop_url = '%s#category=%s' % (reverse(shop_reverse), product.category_id)
        if colors_pk:
            shop_url = '%s&color=%s' % (shop_url, ','.join(colors_pk))

        return docs, shop_url

    return None, None

#def more_like_this_product(product_id, product_gender, limit):
    #kwargs = {'fq': ['django_ct:apparel.product', 'published:true', 'availability:true', 'gender:%s' % (product_gender,)],
              #'rows': limit}
    #mlt_fields = ['manufacturer_name', 'category_names', 'product_name', 'color_names', 'description']
    #connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    #result = connection.more_like_this('id:apparel.product.%s' % (product_id,), mlt_fields, **kwargs)
    #return result

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

    def get_stats(self):
        """
        Get stats
        """
        return self._get_results().stats

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

def clean_index(app_label=None, module_name=None):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))

    if app_label and module_name:
        connection.delete(q=('django_ct:%s.%s' % (app_label, module_name)))
    else:
        connection.delete(q='*:*')

#
# ProductIndex
#

@receiver(post_save, sender=Product, dispatch_uid='product_save')
def product_save(instance, **kwargs):
    if not hasattr(instance, 'id'):
        return

    # If this post save signal is from a product popularity update we do not
    # need to update the product in our search index.
    if 'update_fields' in kwargs and kwargs['update_fields'] and len(kwargs['update_fields']) == 1 and 'popularity' in kwargs['update_fields']:
        return

    if 'solr' in kwargs and kwargs['solr']:
        connection = kwargs['solr']
    else:
        connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))

    document, boost = get_product_document(instance)

    if document is not None:
        if 'commit' in kwargs and kwargs['commit']:
            connection.add([document], commit=True, boost=boost)
        else:
            connection.add([document], commit=False, boost=boost, commitWithin=False)

@receiver(post_delete, sender=Product, dispatch_uid='product_delete')
def product_delete(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

@receiver(post_save, sender=ProductLike, dispatch_uid='product_like_save')
def product_like_save(instance, **kwargs):
    product_save(instance.product)

@receiver(post_delete, sender=ProductLike, dispatch_uid='product_like_delete')
def product_like_delete(instance, **kwargs):
    product_save(instance.product)

def rebuild_product_index():
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    product_count = 0

    for product in get_model('apparel', 'Product').objects.filter(likes__isnull=False):
        product_save(product, solr=connection)
        product_count = product_count + 1

    for product in get_model('apparel', 'Product').valid_objects.iterator():
        product_save(product, solr=connection)
        product_count = product_count + 1

    return product_count

def get_product_document(instance):
    document = {
        'id': '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk),
        'django_ct': '%s.%s' % (instance._meta.app_label, instance._meta.module_name),
        'django_id': instance.pk,
        'published': False
    }
    boost = {}

    if instance.published == True and instance.category and instance.manufacturer and instance.gender:
        availability = instance.availability
        discount = False
        price = stored_price = stored_discount = decimal.Decimal('0.0')
        currency = 'EUR'
        if instance.default_vendor:
            discount = instance.default_vendor.original_discount_price > decimal.Decimal('0.0')
            price = instance.default_vendor.original_price
            currency = instance.default_vendor.original_currency
            stored_price = instance.default_vendor.original_price
            if instance.default_vendor.original_discount_price:
                price = instance.default_vendor.original_discount_price
                stored_discount = instance.default_vendor.original_discount_price
        else:
            # If availability is true but product has no default vendor we do
            # not need to add the product to solr, return None and 0
            if availability:
                logger.error('Availability is true, but product have no vendorproduct [PID: %s]' % (instance.pk,))
                availability = False
                return None, 0

        color_names = []
        color_ids = []
        color_data = instance.options.filter(option_type__name__in=['color', 'pattern']).exclude(value__exact='').values_list('pk', 'value')
        if color_data:
            color_ids, color_names = zip(*color_data)
        color_names = ' '.join(color_names)

        category_data = instance.category.get_ancestors(ascending=False, include_self=True).values_list('pk', 'name_en', 'name_sv')
        category_ids, category_en_names, category_sv_names = zip(*category_data)
        category_names = ' '.join(category_en_names + category_sv_names)

        user_likes = list(get_model('apparel', 'ProductLike').objects.filter(product=instance, active=True).values_list('user__id', flat=True))

        likes = list(get_model('apparel', 'ProductLike').objects.filter(product=instance, active=True).values_list('user__id', 'modified'))
        user_likes = [x[0] for x in likes]

        has_looks = get_model('apparel', 'Look').published_objects.filter(components__product=instance).exists()

        template_browse = render_to_string('apparel/fragments/product_shop.html', {'object': instance, 'has_looks': has_looks})
        template_mlt = render_to_string('apparel/fragments/product_small_no_price.html', {'object': instance})

        document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
        document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
        document['django_id'] = instance.pk
        document['name'] = instance.product_name

        # Search fields
        document['product_name'] = instance.product_name
        document['description'] = instance.description
        document['manufacturer_name'] = instance.manufacturer.name
        document['color_names'] = color_names
        document['category_names'] = category_names

        # Facets
        document['color'] = color_ids
        document['price'] = '%s,%s' % (price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)
        document['category'] = category_ids
        document['manufacturer_id'] = instance.manufacturer_id

        # Filters
        document['gender'] = instance.gender
        document['popularity'] = product_popularity(instance)
        document['availability'] = availability
        document['discount'] = discount
        document['published'] = instance.published

        # Templates and stored fields
        document['template'] = template_browse
        document['template_mlt'] = template_mlt
        document['slug'] = instance.slug
        document['stored_price'] = '%s,%s' % (stored_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)
        document['stored_discount'] = '%s,%s' % (stored_discount.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)

        # Images
        # XXX: during popularity script: IOError: image file is truncated (23
        # bytes not processed)
        # This
        try:
            document['image_small'] = get_thumbnail(instance.product_image, '112x145', crop=False, format='PNG', transparent=True).url
            document['image_medium'] = get_thumbnail(instance.product_image, '224x291', crop=False, format='PNG', transparent=True).url
        except IOError:
            return None, 0

        # Dates
        document['created'] = instance.date_added

        # Users
        document['user_likes'] = user_likes
        for x in likes:
            document['%s_uld' % (x[0],)] = x[1]

        # Store
        if instance.default_vendor:
            document['store_id'] = instance.default_vendor.vendor_id
            document['store'] = '%s|%s' % (instance.default_vendor.vendor.name, instance.default_vendor.vendor_id)
            document['store_auto'] = instance.default_vendor.vendor.name

        # Brand
        document['manufacturer_auto'] = instance.manufacturer.name
        manufacturer_lower = REGEX_STRIP.sub('', instance.manufacturer.name.lower())
        document['manufacturer'] = '%s|%s|%s' % (manufacturer_lower, instance.manufacturer.name, instance.manufacturer_id)

        boost = {'product_name': '0.5', 'description': '0.4', 'manufacturer_name': '1.2'}

    return document, boost

#
# LookIndex
#

@receiver(post_save, sender=Look, dispatch_uid='look_save')
def look_save(instance, **kwargs):
    if 'solr' in kwargs and kwargs['solr']:
        connection = kwargs['solr']
    else:
        connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))

    document, boost = get_look_document(instance)
    connection.add([document], commit=False, boost=boost, commitWithin=False)

@receiver(post_delete, sender=Look, dispatch_uid='look_delete')
def look_delete(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

def rebuild_look_index():
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    look_count = 0
    for look in get_model('apparel', 'Look').objects.iterator():
        look_save(look, solr=connection)
        look_count = look_count + 1

    return look_count

def get_look_document(instance):
    boost = {}
    document = {}
    document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
    document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
    document['django_id'] = instance.pk
    document['gender'] = instance.gender
    document['created'] = instance.created
    document['modified'] = instance.modified
    document['name'] = instance.title
    document['description'] = instance.description
    product_manufacturers = instance.product_manufacturers
    if product_manufacturers and product_manufacturers[0]:
        document['manufacturer_name'] = ', '.join(product_manufacturers)
    document['template'] = render_to_string('apparel/fragments/look_search_content.html', {'object': instance})
    document['published'] = instance.published

    return document, boost


#
# Profile index (brands not counted)
#

@receiver(post_save, sender=get_user_model(), dispatch_uid='search_index_user_save')
def search_index_user_save(instance, **kwargs):
    if 'solr' in kwargs and kwargs['solr']:
        connection = kwargs['solr']
    else:
        connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))

    if not instance.is_brand:
        document, boost = get_profile_document(instance)
        connection.add([document], commit=False, boost=boost, commitWithin=False)

@receiver(post_delete, sender=get_user_model(), dispatch_uid='search_index_user_delete')
def search_index_user_delete(instance, **kwargs):
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

def rebuild_user_index():
    connection = Solr(getattr(settings, 'SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    user_count = 0
    for user in get_user_model().objects.filter(is_brand=False).iterator():
        search_index_user_save(user, solr=connection)
        user_count = user_count + 1

    return user_count

def get_profile_document(instance):
    boost = {}
    document = {}
    document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
    document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
    document['django_id'] = instance.pk
    document['name'] = instance.display_name
    document['gender'] = instance.gender
    document['template'] = render_to_string('apparel/fragments/profile_search_content.html', {'object': instance})

    return document, boost

def decode_manufacturer_facet(data):
    name_combo, ident = data.rsplit('|', 1)
    lower_name, name = name_combo.split('|', 1)

    return int(ident), name, lower_name

def decode_store_facet(data):
    name, ident = data.rsplit('|', 1)

    return int(ident), name


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

    app_label = 'apparel'
    if model_name == 'user':
        app_label = 'profile'

    # Base arguments
    arguments = {'qf': ['text'],
                 'defType': 'edismax',
                 'fq': ['django_ct:%s.%s' % (app_label, model_name,)],
                 'start': 0,
                 'rows': limit}

    # Filter query parameters based on model name
    if model_name == 'product':
        arguments['fq'].append('availability:true')
        arguments['fq'].append('published:true')
        arguments['fq'].append(gender_field)
        arguments['qf'] = PRODUCT_SEARCH_FIELDS
    elif model_name == 'look':
        arguments['qf'] = ['text']
        arguments['fq'].append(gender_field)
        arguments['fq'].append('published:true')
    elif model_name == 'user':
        arguments['qf'] = ['text']
    elif model_name == 'store':
        # override fq cause we do not have a separate store index
        arguments['fq'] = ['django_ct:apparel.product', 'availability:true', gender_field, 'published:true']
        arguments['qf'] = ['store_auto']
        arguments['facet'] = 'on'
        arguments['facet.limit'] = -1
        arguments['facet.mincount'] = 1
        arguments['facet.field'] = ['store']
    elif model_name == 'manufacturer':
        # override fq cause we do not have a separate manufacturer index
        arguments['fq'] = ['django_ct:apparel.product', 'availability:true', gender_field, 'published:true']
        arguments['qf'] = ['manufacturer_auto']
        arguments['facet'] = 'on'
        arguments['facet.limit'] = -1
        arguments['facet.mincount'] = 1
        arguments['facet.field'] = ['manufacturer']

    # Used in look image to bring up popup with products
    ids = request.GET.get('ids', False)
    if ids:
        arguments['fq'].append(' django_id:(%s)' % (ids.replace(',', ' OR '),))

    results = ApparelSearch(query, **arguments)

    # If the model name is manufacturer get the result from a facet
    if model_name == 'manufacturer':
        facet = results.get_facet()['facet_fields']
        results = []
        for i, value in enumerate(facet['manufacturer']):
            if i % 2 == 0:
                id, name, _ = decode_manufacturer_facet(value)
                results.append({'id': int(id), 'name': name})

    if model_name == 'store':
        facet = results.get_facet()['facet_fields']
        results = []
        for i, value in enumerate(facet['store']):
            if i % 2 == 0:
                store_id, name = decode_store_facet(value)
                results.append({'id': store_id, 'name': name})

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
    elif model_name == 'user':
        object_list = [o.template for o in paged_result.object_list if o]
    elif model_name == 'manufacturer':
        object_list = [render_to_string('apparel/fragments/manufacturer_search.html', {'object': obj, 'gender': gender}) for obj in paged_result.object_list]
    elif model_name == 'store':
        object_list = [render_to_string('apparel/fragments/store_search.html', {'object': obj, 'gender': gender}) for obj in paged_result.object_list]

    return HttpResponse(
        json.dumps({
            'object_list': object_list,
            'number': paged_result.number,
            'paginator': {
                'num_pages': paged_result.paginator.num_pages,
                'count': paged_result.paginator.count,
            }
        }),
        mimetype='application/json'
    )
