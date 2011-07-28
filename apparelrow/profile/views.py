import logging
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext
from django.db.models import Q, Count
from django.views.generic import list_detail
from django.contrib.contenttypes.models import ContentType

from apparel.decorators import get_current_user
from apparel.models import *
from apparel.forms import *
from actstream.models import user_stream, actor_stream, Follow

from profile.forms import *

# TODO && FIXME: build a better solution, right now we use this in
# profile/looks/following/followers. Should create a view for the submit form
# maybe?
def handle_change_image(request, profile):
    if request.method == 'POST':
        if profile.user != request.user:
            return HttpResponseForbidden()

        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(form.instance.get_absolute_url())
    else:
        form = ProfileImageForm(instance=profile)

    return form


@get_current_user
def profile(request, profile, page=0):
    """
    Displays the profile page
    """
    form = handle_change_image(request, profile)

    queryset = actor_stream(profile.user)
    queryset = queryset.filter(verb__in=['added', 'commented', 'created', 'liked_look', 'liked_product'])

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/profile.html",
        paginate_by=10,
        page=page,
        extra_context={
            'next': request.get_full_path(),
            "change_image_form": form,
            "profile": profile,
            "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }
    )


@get_current_user
def looks(request, profile, page=0):
    form = handle_change_image(request, profile)
    queryset = Look.objects.filter(user=profile.user).order_by('-modified')
    popular  = get_top_looks(profile.user, 10)
    
    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name='profile/looks.html',
        paginate_by=10,
        page=page,
        extra_context={
            'next': request.get_full_path(),
            "change_image_form": form,
            "profile": profile,
            "popular_looks": popular
            # FIXME: Add the most used brand to display in the left column
        }
    )
    
@get_current_user
def followers(request, profile, page=0):
    form = handle_change_image(request, profile)
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, object_id=profile.user.id)

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/followers.html",
        paginate_by=10,
        page=page,
        extra_context={
            'next': request.get_full_path(),
            "change_image_form": form,
            "profile": profile,
            "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }
    )

@get_current_user
def following(request, profile, page=0):
    form = handle_change_image(request, profile)
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, user=profile.user)

    return list_detail.object_list(
        request,
        queryset=queryset,
        template_name="profile/following.html",
        paginate_by=10,
        page=page,
        extra_context={
            'next': request.get_full_path(),
            "change_image_form": form,
            "profile": profile,
            "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }
    )

def get_top_looks(user, limit=10):
    """
    Returns a list of objects for the most popular looks for the given user.
    """
    return Look.objects.filter(Q(likes__active=True) & Q(user=user)).annotate(num_likes=Count('likes')).order_by('-num_likes')[:limit]
