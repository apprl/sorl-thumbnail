import json
import decimal
import logging
from django.views.generic import TemplateView
from progressbar import ProgressBar, Percentage, Bar
import re
import collections
import HTMLParser

from django.conf import settings
from django.shortcuts import render
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

from apparelrow.apparel.models import Product, ProductLike, Look, ShopProduct
from apparelrow.apparel.utils import select_from_multi_gender, get_location, get_gender_url
from apparelrow.apparel.tasks import product_popularity
from sorl.thumbnail import get_thumbnail

from pysolr import Solr, SolrError, Results

logger = logging.getLogger('apparelrow')

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

def more_like_this_product(body, gender, location, limit):
    kwargs = {'fq': ['django_ct:apparel.product', 'published:true', 'availability:true', 'gender:{}'.format(gender)], 'rows': limit, 'fl': 'image_small,slug'}
    kwargs['stream.body'] = body
    kwargs['fq'].append('market_ss:{location}'.format(location=location))

    mlt_fields = ['manufacturer_name', 'category_names', 'product_name', 'color_names', 'description']
    connection = Solr(settings.SOLR_URL)
    try:
        result = connection.more_like_this('', mlt_fields, **kwargs)
    except SolrError as ex:
        logger.error("Failed to get more like this from SOLR, reason [{}] connection [{}]".format(ex.message, settings.SOLR_URL))
        result = Results({}, 0)
    return result

def more_alternatives(product, location, limit):
    colors_pk = list(map(str, product.colors_pk))
    language_currency = settings.LANGUAGE_TO_CURRENCY.get(translation.get_language(), settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': limit, 'start': 0,
                       'fl': 'image_small,slug',
                       'sort': 'price asc, popularity desc, created desc'}
    query_arguments['fq'] = ['availability:true', 'django_ct:apparel.product']
    query_arguments['fq'].append('gender:({gender} OR U)'.format(gender=product.gender))
    query_arguments['fq'].append('category:{category}'.format(category=product.category_id))
    query_arguments['fq'].append('market_ss:{location}'.format(location=location))
    if colors_pk:
        query_arguments['fq'].append('color:({colors})'.format(colors=' OR '.join(colors_pk)))
    search = ApparelSearch('*:*', **query_arguments)
    docs = search.get_docs()
    if docs:
        shop_url = '{shop_url}?category={category}'.format(shop_url=get_gender_url(product.gender, 'shop'),
                                                           category=product.category_id)
        if colors_pk:
            shop_url = '{full_shop_url}&color={colors}'.format(full_shop_url=shop_url, colors=','.join(colors_pk))

        return docs, shop_url

    return None, None

#def more_like_this_product(product_id, product_gender, limit):
    #kwargs = {'fq': ['django_ct:apparel.product', 'published:true', 'availability:true', 'gender:%s' % (product_gender,)],
              #'rows': limit}
    #mlt_fields = ['manufacturer_name', 'category_names', 'product_name', 'color_names', 'description']
    #connection = Solr(settings.SOLR_URL)
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
                self.connection = Solr(settings.SOLR_URL)
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

def clean_index(app_label=None, module_name=None, url=None):
    connection = Solr(url or settings.SOLR_URL)

    if app_label and module_name:
        connection.delete(q=('django_ct:%s.%s' % (app_label, module_name)))
    else:
        connection.delete(q='*:*')

#
# ProductIndex
#

# Todo: Move this method to the corresponding models.py that contain the Product method its attached to.
@receiver(post_save, sender=Product, dispatch_uid='product_save')
def product_save(instance, **kwargs):
    if not hasattr(instance, 'id'):
        return

    # If this post save signal is a result of only a date update we do not have to update the search index either
    #if kwargs and "imported_date" in kwargs.keys():
    if 'update_fields' in kwargs and kwargs['update_fields'] and len(kwargs['update_fields']) == 1 and 'modified' in kwargs['update_fields']:
        logger.info(kwargs.get('update_fields', None))
        return

    # If this post save signal is from a product popularity update we do not
    # need to update the product in our search index.
    if 'update_fields' in kwargs and kwargs['update_fields'] and len(kwargs['update_fields']) == 1 and 'popularity' in kwargs['update_fields']:
        return

    if 'solr' in kwargs and kwargs['solr']:
        connection = kwargs['solr']
    else:
        connection = Solr(settings.SOLR_URL)

    document, boost = get_product_document(instance)

    if document is not None and document['published']:
        if 'commit' in kwargs and kwargs['commit']:
            connection.add([document], commit=True, boost=boost)
        else:
            connection.add([document], commit=False, boost=boost, commitWithin=False)
    elif document is not None and not document['published']:
        result = ApparelSearch('id:apparel.product.%s AND published:true' % (instance.id,), connection=connection)
        if len(result) == 1:
            connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.id))

@receiver(post_delete, sender=Product, dispatch_uid='product_delete')
def product_delete(instance, **kwargs):
    """
    Removes the product from the SOLR index and also deletes any lingering thumbnails
    :param instance:
    :param kwargs:
    :return:
    """
    from sorl.thumbnail.images import ImageFile as SorlImageFile, deserialize_image_file
    from sorl.thumbnail import default
    from theimp.models import Product as ImpProduct
    sorl_image = None
    try:
        logger.info(u"Trying to remove image and thumbnails for {}".format(instance))
        sorl_image = SorlImageFile(instance.product_image)
        try:
            default.kvstore.delete_thumbnails(sorl_image)
            default.kvstore.delete(sorl_image)
        except:
            logger.warn(u"Failed to remove thumbnails for product {}.".format(instance.pk))
    except:
        logger.warn(u"Failed to remove image, could not load the sorl image wrapper for product {}.".format(instance.pk))
    finally:
        image_name = instance.product_image.name
        # Todo: Check if the image is used somewhere else, if it is do not remove it. This method is post_delete so object
        # using this image is already removed.
        uses = Product.objects.filter(product_image=image_name).count()
        if uses == 0 and sorl_image and sorl_image.exists() and not "image_not_available" in image_name:
           sorl_image.delete()

    logger.info(u"Trying to clean up theimp.Product: {}".format(instance.product_key))
    try:
        if ImpProduct.objects.filter(key=instance.product_key).exists():
            product = ImpProduct.objects.get(key=instance.product_key)
            logger.info(u"Cleaning out Imp product: {}".format(product.id))
            product.delete()
    except:
        logger.warn(u"Unable to clean out Imp product corresponding to: {}".format(instance.product_key))


    connection = Solr(settings.SOLR_URL)
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

@receiver(post_save, sender=ProductLike, dispatch_uid='product_like_save')
def product_like_save(instance, **kwargs):
    product_save(instance.product)

@receiver(post_delete, sender=ProductLike, dispatch_uid='product_like_delete')
def product_like_delete(instance, **kwargs):
    product_save(instance.product)

@receiver(post_save, sender=ShopProduct, dispatch_uid='shop_product_save')
def shop_product_save(instance, **kwargs):
    product_save(instance.product)

@receiver(post_delete, sender=ShopProduct, dispatch_uid='shop_product_delete')
def shop_product_delete(instance, **kwargs):
    product_save(instance.product)


def rebuild_product_index(url=None, vendor_id=None):
    connection = Solr(url or settings.SOLR_URL)
    product_count = 0
    product_buffer = collections.deque()
    boost = {}

    products = get_model('apparel', 'Product').objects.filter(likes__isnull=False, likes__active=True).order_by('-modified')

    if vendor_id:
        products = products.filter(vendors=vendor_id)

    for product in products.iterator():
        document, boost = get_product_document(product, rebuild=True)
        if document is not None and document['published']:
            product_buffer.append(document)
            if vendor_id:
                logger.info("Rebuilding product: %s %s %s" % (product.id,product.product_name,product.default_vendor ))
            if len(product_buffer) == 100:
                connection.add(list(product_buffer), commit=False, boost=boost, commitWithin=False)
                product_buffer.clear()

    valid_products = get_model('apparel', 'Product').valid_objects
    if vendor_id:
        valid_products = valid_products.filter(vendors=vendor_id)

    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=valid_products.count()).start()
    for index, product in enumerate(valid_products.iterator()):
        pbar.update(index)
        document, boost = get_product_document(product, rebuild=True)
        if document is not None and document['published']:
            product_buffer.append(document)
            if len(product_buffer) == 100:
                connection.add(list(product_buffer), commit=False, boost=boost, commitWithin=False)
                product_buffer.clear()

            product_count = product_count + 1
        else:
            connection.delete(id='%s.%s.%s' % (product._meta.app_label, product._meta.module_name, product.pk), commit=False)
    pbar.finish()

    connection.add(list(product_buffer), commit=False, boost=boost, commitWithin=False)
    connection.commit()

    return product_count

def get_product_document(instance, rebuild=False):
    document = {
        'id': '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk),
        'django_ct': '%s.%s' % (instance._meta.app_label, instance._meta.module_name),
        'django_id': instance.pk,
        'published': False
    }
    boost = {}

    if instance.published == True and instance.category and instance.manufacturer and instance.gender:
        availability = bool(instance.availability and instance.default_vendor and instance.default_vendor.availability != 0)
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
                logger.error('Availability is true, but product has no vendorproduct [PID: %s]' % (instance.pk,))
                availability = False
                # Supposed to be..?
                #instance.availability = False
                return None, 0

        color_names = []
        color_ids = []
        color_data = instance.options.filter(option_type__name__in=['color', 'pattern']).exclude(value__exact='').values_list('pk', 'value')
        if color_data:
            color_ids, color_names = zip(*color_data)
        color_names = ' '.join(color_names)

        category_data = instance.category.get_ancestors(ascending=False, include_self=True).values_list('pk', 'name_en', 'name_sv')
        category_ids, category_en_names, category_sv_names = zip(*category_data)
        category_names = ' '.join(x for x in category_en_names + category_sv_names if x)

        document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
        document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
        document['django_id'] = instance.pk
        document['name'] = instance.product_name

        # Search fields
        document['product_key'] = instance.product_key
        document['product_name'] = instance.product_name
        document['description'] = instance.description
        document['manufacturer_name'] = instance.manufacturer.name
        document['color_names'] = color_names
        document['category_names'] = category_names

        # Facets
        vendor_markets = None
        if instance.default_vendor:
            vendor_markets = settings.VENDOR_LOCATION_MAPPING.get(instance.default_vendor.vendor.name,None)
        document['color'] = color_ids
        document['market'] =  vendor_markets if vendor_markets else settings.VENDOR_LOCATION_MAPPING.get("default")
        document['price'] = '%s,%s' % (price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)
        document['category'] = category_ids
        document['manufacturer_id'] = instance.manufacturer_id

        # Filters
        document['gender'] = instance.gender
        if rebuild:
            document['popularity'] = instance.popularity
        else:
            document['popularity'] = product_popularity(instance)
        document['availability'] = availability
        document['discount'] = discount
        document['published'] = instance.published

        # Users and likes
        likes = list(get_model('apparel', 'ProductLike').objects.filter(product=instance, active=True).values_list('user__id', 'modified'))
        document['user_likes'] = [x[0] for x in likes]
        for x in likes:
            document['%s_uld' % (x[0],)] = x[1]

        # Shops and their products
        shops = list(get_model('apparel', 'ShopProduct').objects.filter(product=instance, shop_embed__published=True).values_list('shop_embed__id', 'shop_embed__modified'))
        # Adding array with the different shops that the product has been added to.
        document['shop_products'] = [x[0] for x in shops]
        for x in shops:
            # Adding the shop products with a date for use as sorting parameter when fetching shop products.
            document['%s_spd' % (x[0],)] = x[1]

        # Templates
        has_looks = get_model('apparel', 'Look').published_objects.filter(components__product=instance).exists()
        #document['template'] = render_to_string('apparel/fragments/product_medium.html', {'object': instance, 'has_looks': has_looks, 'LANGUAGE_CODE': translation.get_language()})
        cur_language = translation.get_language()
        try:
            languages = settings.LANGUAGES_DISPLAY
            if likes:
                languages = settings.LANGUAGES

            for language, _ in languages:
                if language != cur_language:
                    translation.activate(language)
                document['{0}_template'.format(language)] = render_to_string('apparel/fragments/product_medium.html', {'object': instance, 'has_looks': has_looks, 'LANGUAGE_CODE': language})
        finally:
            translation.activate(cur_language)

        # Stored fields
        document['slug'] = instance.slug
        document['stored_price'] = '%s,%s' % (stored_price.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)
        document['stored_discount'] = '%s,%s' % (stored_discount.quantize(decimal.Decimal('1.00'), rounding=decimal.ROUND_HALF_UP), currency)

        # Images
        # XXX: during popularity script: IOError: image file is truncated (23
        # bytes not processed)
        # This
        # XXX: SyntaxError: not a TIFF IFD
        try:
            document['image_small'] = get_thumbnail(instance.product_image, '112x145', crop=False, format='PNG', transparent=True).url
            document['image_medium'] = get_thumbnail(instance.product_image, '224x291', crop=False, format='PNG', transparent=True).url
            document['image_xmedium'] = get_thumbnail(instance.product_image, '280x320', keep_size=True, crop=False, format='PNG').url
        except (SyntaxError, IOError):
            logger.exception('Thumbnail Error [PID: %s]' % (instance.pk,))
            return None, 0

        # Dates
        document['created'] = instance.date_added

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
        connection = Solr(settings.SOLR_URL)

    if not instance.user.is_hidden:
        document, boost = get_look_document(instance)
        connection.add([document], commit=False, boost=boost, commitWithin=False)

@receiver(post_delete, sender=Look, dispatch_uid='look_delete')
def look_delete(instance, **kwargs):
    connection = Solr(settings.SOLR_URL)
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))


def rebuild_look_index(url=None):
    connection = Solr(url or settings.SOLR_URL)
    look_count = 0
    look_buffer = collections.deque()
    boost = {}
    valid_looks = get_model('apparel', 'Look').objects.filter(user__is_hidden=False)
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=valid_looks.count()).start()
    for index, look in enumerate(valid_looks.iterator()):
        pbar.update(index)
        document, boost = get_look_document(look)
        look_buffer.append(document)
        if len(look_buffer) == 100:
            connection.add(list(look_buffer), commit=False, boost=boost, commitWithin=False)
            look_buffer.clear()

        look_count = look_count + 1
    pbar.finish()

    connection.add(list(look_buffer), commit=False, boost=boost, commitWithin=False)
    connection.commit()

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
    document['template'] = render_to_string('apparel/fragments/look_medium.html', {'object': instance})
    document['published'] = instance.published

    return document, boost


#
# Profile index (brands not counted)
#

@receiver(post_save, sender=get_user_model(), dispatch_uid='search_index_user_save')
def search_index_user_save(instance, **kwargs):
    boost = {}
    if 'solr' in kwargs and kwargs['solr']:
        connection = kwargs['solr']
    else:
        connection = Solr(settings.SOLR_URL)

    if not instance.is_brand and not instance.is_hidden:
        document, boost = get_profile_document(instance)
        connection.add([document], commit=False, boost=boost, commitWithin=False)

@receiver(post_delete, sender=get_user_model(), dispatch_uid='search_index_user_delete')
def search_index_user_delete(instance, **kwargs):
    connection = Solr(settings.SOLR_URL)
    connection.delete(id='%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk))

def rebuild_user_index(url=None):
    connection = Solr(url or settings.SOLR_URL)
    user_count = 0
    user_buffer = collections.deque()
    boost = {}
    valid_users = get_user_model().objects.filter(is_hidden=False, is_brand=False)

    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=valid_users.count()).start()
    for index, user in enumerate(valid_users.iterator()):
        pbar.update(index)
        document, boost = get_profile_document(user)
        user_buffer.append(document)
        if len(user_buffer) == 100:
            connection.add(list(user_buffer), commit=False, boost=boost, commitWithin=False)
            user_buffer.clear()

        user_count = user_count + 1
    pbar.finish()

    connection.add(list(user_buffer), commit=False, boost=boost, commitWithin=False)
    connection.commit()

    return user_count

def get_profile_document(instance):
    boost = {}
    document = {}
    document['id'] = '%s.%s.%s' % (instance._meta.app_label, instance._meta.module_name, instance.pk)
    document['django_ct'] = '%s.%s' % (instance._meta.app_label, instance._meta.module_name)
    document['django_id'] = instance.pk
    document['name'] = instance.display_name_live
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

class SearchBaseTemplate(TemplateView):
    template_name = 'search.html'

    def get_context_data(self, **kwargs):
        context = super(SearchBaseTemplate,self).get_context_data(**kwargs)
        gender = kwargs.get("gender")
        gender = select_from_multi_gender(self.request, 'shop', gender)
        query = self.request.GET.get('q', '')

        h = HTMLParser.HTMLParser()
        query = h.unescape(query)
        context.update({'q': query, 'gender': gender})
        return context

@DeprecationWarning
def search(request, gender=None):
    """
    Search page
    """
    gender = select_from_multi_gender(request, 'shop', gender)
    query = request.GET.get('q', '')

    h = HTMLParser.HTMLParser()
    query = h.unescape(query)

    return render(request, 'search.html', {'q': query, 'gender': gender})


def search_view(request, model_name):
    """
    Generic search view for different models. This method is being called asyncronously 
    from the web layer. 
    :param request:
    :param model_name:
    :return: Json
    """
    try:
        limit = int(request.REQUEST.get('limit', RESULTS_PER_PAGE))
    except ValueError:
        limit = RESULTS_PER_PAGE

    query = request.REQUEST.get('q')
    if not query:
        raise Http404()

    h = HTMLParser.HTMLParser()
    query = h.unescape(query)

    model_name = model_name.lower()

    # Gender field
    gender = request.REQUEST.get('gender')
    if not gender:
        gender = select_from_multi_gender(request, 'shop', None)

    if not gender or gender == 'A':
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
        arguments['fl'] = 'template:{0}_template'.format(translation.get_language())
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

    # Filter query parameters based on location
    if model_name != 'user':
        arguments['fq'].append('market_ss:{location}'.format(location=get_location(request)))

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
    header_text = ''
    button_text = ''
    if model_name == 'product':
        object_list = [o.template.replace('/Shop/0/', '/Search/0/') for o in paged_result.object_list if o]
        header_text = translation.ungettext('Found %(count)d product', 'Found %(count)d products', paged_result.paginator.count) % {'count': paged_result.paginator.count}
        button_text = translation.ungettext('Show %(count)d product', 'Show all %(count)d products', paged_result.paginator.count) % {'count': paged_result.paginator.count}
    elif model_name == 'look':
        object_list = [o.template for o in paged_result.object_list if o]
        header_text = translation.ungettext('Found %(count)d look', 'Found %(count)d looks', paged_result.paginator.count) % {'count': paged_result.paginator.count}
        button_text = translation.ungettext('Show %(count)d look', 'Show all %(count)d looks', paged_result.paginator.count) % {'count': paged_result.paginator.count}
    elif model_name == 'user':
        object_list = [o.template for o in paged_result.object_list if o]
        header_text = translation.ungettext('Found %(count)d matching member', 'Found %(count)d matching members', paged_result.paginator.count) % {'count': paged_result.paginator.count}
        button_text = translation.ungettext('Show %(count)d matching member', 'Show all %(count)d matching members', paged_result.paginator.count) % {'count': paged_result.paginator.count}
    elif model_name == 'manufacturer':
        object_list = [render_to_string('apparel/fragments/manufacturer_search.html', {'object': obj, 'gender': gender}) for obj in paged_result.object_list]
        header_text = translation.ungettext('Found %(count)d matching brand', 'Found %(count)d matching brands', paged_result.paginator.count) % {'count': paged_result.paginator.count}
        button_text = translation.ungettext('Show %(count)d matching brand', 'Show all %(count)d matching brands', paged_result.paginator.count) % {'count': paged_result.paginator.count}
    elif model_name == 'store':
        object_list = [render_to_string('apparel/fragments/store_search.html', {'object': obj, 'gender': gender}) for obj in paged_result.object_list]
        header_text = translation.ungettext('Found %(count)d matching store', 'Found %(count)d matching stores', paged_result.paginator.count) % {'count': paged_result.paginator.count}
        button_text = translation.ungettext('Show %(count)d matching store', 'Show all %(count)d matching stores', paged_result.paginator.count) % {'count': paged_result.paginator.count}

    return HttpResponse(
        json.dumps({
            'object_list': object_list,
            'number': paged_result.number,
            'paginator': {
                'num_pages': paged_result.paginator.num_pages,
                'count': paged_result.paginator.count,
            },
            'header_text': header_text,
            'button_text': button_text,
        }),
        mimetype='application/json'
    )

def get_available_brands(gender, location):
    """
    Return list of brand ids which products are published, available and able to being shown in the given location
    """
    if not gender or gender == 'A':
        gender_field = 'gender:(U OR M OR W)'
    else:
        gender_field = 'gender:(U OR %s)' % (gender,)
    arguments = {'fq': ['django_ct:apparel.product', 'availability:true', gender_field, 'published:true',
                        'market_ss:{location}'.format(location=location)],
                 'qf': ['manufacturer_auto'],
                 'defType': ['edismax'],
                 'start': 0,
                 'rows': 12,
                 'facet': 'on',
                 'facet.limit': -1,
                 'facet.mincount': 1,
                 'facet.': 1,
                 'facet.field': ['manufacturer']}

    results = ApparelSearch("*:*", **arguments)
    facet = results.get_facet()['facet_fields']
    results = []
    for i, value in enumerate(facet['manufacturer']):
        if i % 2 == 0:
            id, name, _ = decode_manufacturer_facet(value)
            results.append(id)
    return results
