import json
import base64
import uuid
import math
import decimal

from django.conf import settings
from django.core.cache import get_cache
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest, HttpResponseForbidden, Http404, HttpResponseRedirect
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db.models.loading import get_model
from django.utils import translation
from django.contrib.auth.decorators import login_required

from sorl.thumbnail import get_thumbnail

from apparelrow.profile.utils import get_facebook_user

from apparelrow.apparel.signals import look_saved
from apparelrow.apparel.utils import JSONResponse, set_query_parameter, currency_exchange
from apparelrow.apparel.tasks import facebook_push_graph, facebook_pull_graph
from apparelrow.apparel.views import _product_like
from apparelrow.apparel.search import ApparelSearch

def look_like_products(request, look_id):
    look = get_model('apparel', 'Look').objects.get(pk=look_id)

    for component in look.display_components.select_related('product'):
        _product_like(request, component.product, 'like')


def embed(request, slug, identifier=None):
    """
    Display look for use in embedded iframe.
    """
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    try:
        look_embed = get_model('apparel', 'LookEmbed').objects.get(identifier=identifier)
        width = look_embed.width
        language = look_embed.language
        nginx_key = reverse('look-embed-identifier', args=[identifier, slug])
    except get_model('apparel', 'LookEmbed').DoesNotExist:
        width = look.width
        language = 'en'
        nginx_key = reverse('look-embed', args=[slug])

    # Height
    scale = width / float(look.width)
    height = int(math.ceil(look.height * scale))

    # Fix component styles
    max_width = width
    if look.display_with_component == 'C':
        components = look.collage_components.select_related('product')
    elif look.display_with_component == 'P':
        components = look.photo_components.select_related('product')
        if look.image:
            thumbnail = get_thumbnail(look.image, str(width), upscale=False)
            max_width = min(thumbnail.width, width)
            height = min(thumbnail.height, height)


    language_currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': 1, 'start': 0,
                       'fl': 'price,discount_price',
                       'sort': 'price asc, popularity desc, created desc'}
    for component in components:
        component.style_embed = component._style(max_width / float(look.width))

        if request.GET.get('alternative'):
            colors_pk = list(map(str, component.product.options.filter(option_type__name='color').values_list('pk', flat=True)))
            query_arguments['fq'] = ['availability:true', 'django_ct:apparel.product']
            query_arguments['fq'].append('gender:(%s OR U)' % (component.product.gender,))
            query_arguments['fq'].append('category:%s' % (component.product.category_id))
            if colors_pk:
                query_arguments['fq'].append('color:(%s)' % (' OR '.join(colors_pk),))
            search = ApparelSearch('*:*', **query_arguments)
            docs = search.get_docs()
            if docs:
                shop_reverse = 'shop-men' if component.product.gender == 'M' else 'shop-women'
                shop_url = '%s#category=%s' % (reverse(shop_reverse),
                                                        component.product.category_id)
                if colors_pk:
                    shop_url = '%s&color=%s' % (shop_url, ','.join(colors_pk))

                price, currency = docs[0].price.split(',')
                rate = currency_exchange(language_currency, currency)
                price = rate * decimal.Decimal(price)
                price = price.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

                component.alternative = (shop_url, price, language_currency)

    translation.activate(language)
    response = render(request, 'apparel/look_embed.html', {'object': look,
                                                           'components': components,
                                                           'width': str(width),
                                                           'height': str(height)})
    translation.deactivate()

    get_cache('nginx').set(nginx_key, response.content, 60*60*24*20)

    return response


@login_required
def dialog_embed(request, slug):
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    max_width = 1200
    default_width = max(600, look.width or 694)
    if look.display_with_component == 'P' and look.image:
        max_width = default_width = max(600, min(1200, look.image_width))

    return render(request, 'apparel/dialog_look_embed.html', {'look': look,
                                                              'default_width': default_width,
                                                              'max_width': max_width})


@login_required
def widget(request, slug):
    if request.method != 'POST':
        return HttpResponseNotAllowed()

    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    content = {}
    content['object'] = look
    content['language'] = request.POST.get('language', 'sv')

    # Width
    content['width'] = int(request.POST.get('width', '720'))
    if content['width'] < 600:
        content['width'] = 600
    elif content['width'] > 1200:
        content['width'] = 1200

    # Height
    scale = content['width'] / float(look.width)
    content['height'] = int(math.ceil(look.height * scale))
    if look.display_with_component == 'P' and look.image:
        thumbnail = get_thumbnail(look.image, str(content['width']), upscale=False)
        content['height'] = min(thumbnail.height, content['height'])
        content['width'] = min(thumbnail.width, content['width'])

    LookEmbed = get_model('apparel', 'LookEmbed')
    identifier = uuid.uuid4().hex
    look_embed, created = LookEmbed.objects.get_or_create(look=look,
                                                          user=request.user,
                                                          language=content['language'],
                                                          width=content['width'],
                                                          defaults={'identifier': identifier})
    content['identifier'] = look_embed.identifier

    return render(request, 'apparel/fragments/look_widget.html', content)


def create(request):
    """
    Look create page, select between collage and photo.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), request.get_full_path()))

    return render(request, 'apparel/look_create.html')


def editor(request, component=None, slug=None):
    """
    Look editor
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), request.get_full_path()))

    look = None
    has_liked = False
    if slug is not None:
        if not request.user.is_authenticated():
            raise Http404()

        look = get_object_or_404(get_model('apparel', 'Look'), slug=slug, user=request.user)
        component = {'P': 'photo', 'C': 'collage'}[look.component]

    if request.user.is_authenticated():
        has_liked = request.user.product_likes.exists()

    if component is None:
        raise Http404()

    return render(request, 'apparel/look_editor.html', {'component': component,
                                                        'object': look,
                                                        'has_liked': has_liked})


def publish(request, slug):
    """
    Publish look
    """
    if not request.user.is_authenticated():
        raise Http404()

    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug, user=request.user)
    look.published = True
    look.save(update_fields=['published'])

    if request.user.fb_share_create_look:
        if look.display_components.count() > 0:
            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'create', 'look', request.build_absolute_uri(look.get_absolute_url()))

    look_saved.send(sender=get_model('apparel', 'Look'), look=look, update=False)

    # Automatically like all products in the published look
    look_like_products(request, look.pk)

    return JSONResponse(dict(success=True))


def unpublish(request, slug):
    """
    Unpublish look
    """
    if not request.user.is_authenticated():
        raise Http404()

    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug, user=request.user)
    look.published = False
    look.save(update_fields=['published'])

    look_saved.send(sender=get_model('apparel', 'Look'), look=look, update=False)

    return JSONResponse(dict(success=True))


def look_instance_to_dict(look):
    look_dict = {
        'id': look.id,
        'title': look.title,
        'user': look.user.display_name,
        'url': look.get_absolute_url(),
        'slug': look.slug,
        'component': look.component,
        'description': look.description,
        'published': look.published,
    }

    if look.components:
        look_dict['components'] = []
        for component in look.components.all():
            manufacturer_name = component.product.manufacturer.name if component.product.manufacturer else None
            look_dict['components'].append({
                'id': component.id,
                'component_of': component.component_of,
                'left': component.left,
                'top': component.top,
                'width': component.width,
                'height': component.height,
                'z_index': component.z_index,
                'rotation': component.rotation,
                'product': {
                    'id': component.product.id,
                    'slug': component.product.slug,
                    'image_small': get_thumbnail(component.product.product_image, '112x145', crop=False, format='PNG', transparent=True).url,
                    'image_medium': get_thumbnail(component.product.product_image, '224x291', crop=False, format='PNG', transparent=True).url,
                    'product_name': component.product.product_name,
                    'brand_name': manufacturer_name
                }
            })

    if look.image:
        look_dict['image'] = look.image.url

    return look_dict


class LookView(View):

    def delete(self, request, pk, *args, **kwargs):
        """
        Delete a look based on primary key.
        """
        look = get_object_or_404(get_model('apparel', 'Look'), pk=pk)

        if request.user.is_authenticated() and request.user == look.user:
            look.delete()

            return JSONResponse(status=204)

        return JSONResponse({'message': 'not authenicated'}, status=401)


    def put(self, request, pk, *args, **kwargs):
        """
        Update a look based on primary key.
        """
        look = get_object_or_404(get_model('apparel', 'Look'), pk=pk)

        try:
            json_data = json.loads(request.body)
        except ValueError:
            return JSONResponse({'message': 'invalid json body'}, status=400)

        if not request.user.is_authenticated():
            return JSONResponse({'message': 'not authenicated'}, status=401)

        required_keys = ['title', 'component', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return JSONResponse({'message': 'missing key %s' % (key,)}, status=400)

        # Cannot update image without clearing the look
        if 'image' in json_data:
            del json_data['image']

        # Set user to the user object
        json_data['user'] = request.user

        # If published notify next view
        if json_data['published']:
            request.session['look_saved'] = True

        # Look components
        if json_data['components']:

            # Remove components
            look_components = get_model('apparel', 'LookComponent').objects.filter(look_id=pk)
            updated_component_ids = [x['id'] for x in json_data['components'] if 'id' in x]
            for component in look_components:
                if component.id not in updated_component_ids:
                    component.delete()

            # Add new components and update old
            LookComponent = get_model('apparel', 'LookComponent')
            for component in json_data['components']:
                component_id = None
                if 'id' in component:
                    component_id = component['id']
                    del component['id']

                product_id = component['product']['id']
                del component['product']

                look_component, created = LookComponent.objects.get_or_create(id=component_id,
                                                                              look_id=pk,
                                                                              product_id=product_id)

                if 'component_of' not in component or not component['component_of']:
                    component['component_of'] = json_data['component']

                for key, value in component.items():
                    setattr(look_component, key, value)

                look_component.save()

            del json_data['components']

        for key, value in json_data.items():
            setattr(look, key, value)

        # TODO: handle errors
        look.save()

        # Send look saved signal
        look_saved.send(sender=get_model('apparel', 'Look'), look=look)

        # Automatically like all products in the published look
        if look.published:
            look_like_products(request, look.pk)

        return JSONResponse(status=204)


    def post(self, request, *args, **kwargs):
        """
        Create a new look.
        """
        try:
            json_data = json.loads(request.body)
        except ValueError:
            return JSONResponse({'message': 'invalid json body'}, status=400)

        if not request.user.is_authenticated():
            return JSONResponse({'message': 'not authenicated'}, status=401)

        required_keys = ['title', 'component', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return JSONResponse({'message': 'missing key %s' % (key,)}, status=400)

        if json_data['component'] == 'P':
            if 'image' not in json_data:
                return JSONResponse({'message': 'missing image for tagged photo look'}, status=400)

            if 'image_base64' in json_data:
                image_data = base64.decodestring(json_data['image_base64'])
                json_data['image'] = ContentFile(image_data)
                del json_data['image_base64']

                if 'image_name' in json_data:
                    json_data['image'].name = json_data['image_name']
                    del json_data['image_name']
                else:
                    json_data['image'].name = uuid.uuid4().hex

            # Handle temporary image transfer
            elif 'image_id' in json_data:
                temp_image = get_model('apparel', 'TemporaryImage').objects.get(pk=json_data['image_id'])
                json_data['image'] = ContentFile(temp_image.image.read())
                json_data['image'].name = temp_image.image.name
                del json_data['image_id']

        # Add user
        json_data['user'] = request.user

        # If published notify next view
        if json_data['published']:
            request.session['look_saved'] = True

        request.session['look_created'] = True

        # Exclude components, handle later
        components = json_data['components']
        del json_data['components']

        look = get_model('apparel', 'Look')(**json_data)
        look.save()

        for component in components:
            component['product_id'] = component['product']['id']
            del component['product']

            if 'component_of' not in component:
                component['component_of'] = look.component

            component['look_id'] = look.pk

            # TODO: error handling
            look_component = get_model('apparel', 'LookComponent')(**component)
            look_component.look = look
            look_component.save()

        # Send look saved signal
        look_saved.send(sender=get_model('apparel', 'Look'), look=look)

        # Automatically like all products in the published look
        if look.published:
            look_like_products(request, look.pk)

        response = JSONResponse(look_instance_to_dict(look), status=201)
        response['Location'] = reverse('look-detail', args=[look.slug])

        return response

    def get(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a look by primary key or retrieve many looks with pagination
        """
        if pk is not None:
            look = get_object_or_404(get_model('apparel', 'Look'), pk=pk)

            return JSONResponse(look_instance_to_dict(look))

        try:
            limit = int(request.GET.get('limit', 10))
        except ValueError:
            return JSONResponse({'message': 'invalid limit argument'}, status=400)

        clamped_limit = min(30, max(limit, 10))
        paginator = Paginator(get_model('apparel', 'Look').published_objects.all(),
                              clamped_limit)

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

        result.update(looks=[look_instance_to_dict(look) for look in paged_result.object_list])

        return JSONResponse(result)
