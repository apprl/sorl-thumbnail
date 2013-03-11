import logging
import uuid
import itertools

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotAllowed, HttpResponsePermanentRedirect, HttpResponseNotFound
from django.contrib import auth
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext_lazy as _, ugettext

from apparel.models import Product
from apparel.utils import get_pagination_page, get_gender_from_cookie, JSONResponse
from apparel.tasks import facebook_push_graph
from profile.utils import get_facebook_user, get_current_user
from profile.forms import EmailForm, NotificationForm, NewsletterForm, FacebookSettingsForm, BioForm, PartnerSettingsForm, PartnerPaymentDetailForm, RegisterForm, RegisterCompleteForm
from profile.models import EmailChange, Follow, PaymentDetail
from profile.tasks import send_email_confirm_task
from profile.decorators import avatar_change, login_flow
from activity_feed.views import ActivityFeedRender

PROFILE_PAGE_SIZE = 30

def get_facebook_friends(request):
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        return get_user_model().objects.filter(username__in=friends_uids)

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
        info['products'] = Product.published_objects.filter(likes__user=profile, likes__active=True).count()

    content_type = ContentType.objects.get_for_model(get_user_model())
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
        queryset = Product.published_objects.filter(likes__user=profile, likes__active=True).order_by('-availability', '-likes__modified')

    paged_result, pagination = get_pagination_page(queryset, PROFILE_PAGE_SIZE, request.GET.get('page', 1), 1, 2)

    if request.is_ajax():
        return render(request, 'profile/fragments/likes.html', {
                'profile': profile,
                'pagination': pagination,
                'current_page': paged_result,
        })

    content = {
        'pagination': pagination,
        'current_page': paged_result,
        'next': request.get_full_path(),
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'APPAREL_GENDER': gender
    }
    content.update(form)
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
    gender = get_gender_from_cookie(request)
    htmlset = ActivityFeedRender(request, gender, profile, private=True)
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
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.look.filter(published=True).order_by('-modified')[:10]
        }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/profile.html', content)

@get_current_user
@avatar_change
def looks(request, profile, form, page=0):
    if profile == request.user:
        queryset = profile.look.order_by('-created')
    else:
        queryset = profile.look.filter(published=True).order_by('-created')

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
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request)
        }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/looks.html', content)

@get_current_user
@avatar_change
def followers(request, profile, form, page=0):
    content_type = ContentType.objects.get_for_model(get_user_model())
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
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.look.filter(published=True).order_by('-modified')[:4]
        }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/followers.html', content)

@get_current_user
@avatar_change
def following(request, profile, form, page=0):
    content_type = ContentType.objects.get_for_model(get_user_model())
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
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        'recent_looks': profile.look.filter(published=True).order_by('-modified')[:4]
        }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/following.html', content)

#
# Settings
#

@login_required
def settings_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_password'))

    form = PasswordChangeForm(request.user)

    return render(request, 'profile/settings_password.html', {'form': form})

@login_required
def settings_notification(request):
    """
    Handles the notification settings form
    """
    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

        newsletter_form = NewsletterForm(request.POST, request.FILES, instance=request.user)
        if newsletter_form.is_valid():
            newsletter_form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_notification'))

    form = NotificationForm(instance=request.user)
    newsletter_form = NewsletterForm(instance=request.user)

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
                    'username': request.user.display_name,
                    'link': 'http://%s%s' % (Site.objects.get_current().domain, reverse('profile.views.confirm_email')),
                    'token': token,
                })
            send_email_confirm_task.delay(subject, body, request.user.email)

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
        form = FacebookSettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

        return HttpResponseRedirect(reverse('profile.views.settings_facebook'))

    form = FacebookSettingsForm(instance=request.user)

    return render(request, 'profile/settings_facebook.html', {'facebook_settings_form': form})


@login_required
def settings_partner(request):
    """
    Handles the partner settings form.
    """
    try:
        instance = PaymentDetail.objects.get(user=request.user)
    except PaymentDetail.DoesNotExist:
        instance = None

    if request.method == 'POST':
        form = PartnerSettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

        details_form = PartnerPaymentDetailForm(request.POST, request.FILES, instance=instance)
        if details_form.is_valid():
            instance = details_form.save(commit=False)
            instance.user = request.user
            instance.save()

        return HttpResponseRedirect(reverse('profile.views.settings_partner'))

    form = PartnerSettingsForm(instance=request.user)
    details_form = PartnerPaymentDetailForm(instance=instance)

    return render(request, 'profile/settings_partner.html', {'form': form, 'details_form': details_form})

#
# Welcome login flow
#

@get_current_user
@login_flow
@avatar_change
def login_flow_bio(request, profile, forms):
    """
    Step 1: Bio
    """
    profile.login_flow = 'bio'
    profile.save()

    if request.method == 'POST':
        form = BioForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            if 'email' in form.changed_data:
                # Remove old email change confirmations
                EmailChange.objects.filter(user=request.user).delete()

                token = uuid.uuid4().hex
                email = form.cleaned_data['email']
                old_email = profile.email
                email_change = EmailChange.objects.create(user=request.user, email=email, token=token)

                subject = ''.join(render_to_string('profile/confirm_email_subject.html').splitlines())
                body = render_to_string('profile/confirm_email.html', {
                        'username': request.user.display_name,
                        'link': 'http://%s%s' % (Site.objects.get_current().domain, reverse('profile.views.confirm_email')),
                        'token': token,
                    })
                send_email_confirm_task.delay(subject, body, old_email)

                form.changed_data.remove('email')
                form.cleaned_data['email'] = profile.email

            form.save()

            return HttpResponseRedirect(reverse('profile.views.login_flow_friends'))
    else:
        form = BioForm(instance=profile)

    context = {
        'next_url': reverse('profile.views.login_flow_friends'),
        'email_form': form,
    }
    context.update(forms)
    return render(request, 'profile/login_flow_bio.html', context)


@get_current_user
@login_flow
@avatar_change
def login_flow_friends(request, profile, forms):
    """
    Step 2: Friends
    """
    profile.login_flow = 'friends'
    profile.save()

    if request.method == 'POST':
        for friend in get_user_model().objects.filter(id__in=request.POST.getlist('profile_ids', [])):
            follow, created = Follow.objects.get_or_create(user=profile, user_follow=friend)
            if not created and follow.active == False:
                follow.active = True
                follow.save()

            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(friend.get_absolute_url()))

        return HttpResponseRedirect(reverse('login-flow-featured'))

    context = {
        'login_flow_step': 'step-initial',
        'next_url': reverse('profile.views.login_flow_featured'),
        'profiles': get_facebook_friends(request)
    }
    context.update(forms)
    return render(request, 'profile/login_flow_friends.html', context)


@get_current_user
@login_flow
@avatar_change
def login_flow_featured(request, profile, forms):
    """
    Step 3: Featured members
    """
    profile.login_flow = 'featured'
    profile.save()

    if request.method == 'POST':
        for friend in get_user_model().objects.filter(id__in=request.POST.getlist('profile_ids', [])):
            follow, created = Follow.objects.get_or_create(user=profile, user_follow=friend)
            if not created and follow.active == False:
                follow.active = True
                follow.save()

            facebook_user = get_facebook_user(request)
            if facebook_user:
                facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(friend.get_absolute_url()))

        return HttpResponseRedirect(reverse('login-flow-brands'))

    profiles = get_user_model().objects.filter(is_brand=False).order_by('-popularity', '-followers_count')
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        profiles = profiles.exclude(username__in=friends_uids)
        profiles = profiles.exclude(pk=profile.pk)

    context = {
        'login_flow_step': 'step-members',
        'next_url': reverse('profile.views.login_flow_brands'),
        'profiles': profiles[:21],
    }
    context.update(forms)
    return render(request, 'profile/login_flow_featured.html', context)


@get_current_user
@login_flow
@avatar_change
def login_flow_brands(request, profile, forms):
    """
    Step 4: Brands
    """
    profile.login_flow = 'brands'
    profile.save()

    context = {
        'login_flow_step': 'step-brands',
        'next_url': reverse('profile.views.login_flow_like'),
        'profiles': get_user_model().objects.filter(is_brand=True).order_by('-followers_count')[:21]
    }
    context.update(forms)
    return render(request, 'profile/login_flow_brands.html', context)


@get_current_user
@login_flow
@avatar_change
def login_flow_like(request, profile, form):
    """
    Step 5: Like us on facebook
    """
    profile.login_flow = 'like'
    profile.save()

    context = {
        'next_url': reverse('profile.views.login_flow_complete'),
    }
    context.update(form)
    return render(request, 'profile/login_flow_like.html', context)

@get_current_user
@login_flow
def login_flow_complete(request, profile):
    """
    Step 6: Login flow is complete
    """
    profile.login_flow = 'complete'
    profile.save()

    return HttpResponseRedirect(reverse('profile-likes', args=[profile.slug]))


#
# Register view
#

def register(request):
    return render(request, 'registration/registration.html')

def register_email(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.is_active = False
            instance.confirmation_key = uuid.uuid4().hex
            instance.save()

            # Send confirmation email
            subject = _('Activate your Apprl account')
            body = render_to_string('registration/registration_activation_email.html', {
                    'name': instance.display_name,
                    'link': request.build_absolute_uri(reverse('auth_register_activate', args=[instance.confirmation_key])),
                })
            send_email_confirm_task.delay(subject, body, instance.email)

            return HttpResponseRedirect(reverse('auth_register_complete'))
    else:
        form = RegisterForm()

    return render(request, 'registration/registration_email.html', {'form': form})


def register_complete(request):
    if request.method == 'POST':
        form = RegisterCompleteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                instance = get_user_model()._default_manager.get(email=email, is_active=False)
                instance.confirmation_key = uuid.uuid4().hex
                instance.save()

                # Send confirmation email
                subject = _('Activate your Apprl account')
                body = render_to_string('registration/registration_activation_email.html', {
                        'name': instance.display_name,
                        'link': request.build_absolute_uri(reverse('auth_register_activate', args=[instance.confirmation_key])),
                })
                send_email_confirm_task.delay(subject, body, instance.email)

                return HttpResponseRedirect('%s?sent=1' % (reverse('auth_register_complete'),))

            except get_user_model().DoesNotExist:
                pass

    else:
        form = RegisterCompleteForm()

    return render(request, 'registration/registration_complete.html', {'form': form})


def register_activate(request, key):
    try:
        user = get_user_model().objects.get(confirmation_key=key)
        user.is_active = True
        user.confirmation_key = None
        user.save()

        # Send welcome email
        subject = ugettext('Welcome to Apprl')
        body = render_to_string('profile/email_welcome.html')
        send_email_confirm_task.delay(subject, body, user.email)

        return HttpResponseRedirect(reverse('auth_login'))
    except get_user_model().DoesNotExist:
        return render(request, 'registration/registration_invalid_activation.html')


#
# Login view
#

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
        if user and user.is_active:
            auth.login(request, user)
            if request.is_ajax():
                return JSONResponse({'uid': user.pk, 'next': _get_next(request)})

            if user.login_flow != 'complete':
                response = HttpResponseRedirect(reverse('profile.views.login_flow_%s' % (user.login_flow)))
                response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=user.gender, max_age=365 * 24 * 60 * 60)
                return response

            return HttpResponseRedirect(_get_next(request))

    return HttpResponseRedirect('/')

@login_required
def facebook_connect(request):
    """
    Connect existing account with Facebook.
    """
    if request.POST:
        access_token = request.POST.get('access_token', '')
        user_id = request.POST.get('uid', '')

        try:
            get_user_model().objects.get(facebook_user_id=user_id)
        except get_user_model().DoesNotExist:
            request.user.facebook_user_id = user_id
            request.user.save()

            if request.is_ajax():
                return JSONResponse({'uid': user.pk, 'next': _get_next(request)})

            return HttpResponseRedirect(_get_next(request))

        return HttpResponseRedirect('%s?error=1' % (_get_next(request),))

    return HttpResponseRedirect(_get_next(request))
