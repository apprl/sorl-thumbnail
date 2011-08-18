import logging
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect
from django.template import RequestContext
from django.db.models import Q, Count
from django.views.generic import list_detail
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from apparel.decorators import get_current_user
from apparel.models import Look
from actstream.models import user_stream, actor_stream, Follow
from profile.forms import ProfileImageForm, EmailForm, NotificationForm

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
    # Returns a list of objects for the most popular looks for the given user.
    popular_by_user = Look.objects.filter(Q(likes__active=True) & Q(user=profile.user)).annotate(num_likes=Count('likes')).order_by('-num_likes')[:10]
    
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
            "popular_looks": popular_by_user
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

#
# Settings
#

@login_required
def settings_notification(request):
    """
    Handles the notification settings form
    """
    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES, instance=request.user.get_profile())
        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_notification'))

    form = NotificationForm(instance=request.user.get_profile())

    return render_to_response('profile/settings_notification.html',
            {'notification_form': form}, context_instance=RequestContext(request))

@login_required
def settings_email(request):
    """
    Handles the email settings form
    """
    if request.method == 'POST':
        form = EmailForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_email'))

    form = EmailForm(instance=request.user)

    return render_to_response('profile/settings_email.html',
            {'email_form': form}, context_instance=RequestContext(request))
