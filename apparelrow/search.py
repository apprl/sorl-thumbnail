import json

from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.http import Http404
from django.http import HttpResponse
from django.db.models import signals
from django.db.models import get_model
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType

from haystack import site
from haystack.indexes import SearchIndex
from haystack.indexes import CharField
from haystack.indexes import DateTimeField
from haystack.indexes import IntegerField
from haystack.indexes import MultiValueField
from haystack.indexes import NgramField
from haystack.indexes import BooleanField

from apparelrow.apparel.messaging import search_index_update
from apparelrow.apparel.models import Category
from apparelrow.apparel.models import Look
from apparelrow.apparel.models import Manufacturer
from apparelrow.apparel.models import Product
from apparelrow.apparel.models import Wardrobe
from apparelrow.apparel.models import ProductLike

from pysolr import Solr

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 10)
PRODUCT_SEARCH_FIELDS = ['manufacturer_name', 'category_names^40', 'product_name', 'color_names^40', 'description']

def remove_instance_from_index(instance, **kwargs):
    model_class = get_model(instance._meta.app_label, instance._meta.module_name)
    search_index = site.get_index(model_class)
    search_index.remove_object(instance, **kwargs)

class QueuedSearchIndex(SearchIndex):
    """
    A ``SearchIndex`` subclass that enqueues updates for later processing.

    Deletes are handled instantly since a reference, not the instance, is put on the queue. It would not be hard
    to update this to handle deletes as well (with a delete task).
    """
    def _setup_save(self, model):
        signals.post_save.connect(self.enqueue_save, sender=model)

    def _setup_delete(self, model):
        signals.post_delete.connect(self.enqueue_delete, sender=model)

    def _teardown_save(self, model):
        signals.post_save.disconnect(self.enqueue_save, sender=model)

    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)

    def enqueue_save(self, instance, **kwargs):
        if hasattr(instance, 'published') and instance.published == False:
            remove_instance_from_index(instance, **kwargs)
        elif hasattr(instance, 'category') and instance.category == None:
            remove_instance_from_index(instance, **kwargs)
        elif self.should_update(instance, **kwargs):
            search_index_update(instance._meta.app_label, instance._meta.module_name, instance._get_pk_val())

    def enqueue_delete(self, instance, **kwargs):
        remove_instance_from_index(instance, **kwargs)

    def update_objects(self, instances, using=None, **kwargs):
        instances = [x for x in instances if self.should_update(x, **kwargs)]
        self.backend.update(self, instances)

#
# Apparel search (circumvent haystack)
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
    connection = Solr(getattr(settings, 'HAYSTACK_SOLR_URL', 'http://127.0.0.1:8983/solr/'))
    result = connection.more_like_this('id:apparel.product.%s' % (product_id,), 'text', **kwargs)
    return result

class ApparelSearch(object):
    """
    Our own interface with solr
    """
    def __init__(self, query_string, **data):
        self.query_string = query_string
        self.data = data

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

    _result = None
    def _get_results(self, update=False):
        if self._result is None or update:
            self._result = Solr(getattr(settings, 'HAYSTACK_SOLR_URL', 'http://127.0.0.1:8983/solr/')).search(self.query_string, **self.data)
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

class ProductIndex(QueuedSearchIndex):
    """
    Search index for product model.
    """
    text = CharField(document=True, use_template=True, model_attr='product_name', stored=False)
    name = CharField(model_attr='product_name', stored=False)
    created = DateTimeField(model_attr='date_added', stored=False)
    gender = CharField(model_attr='gender', default=None, stored=False)
    price = IntegerField(faceted=True, stored=False)
    color = MultiValueField(faceted=True, stored=False)
    category = MultiValueField(faceted=True, stored=False)
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/product_small_content.html')
    template_mlt = CharField(use_template=True, indexed=False, template_name='apparel/fragments/product_small_no_price.html')
    user_wardrobe = MultiValueField(stored=False)
    user_likes = MultiValueField(stored=False)
    popularity = IntegerField(model_attr='popularity')
    availability = BooleanField(stored=False)

    # Search fields
    product_name = CharField(model_attr='product_name', stored=False, boost=0.5)
    description = CharField(model_attr='description', stored=False, boost=0.4)
    manufacturer_name = CharField(model_attr='manufacturer__name', boost=1.2)
    color_names = CharField(stored=False, boost=1.7)
    category_names = CharField(stored=False, boost=1.7)

    # Manufacturer
    manufacturer_id = CharField(model_attr='manufacturer__id')
    manufacturer_auto = NgramField(model_attr='manufacturer__name')
    manufacturer_data = CharField()

    def prepare(self, object):
        self.prepared_data = super(ProductIndex, self).prepare(object)
        # Add price to search index
        if object.default_vendor and object.default_vendor.price:
            try:
                self.prepared_data['price'] = int(object.default_vendor.price)
            except ValueError:
                pass
        # Add color to search index
        self.prepared_data['color'] = object.options.filter(option_type__name='color').values_list('pk', flat=True)
        # Add category to search index
        self.prepared_data['category'] = Category.objects.get(pk=object.category.id).get_ancestors(ascending=False, include_self=True).values_list('pk', flat=True)
        # Add user to search index
        self.prepared_data['user_wardrobe'] = Wardrobe.objects.filter(products=object).values_list('user__id', flat=True)
        # Add user likes to search index
        self.prepared_data['user_likes'] = ProductLike.objects.filter(product=object, active=True).values_list('user__id', flat=True)
        # Add availability to search index
        # A product is available if atleast one vendorproduct is not sold out (NULL does not count as sold out)
        availability = False
        for available in set(object.vendorproduct.values_list('availability', flat=True)):
            if available != 0:
                availability = True
                break
        self.prepared_data['availability'] = availability
        # Add category names
        self.prepared_data['category_names'] = ' '.join(object.categories_all_languages)
        # Add color names
        self.prepared_data['color_names'] = ' '.join(object.colors)
        # Add manufacturer data
        self.prepared_data['manufacturer_data'] = '%s|%s' % (object.manufacturer.name, object.manufacturer.id)

        return self.prepared_data

    def index_queryset(self):
        return Product.objects.filter(category__isnull=False, vendorproduct__isnull=False, published=True)

    def get_updated_field(self):
        return 'modified'

    def should_update(self, instance, **kwargs):
        return instance.published==True

#
# LookIndex
#

class LookIndex(QueuedSearchIndex):
    """
    Search index for look model.
    """
    text = CharField(document=True, use_template=True, model_attr='title')
    created = DateTimeField(model_attr='created')
    modified = DateTimeField(model_attr='modified')
    user = CharField(model_attr='user__username')
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/look_small_like_content.html')

    def get_updated_field(self):
        return 'modified'

    def index_queryset(self):
        return Look.objects.all()

site.register(Product, ProductIndex)
site.register(Look, LookIndex)

#
# Generic search
#

def search_view(request, model_name):
    """
    Generic search view
    """
    try:
        limit = int(request.GET.get('limit', RESULTS_PER_PAGE))
    except ValueError:
        limit = RESULTS_PER_PAGE

    query = request.GET.get('q')
    if not query:
        return Http404('Search require a search string')

    model_name = model_name.lower()

    # Base arguments
    arguments = {'qf': ['text'],
                 'defType': 'edismax',
                 'fq': ['django_ct:apparel.%s' % (model_name,)],
                 'start': 0,
                 'rows': limit}

    # Filter query parameters based on model name
    if model_name == 'product':
        arguments['fq'].append('availability:true')
        arguments['fq'].append('gender:(W OR M OR U)')
        arguments['qf'] = PRODUCT_SEARCH_FIELDS
    elif model_name == 'look':
        arguments['qf'] = ['text']
    elif model_name == 'manufacturer':
        # override fq cause we do not have a separate manufacturer index
        arguments['fq'] = ['django_ct:apparel.product', 'availability:true', 'gender:(W OR M OR U)']
        arguments['qf'] = ['manufacturer_auto']
        arguments['facet'] = 'on'
        arguments['facet.limit'] = -1
        arguments['facet.mincount'] = 1
        arguments['facet.field'] = ['manufacturer', 'manufacturer_data']

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
                split = value.rsplit('|')
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
        object_list = [render_to_string('apparel/fragments/manufacturer_search.html', {'object': obj}) for obj in paged_result.object_list]

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
