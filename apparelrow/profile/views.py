import logging
import uuid

from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.template import RequestContext
from django.db.models import Q, Count
from django.views.generic import list_detail
from django.contrib import auth
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from apparel.decorators import get_current_user
from apparel.models import Look
# FIXME: Move get_facebook_friends and get_most_followed_users to a util module
from apparel.views import get_facebook_friends, get_most_followed_users
from apparel.utils import get_pagination_page
from actstream.models import user_stream, actor_stream, Follow
from profile.forms import ProfileImageForm, EmailForm, NotificationForm
from profile.models import EmailChange
from profile.tasks import send_email_confirm_task

PROFILE_PAGE_SIZE = 30

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
    queryset = queryset.filter(verb__in=['added', 'commented', 'created', 'liked_look', 'liked_product', 'started following'])

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    return render_to_response('profile/profile.html', {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        "change_image_form": form,
        "profile": profile,
        "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }, context_instance=RequestContext(request))

@get_current_user
def looks(request, profile, page=0):
    form = handle_change_image(request, profile)
    queryset = Look.objects.filter(user=profile.user).order_by('-modified')
    # Returns a list of objects for the most popular looks for the given user.
    popular_by_user = Look.objects.filter(Q(likes__active=True) & Q(user=profile.user)).annotate(num_likes=Count('likes')).order_by('-num_likes')[:10]
    
    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    return render_to_response('profile/looks.html', {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        "change_image_form": form,
        "profile": profile,
        "popular_looks": popular_by_user
        }, context_instance=RequestContext(request))
    
@get_current_user
def followers(request, profile, page=0):
    form = handle_change_image(request, profile)
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, object_id=profile.user.id)

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    return render_to_response('profile/followers.html', {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        "change_image_form": form,
        "profile": profile,
        "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }, context_instance=RequestContext(request))

@get_current_user
def following(request, profile, page=0):
    form = handle_change_image(request, profile)
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(content_type=content_type, user=profile.user)

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    return render_to_response('profile/following.html', {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        "change_image_form": form,
        "profile": profile,
        "recent_looks": Look.objects.filter(user=profile.user).order_by('-modified')[:4],
        }, context_instance=RequestContext(request))

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
def confirm_email(request):
    """
    Confirm email through GET-request.
    """
    token = request.GET.get('token', None)
    if token:
        try:
            email_change = EmailChange.objects.get(token=token, user=request.user)
        except EmailChange.DoesNotExist:
            return HttpResponseNotFound()
        request.user.email = email_change.email
        request.user.save()
        email_change.delete()

    return HttpResponseRedirect(reverse('profile.views.settings_email'))

@login_required
def settings_email(request):
    """
    Handles the email settings form
    """
    if request.method == 'POST':
        form = EmailForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # Remove old email change confirmations
            EmailChange.objects.filter(user=request.user).delete()

            token = uuid.uuid4().hex
            email = form.cleaned_data['email']
            email_change = EmailChange.objects.create(user=request.user, email=email, token=token)

            subject = ''.join(render_to_string('profile/confirm_email_subject.html').splitlines())
            body = render_to_string('profile/confirm_email.html', {
                    'username': request.user.get_profile().display_name,
                    'link': 'http://%s%s' % (Site.objects.get_current().domain, reverse('profile.views.confirm_email')),
                    'token': token,
                })
            send_email_confirm_task.delay(subject, body, email)

        return HttpResponseRedirect(reverse('profile.views.settings_email'))

    form = EmailForm()
    try:
        email_change = EmailChange.objects.get(user=request.user)
    except EmailChange.DoesNotExist:
        email_change = None

    return render_to_response('profile/settings_email.html', {
            'email_form': form,
            'email_change': email_change
        }, context_instance=RequestContext(request))

@login_required
def welcome_dialog(request):
    """
    Welcome dialog, shown on first login
    """
    apparel_profile = request.user.get_profile()
    apparel_profile.first_visit = False
    apparel_profile.save()

    context = {
            'first_name': request.user.first_name,
            'facebook_friends': get_facebook_friends(request),
            'most_followed_users': get_most_followed_users(limit=6)}

    return render_to_response('profile/dialog_welcome.html', context, context_instance=RequestContext(request))

def _get_next(request):
    """
    Returns a url to redirect to after the login
    """
    if 'next' in request.session:
        next = request.session['next']
        del request.session['next']
        return next
    elif 'next' in request.GET:
        return request.GET.get('next')
    elif 'next' in request.POST:
        return request.POST.get('next')
    else:
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

def login(request):
    if request.facebook is not None:
        user = auth.authenticate(fb_uid=request.facebook.uid, fb_object=request.facebook)
        if user is not None and user.is_active:
            auth.login(request, user)
            if user.get_profile().first_visit:
                return HttpResponseRedirect(reverse('apparel.views.home'))
            return HttpResponseRedirect(_get_next(request))

    return HttpResponseRedirect('/')
