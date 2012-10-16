import logging
import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.db.models.loading import get_model
from django.contrib import auth
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apparel.decorators import get_current_user
from apparel.models import Product
from apparel.utils import get_pagination_page, get_gender_from_cookie
from profile.utils import get_facebook_user
from profile.forms import ProfileImageForm, EmailForm, NotificationForm, NewsletterForm, FacebookSettingsForm
from profile.models import EmailChange, ApparelProfile, Follow
from profile.tasks import send_email_confirm_task
from profile.decorators import avatar_change
from activity_feed.views import ActivityFeedHTML

PROFILE_PAGE_SIZE = 30

def get_facebook_friends(request):
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        return ApparelProfile.objects.filter(user__username__in=friends_uids)

def get_profile_sidebar_info(request, profile):
    """
    Get the misc. information needed in the sidebar of the profile page

    Returns a dict containing the extra information
    """
    info = {'products': 0, 'following': 0}

    if profile.is_brand:
        gender = get_gender_from_cookie(request)
        info['products'] = Product.valid_objects.filter(manufacturer=profile.brand_id, gender__in=['U', gender]).order_by('-date_added').count()
    else:
        info['products'] = Product.published_objects.filter(likes__user=profile.user, likes__active=True).count()

    content_type = ContentType.objects.get_for_model(User)
    info['following'] = Follow.objects.filter(user=profile, active=True).count()

    return info

@get_current_user
@avatar_change
def likes(request, profile, form, page=0, gender=None):
    """
    Displays the profile likes page.
    """
    if not gender:
        gender = get_gender_from_cookie(request)

    if profile.is_brand:
        queryset = Product.valid_objects.filter(manufacturer=profile.brand_id, gender__in=['U', gender]).order_by('-date_added')
    else:
        queryset = Product.published_objects.filter(likes__user=profile.user, likes__active=True).order_by('-availability', '-likes__modified')

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE, request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render(request, 'profile/fragments/likes.html', {
                'pagination': pagination,
                'current_page': paged_result,
        })

    content = {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'change_image_form': form,
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'APPAREL_GENDER': gender
    }

    content.update(get_profile_sidebar_info(request, profile))

    response = render(request, 'profile/likes.html', content)
    response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=gender, max_age=365 * 24 * 60 * 60)
    return response

@get_current_user
@avatar_change
def profile(request, profile, form, page=0):
    """
    Displays the profile page
    """
    htmlset = ActivityFeedHTML(request, get_model('activity_feed', 'activity').objects.get_for_user(profile))
    paginator = Paginator(htmlset, 5)

    page = request.GET.get('page')
    try:
        paged_result = paginator.page(page)
    except PageNotAnInteger:
        paged_result = paginator.page(1)
    except EmptyPage:
        paged_result = paginator.page(paginator.num_pages)

    if request.is_ajax():
        return render(request, 'activity_feed/feed.html', {
            'current_page': paged_result
        })

    content = {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'change_image_form': form,
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.user.look.order_by('-modified')[:10]
        }
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/profile.html', content)

@get_current_user
@avatar_change
def looks(request, profile, form, page=0):
    queryset = profile.user.look.order_by('-modified')

    paged_result, pagination = get_pagination_page(queryset, 6,
            request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render(request, 'apparel/fragments/looks_large.html', {
                'pagination': pagination,
                'current_page': paged_result
            })

    content = {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'change_image_form': form,
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request)
        }
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/looks.html', content)

@get_current_user
@avatar_change
def followers(request, profile, form, page=0):
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(user_follow=profile, active=True)

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render(request, 'profile/fragments/followers.html', {
                'pagination': pagination,
                'current_page': paged_result
        })

    content = {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'change_image_form': form,
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.user.look.order_by('-modified')[:4]
        }
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/followers.html', content)

@get_current_user
@avatar_change
def following(request, profile, form, page=0):
    content_type = ContentType.objects.get_for_model(User)
    queryset = Follow.objects.filter(user=profile, active=True)

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE,
            request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render(request, 'profile/fragments/following.html', {
                'pagination': pagination,
                'current_page': paged_result
        })

    content = {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'change_image_form': form,
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.user.look.order_by('-modified')[:4]
        }
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/following.html', content)

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

        newsletter_form = NewsletterForm(request.POST, request.FILES, instance=request.user.get_profile())
        if newsletter_form.is_valid():
            newsletter_form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_notification'))

    form = NotificationForm(instance=request.user.get_profile())
    newsletter_form = NewsletterForm(instance=request.user.get_profile())

    return render(request, 'profile/settings_notification.html', {'notification_form': form, 'newsletter_form': newsletter_form})

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

    return render(request, 'profile/settings_email.html', {
            'email_form': form,
            'email_change': email_change
        })

@login_required
def settings_facebook(request):
    """
    Handles the facebook settings form.
    """
    if request.method == 'POST':
        form = FacebookSettingsForm(request.POST, request.FILES, instance=request.user.get_profile())
        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_facebook'))

    form = FacebookSettingsForm(instance=request.user.get_profile())

    return render(request, 'profile/settings_facebook.html', {'facebook_settings_form': form})

#
# Welcome login flow
#

@login_required
def login_flow_initial(request):
    """
    Login flow step 1, friends.
    """
    profile = request.user.get_profile()
    if profile.login_flow == 'complete':
        return HttpResponseRedirect(reverse('shop'))

    profile.first_visit = False
    profile.login_flow = 'initial'
    profile.save()

    context = {
        'login_flow_step': 'step-initial',
        'next_url': reverse('profile.views.login_flow_members'),
        'profiles': get_facebook_friends(request)
    }
    return render(request, 'profile/login_flow_content.html', context)

@login_required
def login_flow_members(request):
    """
    Login flow step 2, members.
    """
    profile = request.user.get_profile()
    if profile.login_flow == 'complete':
        return HttpResponseRedirect(reverse('shop'))

    profile.first_visit = False
    profile.login_flow = 'members'
    profile.save()

    profiles = ApparelProfile.objects.filter(is_brand=False).order_by('-followers_count')
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        profiles = profiles.exclude(user__username__in=(f['id'] for f in friends['data']))

    context = {
        'login_flow_step': 'step-members',
        'next_url': reverse('profile.views.login_flow_brands'),
        'profiles': profiles[:21]
    }
    return render(request, 'profile/login_flow_content.html', context)

@login_required
def login_flow_brands(request):
    """
    Login flow step 3, brands.
    """
    profile = request.user.get_profile()
    if profile.login_flow == 'complete':
        return HttpResponseRedirect(reverse('shop'))

    profile.first_visit = False
    profile.login_flow = 'brands'
    profile.save()

    context = {
        'login_flow_step': 'step-brands',
        'next_url': reverse('profile.views.login_flow_complete'),
        'profiles': ApparelProfile.objects.filter(is_brand=True).order_by('-followers_count')[:21]
    }
    return render(request, 'profile/login_flow_content.html', context)

@login_required
def login_flow_complete(request):
    profile = request.user.get_profile()
    profile.first_visit = False
    profile.login_flow = 'complete'
    profile.save()
    return HttpResponseRedirect(reverse('user_feed'))

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
    if request.POST:
        access_token = request.POST.get('access_token', '')
        uid = request.POST.get('uid', '')

        user = auth.authenticate(fb_uid=uid, fb_graphtoken=access_token)
        if user is not None and user.is_active:
            auth.login(request, user)
            if user.get_profile().login_flow != 'complete':
                return HttpResponseRedirect(reverse('profile.views.login_flow_%s' % (user.get_profile().login_flow)))

            return HttpResponseRedirect(_get_next(request))

    return HttpResponseRedirect('/')
