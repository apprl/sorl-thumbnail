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
from haystack.query import SearchQuerySet

from apparelrow.apparel.messaging import search_index_update
from apparelrow.apparel.models import Category
from apparelrow.apparel.models import Look
from apparelrow.apparel.models import Manufacturer
from apparelrow.apparel.models import Product
from apparelrow.apparel.models import Wardrobe
from apparelrow.apparel.models import ProductLike

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 10)

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
        if self.should_update(instance, **kwargs):
            search_index_update(instance._meta.app_label, instance._meta.module_name, instance._get_pk_val())

    def enqueue_delete(self, instance, **kwargs):
        remove_instance_from_index(instance, **kwargs)

    def update_objects(self, instances, using=None, **kwargs):
        instances = [x for x in instances if self.should_update(x, **kwargs)]
        self.backend.update(self, instances)

class ProductIndex(QueuedSearchIndex):
    """
    Search index for product model.
    """
    text = CharField(document=True, use_template=True, model_attr='product_name', stored=False)
    name = CharField(model_attr='product_name', stored=False)
    created = DateTimeField(model_attr='date_added', stored=False)
    gender = CharField(model_attr='gender', default=None, stored=False)
    manufacturer = CharField(model_attr='manufacturer__id', faceted=True, stored=False)
    price = IntegerField(faceted=True, stored=False)
    color = MultiValueField(faceted=True, stored=False)
    category = MultiValueField(faceted=True, stored=False)
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/product_small_content.html')
    template_mlt = CharField(use_template=True, indexed=False, template_name='apparel/fragments/product_small_no_price.html')
    user_wardrobe = MultiValueField(stored=False)
    user_likes = MultiValueField(stored=False)
    popularity = IntegerField(model_attr='popularity')
    availability = BooleanField(stored=False)

    #description = CharField(model_attr='description', stored=False)
    #color_name = MultiValueField(stored=False)
    #manufacturer_name = CharField(model_attr='manufacturer__name', stored=False)
    #categories = CharField(stored=False)

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

        # Add categories
        #self.prepared_data['categories'] = object.categories_all_languages
        # Add color names
        #self.prepared_data['color_names'] = object.options.filter(option_type__name='color').values_list('value', flat=True)

        return self.prepared_data

    def index_queryset(self):
        return Product.objects.filter(category__isnull=False, vendorproduct__isnull=False, published=True)

    def get_updated_field(self):
        return 'modified'

    def should_update(self, instance, **kwargs):
        return instance.published==True

class ManufacturerIndex(QueuedSearchIndex):
    """
    Search index for manufacturer model.
    """
    text = CharField(document=True, use_template=True, model_attr='name')
    manufacturer_id = IntegerField(model_attr='id')
    name = CharField(model_attr='name')
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/manufacturer_search.html')
    auto = NgramField(model_attr='name')

    def index_queryset(self):
        return Manufacturer.objects.filter(product__published=True).distinct()

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
site.register(Manufacturer, ManufacturerIndex)
site.register(Look, LookIndex)


def search_view(request, model):
    try:
        limit = int(request.GET.get('limit', RESULTS_PER_PAGE))
    except ValueError:
        limit = RESULTS_PER_PAGE

    ids = request.GET.get('ids', None)
    class_name = model.lower()
    model_class = get_model('apparel', class_name)
    if model_class is None:
        raise Exception('No model to search for')

    sqs = SearchQuerySet().models(model_class)
    if class_name == 'product':
        sqs = sqs.narrow('availability:true')
        sqs = sqs.order_by('-popularity')

    if ids:
        sqs = sqs.narrow('django_id:(%s)' % (ids.replace(',', ' OR '),))

    if request.GET.get('q'):
        #sqs = sqs.filter(content=sqs.query.clean(request.GET.get('q')))
        sqs = sqs.auto_query(request.GET.get('q'))
    else:
        return Http404('Search require a search string')

    paginator = Paginator(sqs, limit)

    try:
        paged_result = paginator.page(int(request.GET.get('page', 1)))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    except ValueError:
        paged_result = paginator.page(1)

    if request.GET.get('thumb', None):
        object_list = []
        for obj in paged_result.object_list:
            if obj:
                object_list.append({
                    'id': obj.object.id,
                    'template': render_to_string('apparel/fragments/product_thumb_no_cache.html', {'product': obj.object})
                })
    else:
        object_list = [o.template for o in paged_result.object_list if o]

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
