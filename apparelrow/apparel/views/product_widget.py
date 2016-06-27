from django.views.generic.base import TemplateResponseMixin
import re
import math
import os.path
import decimal
import json
import uuid

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response

from django.shortcuts import get_object_or_404, render
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
from django.views.generic import View, TemplateView

from apparelrow.apparel.search import PRODUCT_SEARCH_FIELDS
from apparelrow.apparel.search import ApparelSearch
from apparelrow.apparel.models import Product
from apparelrow.apparel.models import Brand
from apparelrow.apparel.models import Option
from apparelrow.apparel.models import Category
from apparelrow.apparel.models import Vendor
from apparelrow.apparel.models import ProductWidget, ProductWidgetProduct, ProductWidgetEmbed
from apparelrow.apparel.utils import get_pagination_page, select_from_multi_gender

from apparelrow.apparel.views.shop import set_query_arguments

from sorl.thumbnail import get_thumbnail
from apparelrow.apparel.utils import JSONResponse, set_query_parameter, select_from_multi_gender, currency_exchange


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


class BaseProductWidgetView(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), request.get_full_path()))
        return super(BaseProductWidgetView, self).dispatch(request, *args, **kwargs)


class CreateProductWidgetView(BaseProductWidgetView):
    template_name = "apparel/create_product_widget.html"

    def get_context_data(self, **kwargs):
        context = super(CreateProductWidgetView, self).get_context_data(**kwargs)
        context.update(
            {
             'external_product_widget_id': 0,
             'external_widget_url': self.request.user.url_widgets
            }
        )
        return context


class EditProductWidgetView(BaseProductWidgetView):
    template_name = 'apparel/create_product_widget.html'
    product_widget = None

    def get_context_data(self, **kwargs):
        context = super(EditProductWidgetView, self).get_context_data(**kwargs)
        # product_widget_id if product_widget_id is not None else 0
        context.update({
            'external_product_widget_id': self.product_widget.id,
            'widget_type': self.product_widget.widget_type,
            'object': self.product_widget,
            'external_widget_url': self.request.user.url_widgets
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        self.product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=kwargs.get("product_widget_id", None))
        if not request.user.pk == self.product_widget.user.pk:
            return HttpResponse('Unauthorized', status=401)
        return super(EditProductWidgetView, self).dispatch(request, *args, **kwargs)


def get_liked_product_ids(product_widget):
    user_id = product_widget.user.id

    language = get_language()
    translation.activate(language)

    currency = settings.APPAREL_BASE_CURRENCY
    if language in settings.LANGUAGE_TO_CURRENCY:
        currency = settings.LANGUAGE_TO_CURRENCY.get(language)

    query_arguments = {'rows': 10, 'start': 0}
    class Request:
        pass
    request = Request()
    request.GET = {}
    query_arguments = set_query_arguments(query_arguments, request, facet_fields=None, currency=currency)

    query_arguments['fl'] = ['id:django_id']

    query_arguments['fq'].append('availability:true')

    query_arguments['sort'] = 'availability desc, %s_uld desc, popularity desc, created desc' % (user_id,)
    query_arguments['fq'].append('user_likes:%s' % (user_id,))

    query_string = '*:*'

    search = ApparelSearch(query_string, **query_arguments)
    paged_result, pagination = get_pagination_page(search, 10, 1)

    return [product.id for product in paged_result.object_list if product]


def product_widget_instance_to_dict(product_widget):
    """
    Runs query against solr to fetch products to display.
    :param product_widget:
    :return:
    """

    product_widget_dict = {
        'id': product_widget.id,
        'title': product_widget.title,
        'user': product_widget.user.display_name,
        'url': product_widget.get_absolute_url(),
        'description': product_widget.description,
        'published': product_widget.published,
        'widget_type': product_widget.widget_type,
        'show_liked': product_widget.show_liked
    }
    product_widget_dict['products'] = []
    if product_widget.show_liked:
        product_ids = get_liked_product_ids(product_widget)
        for product in Product.objects.filter(pk__in=product_ids):
            if product.default_vendor:
                manufacturer_name = product.manufacturer.name if product.manufacturer else None
                product_widget_dict['products'].append({
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
        for product in product_widget.products.all():
            if product.default_vendor:
                manufacturer_name = product.manufacturer.name if product.manufacturer else None
                product_widget_dict['products'].append({
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

    return product_widget_dict


def delete_productwidget(request, product_widget_id):
    productwidget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=product_widget_id)

    if request.user.is_authenticated() and request.user == productwidget.user:
        productwidget.delete()
        if get_model('apparel', 'ProductWidget').objects.filter(user=request.user).exists():
            return HttpResponseRedirect(reverse('profile-widgets', args=(request.user.slug,)))
        else:
            return HttpResponseRedirect(reverse('profile-likes', args=(request.user.slug,)))
    else:
        return HttpResponseRedirect(reverse('profile-widgets', args=(request.user.slug,)))


class ProductWidgetView(View):

    def get(self, request, pk, *args, **kwargs):
        if pk is not None:
            product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=pk)
            return JSONResponse(product_widget_instance_to_dict(product_widget))

    def delete(self, request, pk, *args, **kwargs):
        product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=pk)

        if request.user.is_authenticated() and request.user == product_widget.user:
            product_widget.delete()
            return JSONResponse(status=204)

        return JSONResponse({ 'message': 'Not authenticated'}, status=401)

    def put(self, request, pk=None, *args, **kwargs):
        if pk is not None and pk is not 0:
            product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=pk)
        else:
            product_widget = ProductWidget()
            product_widget.save()

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
            request.session['product_widget_saved'] = True

        product_widget.published = json_data['published']
        product_widget.title = json_data['title']

        if json_data['components'] and not json_data['show_liked']:

            # Remove components
            product_widget_components = get_model('apparel', 'ProductWidgetProduct').objects.filter(product_widget_embed_id=pk)
            updated_component_ids = [x['id'] for x in json_data['components'] if 'id' in x]
            for component in product_widget_components:
                if component.id not in updated_component_ids:
                    component.delete()

            # Add new components and update old
            ProductWidgetProduct = get_model('apparel', 'ProductWidgetProduct')
            for component in json_data['components']:
                component_id = None
                if 'id' in component:
                    component_id = component['id']
                    del component['id']

                product_id = component['product']['id']
                del component['product']

                product_widget_component, created = ProductWidgetProduct.objects.get_or_create(id=component_id,
                                                                                 product_widget_embed_id=pk,
                                                                                 product_id=product_id)

                for key, value in component.items():
                    setattr(product_widget_component, key, value)

                product_widget_component.save()

            del json_data['components']

        # TODO: Handle errors
        product_widget.save()

        return JSONResponse(status=204)

    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(request.body)
            if "type" in json_data:
                # Due to Klas law regarding non conflicting variable names.
                json_data['widget_type'] = json_data.pop("type")
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
            request.session['product_widget_saved'] = True

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
                product_widget = get_model('apparel', 'ProductWidget').objects.filter(user=request.user, show_liked=True, widget_type=json_data['widget_type'])[0]
            except:
                product_widget = get_model('apparel', 'ProductWidget')(**json_data)
        else:
            product_widget = get_model('apparel', 'ProductWidget')(**json_data)

        product_widget.show_liked = show_liked
        product_widget.save()

        for component in components:
            component['product_id'] = component['product']['id']
            del component['product']

            # TODO: Error handling
            product_widget_component = get_model('apparel', 'ProductWidgetProduct')(**component)
            product_widget_component.product_widget_embed = product_widget
            product_widget_component.save()

        response = JSONResponse(product_widget_instance_to_dict(product_widget), status=201)
        response['Location'] = reverse('edit-product-widget', args=[product_widget.pk])

        return response


class ProductWidgetDialogueView(TemplateResponseMixin, View):
    template_name = "apparel/fragments/product_widget_widget.html"
    http_method_not_allowed = ['get', 'put', 'patch', 'delete', 'head', 'options', 'trace']
    product_widget = None

    def get_context_data(self, **kwargs):
        request = self.request
        context = {}
        context.update({'width': request.POST.get('width', 100),
                        'width_type': request.POST.get('width_type', '%'),
                        'height': request.POST.get('height', 600),
                        'language': request.POST.get('language', 'sv'),
                        })

        show_product_brand = bool(int(request.POST.get('show_product_brand', 1)))
        show_filters = bool(int(request.POST.get('show_filters', 1)))
        show_filters_collapsed = bool(int(request.POST.get('show_filters_collapsed', 1)))
    
        if context['width_type'] == '%' and int(context['width']) > 100:
            context['width'] = 100
        elif context['width_type'] == 'px':
            if context['width'] == '' or int(context['width']) < 400:
                context['width'] = 400
            elif int(context['width']) > 1200:
                context['width'] = 1200
            else:
                context['width'] = int(context['width'])
    
        if context['height'] == '':
            if self.product_widget.widget_type == 'single':
                context['height'] = 300
            else:
                context['height'] = 200
        context['height'] = int(context['height'])
        if context['height'] < 50:
            context['height'] = 50
    
        product_widget_embed = ProductWidgetEmbed(
            product_widget=self.product_widget,
            user=self.product_widget.user,
            width=context['width'],
            width_type=context['width_type'],
            height=context['height'],
            language=context['language'],
            show_product_brand=show_product_brand
        )
        product_widget_embed.save()
        context.update({'slug': uuid.uuid4().hex, 'object': product_widget_embed})
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def dispatch(self, request, *args, **kwargs):
        self.product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=kwargs.get("product_widget_id", None))
        if not request.user.pk == self.product_widget.user.pk:
            return HttpResponse('Unauthorized', status=401)
        return super(ProductWidgetDialogueView, self).dispatch(request, *args, **kwargs)

#
# Embed
#

class EmbedProductWidgetView(TemplateView):
    template_name = "apparel/product_widget_embed.html"

    def get_context_data(self, **kwargs):
        context = super(EmbedProductWidgetView, self).get_context_data(**kwargs)
        product_widget_embed = get_model('apparel', 'ProductWidgetEmbed').objects.get(pk=context["embed_product_widget_id"])
        components = []
        if product_widget_embed.product_widget.show_liked:
            components = Product.objects.filter(pk__in=get_liked_product_ids(product_widget_embed.product_widget))
        else:
            components = product_widget_embed.product_widget.products.select_related('product')

        context.update({"object": product_widget_embed,
                        "language": product_widget_embed.language,
                        "width": str(product_widget_embed.width),
                        "embed_id": context["embed_product_widget_id"], # Redundant
                        "components": components})
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        nginx_key = reverse('embed-product-widget', args=[context["embed_product_widget_id"]])
        translation.activate(context["language"])
        response = self.render_to_response(context)

        # Must render the content otherwise the html ending up in memcached gets weird django tags in the beginning and the end
        response.render()
        translation.deactivate()
        get_cache('nginx').set(nginx_key, response.content, 600)
        return response

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("embed_product_widget_id", None) is None:
            # Todo handling for missing embed product widget, should not be possible due to url pattern matching.
            return
        return super(EmbedProductWidgetView, self).dispatch(request, *args, **kwargs)


@DeprecationWarning
def embed_product_widget(request, template='apparel/product_widget_embed.html', embed_product_widget_id=None):
    """
     Display look for use in embedded iframe.
    """
    product_widget_embed = None
    try:
        product_widget_embed = get_model('apparel', 'ProductWidgetEmbed').objects.get(pk=embed_product_widget_id)
        width = product_widget_embed.width
        language = product_widget_embed.language
        nginx_key = reverse('embed-product-widget', args=[embed_product_widget_id])
    except get_model('apparel', 'ProductWidgetEmbed').DoesNotExist:
        #nginx_key = reverse('look-embed', args=[slug])
        return

    # TODO: replace alternative code with get_product_alternative from apparel.utils
    language_currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': 1, 'start': 0,
                       'fl': 'price,discount_price',
                       'sort': 'price asc, popularity desc, created desc'}
    components = product_widget_embed.product_widget.products.select_related('product')

    translation.activate(language)
    response = render(request, 'apparel/product_widget_embed.html', {'object': product_widget_embed,
                                                           'components': components,
                                                           'width': str(width),
                                                           'embed_id': embed_product_widget_id},)

    translation.deactivate()
    get_cache('nginx').set(nginx_key, response.content, 3600*24*20)
    return response

@DeprecationWarning
def editor(request, template='apparel/create_product_widget.html', product_widget_id=None, **kwargs):
    if not request.user.is_authenticated():
        return HttpResponse('Unauthorized', status=401)
    product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=product_widget_id)

    if not request.user.pk == product_widget.user.pk:
        return HttpResponse('Unauthorized', status=401)

    return render(request, template, {
        'external_product_widget_id': product_widget_id if product_widget_id is not None else 0,
        'type': product_widget.type,
        'object': product_widget,
        'external_widget_url': request.user.url_widgets
    })

@DeprecationWarning
def create(request, type):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), request.get_full_path()))
    return render(request, 'apparel/create_product_widget.html', {'external_product_widget_id': 0, 'type': type,
                                                                  'external_widget_url': request.user.url_widgets})

# Deprecated
@DeprecationWarning
def dialog_embed(request, product_widget_id=None):
    product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=product_widget_id)

    max_width = 1200
    default_width = 600

    return render(request, 'apparel/dialog_product_widget_embed.html', {
        'product_widget': product_widget,
        'default_width': default_width,
        'max_width': max_width,
    })

@DeprecationWarning
def product_widget_widget(request, product_widget_id=None):
    if request.method != 'POST':
        return HttpResponseNotAllowed("Method is not allowed")

    product_widget = get_object_or_404(get_model('apparel', 'ProductWidget'), pk=product_widget_id)

    if not request.user.pk == product_widget.user.pk:
        return HttpResponseNotAllowed("Unauthorized")


    content = {}
    content['width'] = request.POST.get('width', 100)
    content['width_type'] = request.POST.get('width_type', '%')
    content['height'] = request.POST.get('height', 600)
    content['language'] = request.POST.get('language', 'sv'),
    show_product_brand = bool(int(request.POST.get('show_product_brand', 1)))
    show_filters = bool(int(request.POST.get('show_filters', 1)))
    show_filters_collapsed = bool(int(request.POST.get('show_filters_collapsed', 1)))

    if content['width_type'] == '%' and int(content['width']) > 100:
        content['width'] = 100
    elif content['width_type'] == 'px':
        if content['width'] == '' or int(content['width']) < 400:
            content['width'] = 400
        elif int(content['width']) > 1200:
            content['width'] = 1200
        else:
            content['width'] = int(content['width'])

    if content['height'] == '':
        if product_widget.type == 'single':
            content['height'] = 300
        else:
            content['height'] = 200
    content['height'] = int(content['height'])
    if content['height'] < 50:
        content['height'] = 50

    product_widget_embed = ProductWidgetEmbed(
        product_widget=product_widget,
        user=product_widget.user,
        width=content['width'],
        width_type=content['width_type'],
        height=content['height'],
        language=content['language'][0],
        show_product_brand=show_product_brand
    )
    content['slug'] = uuid.uuid4().hex
    product_widget_embed.save()
    content['object'] = product_widget_embed

    return render(request, 'apparel/fragments/product_widget_widget.html', content)