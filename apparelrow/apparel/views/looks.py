import json
import base64
import uuid
import math
import decimal
import StringIO

from django.conf import settings
from django.core.cache import get_cache
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest, HttpResponseForbidden, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db.models.loading import get_model
from django.utils import translation
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile

try:
    from PIL import Image
except ImportError:
    import Image

from sorl.thumbnail import get_thumbnail

from apparelrow.profile.utils import get_facebook_user

from apparelrow.apparel.signals import look_saved
from apparelrow.apparel.utils import JSONResponse, set_query_parameter, select_from_multi_gender, currency_exchange, \
    get_gender_url
from apparelrow.apparel.tasks import facebook_push_graph, facebook_pull_graph
from apparelrow.apparel.views import _product_like
from apparelrow.apparel.search import ApparelSearch

def look_like_products(request, look_id):
    look = get_model('apparel', 'Look').objects.get(pk=look_id)

    for component in look.display_components.select_related('product'):
        # Not autolike text links
        if not component.link:
            _product_like(request, component.product, 'like')

def embed(request, slug, identifier=None):
    """
    Display look for use in embedded iframe.
    """
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)
    look_embed = None
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
        components = look.photo_components.select_related('product').select_related('link')
        if look.image:
            thumbnail = get_thumbnail(look.image, str(width), upscale=False)
            max_width = min(thumbnail.width, width)
            height = min(thumbnail.height, height)

    # TODO: replace alternative code with get_product_alternative from apparel.utils
    language_currency = settings.LANGUAGE_TO_CURRENCY.get(language, settings.APPAREL_BASE_CURRENCY)
    query_arguments = {'rows': 1, 'start': 0,
                       'fl': 'price,discount_price',
                       'sort': 'price asc, popularity desc, created desc'}
    for component in components:
        component.style_embed = component.style_percentage()
        if component.product:
            colors_pk = list(map(str, component.product.options.filter(option_type__name='color').values_list('pk', flat=True)))
            query_arguments['fq'] = ['availability:true', 'django_ct:apparel.product']
            query_arguments['fq'].append('gender:(%s OR U)' % (component.product.gender,))
            query_arguments['fq'].append('category:%s' % (component.product.category_id))
            if colors_pk:
                query_arguments['fq'].append('color:(%s)' % (' OR '.join(colors_pk),))
            search = ApparelSearch('*:*', **query_arguments)
            docs = search.get_docs()
            if docs:
                shop_url_base = get_gender_url(component.product.gender, 'shop')
                shop_url = '{shop_url}?aid={user_id}&alink=Ext-Look&category={category}'.format(shop_url=shop_url_base,
                                                                                                user_id=look.user.pk,
                                                                                                category=component.product.category_id)
                if colors_pk:
                    shop_url = '{shop_url}&color={colors}'.format(shop_url=shop_url, colors=','.join(colors_pk))

                price, currency = docs[0].price.split(',')
                rate = currency_exchange(language_currency, currency)
                price = rate * decimal.Decimal(price)
                price = price.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

                component.alternative = (shop_url, price, language_currency)

    translation.activate(language)
    response = render(request, 'apparel/look_embed.html', {'object': look,
                                                           'components': components,
                                                           'width': str(width),
                                                           'height': str(height),
                                                           'hide_border': look_embed.hide_border if look_embed is not None else False,
                                                           'embed_width': str(width) or settings.APPAREL_LOOK_SIZE[0],
                                                           'embed_height': str(height) or settings.APPAREL_LOOK_SIZE[1],
                                                           'embed_id': look_embed.identifier if look_embed else ''},)

    translation.deactivate()

    get_cache('nginx').set(nginx_key, response.content, 60*60*24*20)

    return response


def dialog_embed(request, slug):
    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    max_width = 1200
    default_width = max(600, look.width or 694)
    if look.display_with_component == 'P' and look.image:
        max_width = default_width = max(600, min(1200, look.image_width))

    return render(request, 'apparel/dialog_look_embed.html', {'look': look,
                                                              'default_width': default_width,
                                                              'max_width': max_width})


def widget(request, slug):
    if request.method != 'POST':
        return HttpResponseNotAllowed("Call method is not allowed")

    look = get_object_or_404(get_model('apparel', 'Look'), slug=slug)

    content = {}
    content['object'] = look
    content['language'] = request.POST.get('language', 'sv')

    # Width
    content['width'] = int(request.POST.get('width', '720'))
    content['width_type'] = request.POST.get('width_type', 'px')

    if content['width_type'] == '%' and int(content['width']) > 100:
        content['width'] = 100
    elif content['width_type'] == 'px':
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

    # Border
    content['hide_border'] = request.POST.get('hide_border', False)

    # User
    embed_user = look.user
    if request.user.is_authenticated():
        embed_user = request.user

    LookEmbed = get_model('apparel', 'LookEmbed')
    identifier = uuid.uuid4().hex

    look_embed, created = LookEmbed.objects.get_or_create(look=look, user=embed_user, language=content['language'],
                                                          width=content['width'], width_type=content['width_type'],
                                                          hide_border=(True if content['hide_border'] == '1' else False),
                                                          defaults={'identifier': identifier})


    content['identifier'] = look_embed.identifier
    content['STATIC_URL'] = settings.STATIC_URL.replace('http://','')
    return render(request, 'apparel/fragments/look_widget.html', content)


def create_and_like(request, slug):
    """
    Like product and then display look create page.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('auth_login'), request.get_full_path()))

    Product = get_model('apparel', 'Product')

    try:
        product = Product.objects.get(slug=slug)
    except (Product.MultipleObjectsReturned, Product.DoesNotExist) as e:
        raise Http404()

    _product_like(request, product, 'like')

    return HttpResponseRedirect(reverse('look-create'))


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

    gender = select_from_multi_gender(request, 'shop', None)

    return render(request, 'apparel/look_editor.html', {'component': component,
                                                        'object': look,
                                                        'has_liked': has_liked,
                                                        'gender': gender})


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
        'width': look.width,
        'height': look.height
    }

    if look.components:
        look_dict['components'] = []
        for component in look.components.all():
            component_dict = {
                'id': component.id,
                'component_of': component.component_of,
                'left': component.left,
                'top': component.top,
                'width': component.width,
                'height': component.height,
                'z_index': component.z_index,
                'rotation': component.rotation,
                'flipped': component.flipped,
                'rel_left': float(component.left + (component.width/2 if look.component == 'P' else 0))/look.width,
                'rel_top': float(component.top + (component.height/2 if look.component == 'P' else 0))/look.height
            }
            if component.product:
                manufacturer_name = component.product.manufacturer.name if component.product.manufacturer else None
                component_dict['product'] = {
                    'id': component.product.id,
                    'slug': component.product.slug,
                    'image_small': get_thumbnail(component.product.product_image, '112x145', crop=False, format='PNG', transparent=True).url,
                    'image_look': get_thumbnail(component.product.product_image, '224x291', crop=False, format='PNG', transparent=True).url,
                    'product_name': component.product.product_name,
                    'brand_name': manufacturer_name
                }
                component_dict['link'] = None
            else:
                component_dict['product'] = None
                component_dict['link'] = {
                    'id': component.link.id,
                    'title': component.link.title,
                    'url': component.link.url
                }

            look_dict['components'].append(component_dict)

    if look.image:
        look_dict['image'] = look.image.url

    return look_dict

def crop_look(json_data):
    padding = 20
    top = left = width = height = None
    if json_data['components']:
        for component in json_data['components']:
            top = component['top'] if component['top'] < top or top is None else top
            width = (component['left'] + component['width']) if (component['left'] + component['width']) > width or width is None else width
            height = (component['top'] + component['height']) if (component['top'] + component['height']) > height or height is None else height
            left = component['left'] if component['left'] < left or left is None else left

        for component in json_data['components']:
            component['top'] = component['top'] - top
            component['left'] = component['left'] - left

        json_data['width'] = width - left
        json_data['height'] = height - top



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

        # Crop area and adjust positions if we have a collage
        if json_data['component'] == 'C':
            crop_look(json_data)

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
            ComponentLink = get_model('apparel', 'ComponentLink')
            for component in json_data['components']:
                component_id = None
                if 'id' in component:
                    component_id = component['id']
                    del component['id']
                if 'product' in component and component['product']:
                    product_id = component['product']['id']
                    del component['product']
                else:
                    product_id = None
                if 'link' in component:
                    if component['link']:
                        if 'id' in component['link']:
                            link_id = component['link']['id']
                        else:
                            component_link = ComponentLink(title=component['link']['title'], url=component['link']['url'])
                            component_link.save()
                            link_id = component_link.pk
                    else:
                        link_id = None
                    del component['link']
                else:
                    link_id = None

                look_component, created = LookComponent.objects.get_or_create(id=component_id,
                                                                              look_id=pk,
                                                                              product_id=product_id,
                                                                              link_id=link_id)

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
        else:
            empty_image = Image.new('RGBA', (settings.APPAREL_LOOK_SIZE[0] - 2, settings.APPAREL_LOOK_SIZE[1] - 2), (255, 255, 255, 0))
            empty_image_io = StringIO.StringIO()
            empty_image.save(empty_image_io, format='PNG')

            json_data['image'] = InMemoryUploadedFile(empty_image_io, None, '%s.png' % (uuid.uuid4().hex,), 'image/png', empty_image_io.len, None)
            json_data['image'].seek(0)

         # Crop area and adjust positions if we have a collage
        if json_data['component'] == 'C':
            crop_look(json_data)

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
        ComponentLink = get_model('apparel', 'ComponentLink')
        for component in components:
            if 'product' in component:
                component['product_id'] = component['product']['id']
                del component['product']
            else:
                component['product_id'] = None
            if 'link' in component:
                if component['link']:
                    if 'id' in component['link']:
                        component['link_id'] = component['link']['id']
                    else:
                        component_link = ComponentLink(title=component['link']['title'], url=component['link']['url'])
                        component_link.save()
                        component['link_id'] = component_link.pk
                else:
                    component['link'] = None
                del component['link']
            else:
                component['link_id'] = None
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
