from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import InvalidPage
from django.core.paginator import EmptyPage
from django.http import Http404
from django.http import HttpResponse
from django.db.models import get_model

from hanssonlarsson.django.exporter import json

from haystack import site
from haystack.indexes import SearchIndex
from haystack.indexes import CharField
from haystack.indexes import DateTimeField
from haystack.forms import ModelSearchForm
from haystack.query import EmptySearchQuerySet
from haystack.query import SearchQuerySet

from apparelrow.apparel.models import Product
from apparelrow.apparel.models import Manufacturer
from apparelrow.apparel.models import Look

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 10)

class ProductIndex(SearchIndex):
    """
    Search index for product model.
    """
    text = CharField(document=True, use_template=True, model_attr='product_name')
    description = CharField(model_attr='description')
    created = DateTimeField(model_attr='date_added')
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/product_small_content.html')

    def index_queryset(self):
        return Product.objects.filter(category__isnull=False, vendorproduct__isnull=False, published=True)


class ManufacturerIndex(SearchIndex):
    """
    Search index for manufacturer model.
    """
    text = CharField(document=True, use_template=True, model_attr='name')
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/manufacturer_search.html')

    def index_queryset(self):
        return Manufacturer.objects.filter(product__published=True)


class LookIndex(SearchIndex):
    """
    Search index for look model.
    """
    text = CharField(document=True, use_template=True, model_attr='title')
    created = DateTimeField(model_attr='created')
    modified = DateTimeField(model_attr='modified')
    user = CharField(model_attr='user__username')
    template = CharField(use_template=True, indexed=False, template_name='apparel/fragments/look_small_like_content.html')

    def index_queryset(self):
        return Look.objects.all()

site.register(Product, ProductIndex)
site.register(Manufacturer, ManufacturerIndex)
site.register(Look, LookIndex)


def search_view(request, model):
    query = ''
    results = EmptySearchQuerySet()
    try:
        limit = int(request.GET.get('limit', RESULTS_PER_PAGE))
    except ValueError:
        limit = RESULTS_PER_PAGE

    class_name = model.lower()
    model_class = get_model('apparel', class_name)
    if model_class is None:
        raise Exception('No model to search for')

    sqs = SearchQuerySet().models(model_class)
    # FIXME: Do we really need a form when this is only accessed through ajax
    if request.GET.get('q'):
        form = ModelSearchForm(request.GET, searchqueryset=sqs, load_all=True)
        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
    else:
        return Http404('Search require a search string')

    paginator = Paginator(results, limit)

    try:
        paged_result = paginator.page(int(request.GET.get('page', 1)))
    except (EmptyPage, InvalidPage):
        paged_result = paginator.page(paginator.num_pages)
    except ValueError:
        paged_result = paginator.page(1)

    return HttpResponse(
        # FIXME: is the special json encoder that dives through all lazy
        # attributes necessary?
        json.encode(get_pagination_as_dict(paged_result)),
        mimetype='application/json'
    )

def get_pagination_as_dict(paged_result):
    # FIXME: This exists because the JSON exporter is unable to serialise
    # Page and Pagination objects. Perhaps this code could be moved to the
    # exporter module instead?
    return {
        #'object_list': [o.object for o in paged_result.object_list],
        'object_list': [o.template for o in paged_result.object_list],
        'previous_page_number': paged_result.previous_page_number(),
        'next_page_number': paged_result.next_page_number(),
        'number': paged_result.number,
        'paginator': {
            'num_pages': paged_result.paginator.num_pages,
            'count': paged_result.paginator.count,
        },
    }
