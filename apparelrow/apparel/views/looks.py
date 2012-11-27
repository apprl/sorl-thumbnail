from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apparel.models import Look
from apparel.utils import JSONResponse, set_query_parameter


def look_instance_to_dict(look):
    look_dict = {
        'id': look.id,
        'title': look.title,
        'user': look.user.get_profile().display_name,
        'url': look.get_absolute_url(),
    }
    if look.image:
        look_dict['image'] = look.image.url

    return look_dict


class LookView(View):

    def delete(self, request, pk, *args, **kwargs):
        look = get_object_or_404(Look, pk=pk)

        if request.user.is_authenticated() and request.user == look.user:
            look.delete()

        return JSONResponse()

    def put(self, request, pk, *args, **kwargs):
        look = get_object_or_404(Look, pk=pk)

        # TODO: update

        return JSONResponse('put')

    def post(self, request, *args, **kwargs):

        # TODO: create

        return JSONResponse('post')

    def get(self, request, pk=None, *args, **kwargs):
        """
        HTTP GET handler
        """
        if pk is not None:
            look = get_object_or_404(Look, pk=pk)

            return JSONResponse(look_instance_to_dict(look))

        paginator = Paginator(Look.published_objects.all(), 10)

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
