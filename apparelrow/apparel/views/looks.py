import json
import base64
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db.models.loading import get_model

from apparel.utils import JSONResponse, set_query_parameter


def look_instance_to_dict(look):
    look_dict = {
        'id': look.id,
        'title': look.title,
        'user': look.user.get_profile().display_name,
        'url': look.get_absolute_url(),
        'slug': look.slug,
        # TODO fix components
        'components': [],
        'component': look.component,
        'description': look.description,
    }

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

        return HttpResponseForbidden()

    def put(self, request, pk, *args, **kwargs):
        """
        Update a look based on primary key.
        """
        look = get_object_or_404(get_model('apparel', 'Look'), pk=pk)

        try:
            json_data = json.loads(request.body)
        except ValueError:
            return HttpResponseBadRequest('invalid body')

        if not request.user.is_authenticated():
            return HttpResponseForbidden('invalid user')

        required_keys = ['title', 'component', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return HttpResponseBadRequest('missing key %s' % (key))

        # Cannot update image without clearing the look
        del json_data['image']

        # Set user to the user object
        json_data['user'] = request.user

        # TODO: handle components
        del json_data['components']

        for key, value in json_data.items():
            setattr(look, key, value)

        # TODO: handle errors
        look.save()

        return JSONResponse(status=204)

    def post(self, request, *args, **kwargs):
        """
        Create a new look.
        """
        try:
            json_data = json.loads(request.body)
        except ValueError:
            return HttpResponseBadRequest('invalid body')

        if not request.user.is_authenticated():
            return HttpResponseForbidden('invalid user')

        required_keys = ['title', 'component', 'components', 'published']
        for key in required_keys:
            if key not in json_data:
                return HttpResponseBadRequest('missing key %s' % (key))

        if json_data['component'] == 'P':
            if 'image' not in json_data:
                return HttpResponseBadRequest('missing image for photo look')

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

        # Exclude components, handle later
        components = json_data['components']
        del json_data['components']

        look = get_model('apparel', 'Look')(**json_data)

        # TODO: Handle components creation
        for component in components:
            # TODO: error handling
            look_component = get_model('apparel', 'LookComponent')(**component)
            look.components.add(look_component)

        # TODO: error handling
        look.save()

        response = JSONResponse(look_instance_to_dict(look), status=201)
        response['Location'] = reverse('apparel.views.look_detail', args=[look.slug])

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
            return HttpResponseBadRequest('bad limit argument')

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
