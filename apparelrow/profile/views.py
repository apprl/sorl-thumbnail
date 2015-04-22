import uuid
import urlparse
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.template import Context, Template, RequestContext
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.loading import get_model

import requests

from apparelrow.apparel.utils import get_paged_result, JSONResponse, get_ga_cookie_cid
from apparelrow.apparel.tasks import facebook_push_graph, google_analytics_event

from apparelrow.profile.utils import get_facebook_user, get_current_user, send_welcome_mail, reset_facebook_user
from apparelrow.profile.forms import EmailForm, NotificationForm, NewsletterForm, FacebookSettingsForm, BioForm, PartnerSettingsForm, PartnerPaymentDetailForm, RegisterForm, RegisterCompleteForm
from apparelrow.profile.models import EmailChange, Follow, PaymentDetail
from apparelrow.profile.tasks import send_email_confirm_task, mail_managers_task
from apparelrow.profile.decorators import avatar_change

from apparelrow.apparel.browse import browse_products

PROFILE_PAGE_SIZE = 24

logger = logging.getLogger('apparel.debug')

def get_facebook_friends(request):
    facebook_user = get_facebook_user(request)
    if request.user.is_authenticated() and facebook_user:
        friends = facebook_user.graph.get_connections('me', 'friends')
        friends_uids = [f['id'] for f in friends['data']]
        return get_user_model().objects.filter(is_active=True, username__in=friends_uids)

def get_profile_sidebar_info(request, profile):
    """
    Get the misc. information needed in the sidebar of the profile page

    Returns a dict containing the extra information
    """
    info = {'products': 0, 'following': 0}

    if profile.is_brand:
        info['products'] = get_model('apparel', 'Product').valid_objects.filter(manufacturer=profile.brand_id).order_by('-date_added').count()
    else:
        info['products'] = get_model('apparel', 'Product').published_objects.filter(likes__user=profile, likes__active=True).count()

    info['following'] = Follow.objects.filter(user_follow__is_hidden=False, user=profile, active=True).count()

    return info


@login_required
def save_description(request):
    """
    Save user description and return a parsed version for display.
    """
    description = request.POST.get('description', '')
    description = description.replace(u'\xa0', ' ').strip()

    request.user.about = description
    request.user.save()

    t = Template('{% load apparel_extras %}{{ description|urlize_target_blank|linebreaksbr }}')
    c = Context({'description': description})
    description_html = t.render(c)

    return HttpResponse(description_html, mimetype='text/html')


@get_current_user
@avatar_change
def likes(request, profile, form, page=0):
    """
    Displays the profile likes page.
    """
    content = {
        'next': request.get_full_path(),
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
    }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    is_brand = False
    if profile.is_brand:
        is_brand = profile.brand_id

    return browse_products(request,
                           template='profile/likes.html',
                           gender=request.GET.get('gender', 'A'),
                           user_gender='A',
                           language=None,
                           user_id=profile.pk,
                           disable_availability=not is_brand,
                           is_brand=is_brand,
                           **content)


@get_current_user
@avatar_change
def looks(request, profile, form, page=0):

    if profile == request.user:
        queryset = profile.look.order_by('-created')
    else:
        queryset = profile.look.filter(published=True).order_by('-created')

    paged_result = get_paged_result(queryset, 12, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/look_list.html', {
                'current_page': paged_result
            })

    content = {
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
def likedlooks(request, profile, form, page=0):
    #logger.info("looks called")

    #retrieve looks for which a like for the current user exists and is active
    looks = get_model('apparel', 'Look').published_objects.filter(likes__user=profile, likes__active=True)

    paged_result = get_paged_result(looks, 12, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/look_list.html', {
                'current_page': paged_result
            })

    content = {
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
def brandlooks(request, profile, form, page=0):
    logger.info("brand looks called")

    #retrieve looks for which a like for the current user exists and is active
    looks = get_model('apparel', 'Look').published_objects.filter(components__product__static_brand = profile.name)

    paged_result = get_paged_result(looks, 12, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/look_list.html', {
                'current_page': paged_result
            })

    content = {
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
def shops(request, profile, form, page=0):
    if profile == request.user:
        queryset = profile.shop.order_by('-modified')
    else:
        return HttpResponse('Unauthorized', status=401)

    paged_result = get_paged_result(queryset, 12, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/shop_list.html', {
            'current_page': paged_result
        })

    content = {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'profile': profile,
        'avatar_absolute_url': profile.avatar_large_absolute_uri(request)
    }

    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/shops.html', content)



@get_current_user
@avatar_change
def followers(request, profile, form, page=0):
    queryset = get_user_model().objects.filter(is_hidden=False, following__user_follow=profile, following__active=True) \
                                       .order_by('name', 'first_name', 'username')

    paged_result = get_paged_result(queryset, PROFILE_PAGE_SIZE, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/user_list.html', {
                'current_page': paged_result
        })

    content = {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        }
    content.update(form)
    content.update(get_profile_sidebar_info(request, profile))

    return render(request, 'profile/followers.html', content)

@get_current_user
@avatar_change
def following(request, profile, form, page=0):
    queryset = get_user_model().objects.filter(is_hidden=False, followers__user=profile, followers__active=True) \
                                       .order_by('name', 'first_name', 'username')

    paged_result = get_paged_result(queryset, PROFILE_PAGE_SIZE, request.GET.get('page', '1'))

    if request.is_ajax():
        return render(request, 'apparel/fragments/user_list.html', {
                'current_page': paged_result
        })

    content = {
        'current_page': paged_result,
        'next': request.get_full_path(),
        'profile': profile,
        'avatar_absolute_uri': profile.avatar_large_absolute_uri(request),
        }
    content.update(form)
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
        form = NotificationForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

        newsletter_form = NewsletterForm(request.POST, request.FILES, instance=request.user)
        if newsletter_form.is_valid():
            newsletter_form.save()

        return HttpResponseRedirect(reverse('settings-notification'))

    form = NotificationForm(instance=request.user, isPublisher=request.user.is_partner)
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
            return render(request, 'profile/confirm_email_used_token.html')
        request.user.email = email_change.email
        request.user.save()
        email_change.delete()

    return HttpResponseRedirect(reverse('settings-email'))

@login_required
def settings_email(request):
    """
    Handles the email settings and facebook form on settings
    """
    form_has_error = False
    try:
        email_change = EmailChange.objects.get(user=request.user)
    except EmailChange.DoesNotExist:
        email_change = None
    FormClass = PasswordChangeForm if request.user.password else SetPasswordForm

    if request.method == 'POST':
        password_form = FormClass(request.user)
        facebook_form = FacebookSettingsForm(request.POST, request.FILES, instance=request.user)
        if facebook_form.is_valid():
            facebook_form.save()

        form = EmailForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # Remove old email change confirmations
            EmailChange.objects.filter(user=request.user).delete()

            token = uuid.uuid4().hex
            email = form.cleaned_data['email']
            subject = ''.join(render_to_string('profile/confirm_email_subject.html').splitlines())
            body = render_to_string('profile/confirm_email.html', {
                    'username': request.user.display_name,
                    'link': 'http://%s%s' % (Site.objects.get_current().domain, reverse('user-confirm-email')),
                    'token': token,
                })
            send_email_confirm_task.delay(subject, body, request.user.email)
        else:
            return render_to_response('profile/settings_email.html',
                                  {'email_form': form, 'email_change': email_change,
                                   'form': password_form, 'facebook_settings_form': facebook_form },
                                  context_instance=RequestContext(request))
        return HttpResponseRedirect(reverse('settings-email'))

    form = EmailForm()
    password_form = FormClass(request.user)
    facebook_form = FacebookSettingsForm(instance=request.user)


    return render(request, 'profile/settings_email.html', {
            'email_form': form,
            'email_change': email_change,
            'form': password_form,
            'facebook_settings_form': facebook_form
        })


@login_required
def settings_password(request):
    """
    Handles the password form on settings
    """
    try:
        email_change = EmailChange.objects.get(user=request.user)
    except EmailChange.DoesNotExist:
        email_change = None
    FormClass = PasswordChangeForm if request.user.password else SetPasswordForm
    facebook_form = FacebookSettingsForm(instance=request.user)
    form = EmailForm()
    if request.method == 'POST':
        password_form = FormClass(request.user, request.POST)
        if password_form.is_valid():
            password_form.save()

            if request.user.password:
                messages.success(request, _('Password was updated'))
            else:
                messages.success(request, _('Password was added'))
        else:
            return render_to_response('profile/settings_email.html',
                                  {'email_form': form, 'email_change': email_change,
                                   'form': password_form, 'facebook_settings_form': facebook_form},
                                  context_instance=RequestContext(request))
    password_form = FormClass(request.user)

    return render(request, 'profile/settings_email.html', {
        'email_form': form,
        'email_change': email_change,
        'form': password_form,
        'facebook_settings_form': facebook_form
    })

@login_required
def settings_publisher(request):
    """
    Handles the partner settings form.
    """
    try:
        instance = PaymentDetail.objects.get(user=request.user)
    except PaymentDetail.DoesNotExist:
        instance = None

    if request.method == 'POST':
        form = PartnerSettingsForm(request.POST, request.FILES, instance=request.user)
        details_form = PartnerPaymentDetailForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
        else:
            return render_to_response('profile/settings_publisher.html', {'form': form, 'form': form, 'details_form': details_form }, context_instance=RequestContext(request))


        if details_form.is_valid():
            instance = details_form.save(commit=False)
            instance.user = request.user
            instance.save()
        else:
            form_errors = details_form.errors
            return render_to_response('profile/settings_publisher.html', {'form': form, 'details_form': details_form, 'form_errors': form_errors}, context_instance=RequestContext(request))

        return HttpResponseRedirect(reverse('settings-publisher'))

    form = PartnerSettingsForm(instance=request.user)
    details_form = PartnerPaymentDetailForm(instance=instance)

    return render(request, 'profile/settings_publisher.html', {'form': form, 'details_form': details_form})

#
# Welcome login flow
#

@login_required
def login_flow_brands(request):
    """
    Step 1: Brands
    """
    if request.user.is_authenticated() and request.user.login_flow == 'complete':
        return HttpResponseRedirect(reverse('login-flow-complete'))


    request.user.login_flow = 'brands'
    request.user.save()

    if not request.user.following.exists():
        follow_featured_auto(request)

    queryset = get_user_model().objects.filter(is_brand=True).order_by('-followers_count')[:24]
    paged_result = get_paged_result(queryset, 24, request.GET.get('page', '1'))

    context = {
        'current_page': paged_result,
        'next_url': reverse('login-flow-complete'),
    }
    return render(request, 'profile/login_flow_welcome.html', context)


@login_required
def login_flow_complete(request):
    """
    Step 2: Login flow is complete
    """
    request.user.login_flow = 'complete'
    request.user.save()

    return render(request, 'profile/login_flow_complete.html')


#
# Register view
#


def follow_featured_auto(request):
    # XXX: disabled follow featured users automatically
    #profiles = get_user_model().objects.filter(is_active=True, is_brand=False)
    #profiles = profiles.exclude(pk=request.user.pk)
    #if request.user.gender == 'M':
        #profiles = profiles.order_by('-popularity_men', '-followers_count')
    #else:
        #profiles = profiles.order_by('-popularity', '-followers_count')

    #friends = list(profiles[:20])
    friends = []

    facebook_friends = get_facebook_friends(request)
    if facebook_friends:
        friends = friends + list(facebook_friends)

    facebook_user = get_facebook_user(request)
    for friend in friends:
        follow, created = Follow.objects.get_or_create(user=request.user, user_follow=friend)
        if not created and follow.active == False:
            follow.active = True
            follow.save()

        if facebook_user:
            facebook_push_graph.delay(request.user.pk, facebook_user.access_token, 'follow', 'profile', request.build_absolute_uri(friend.get_absolute_url()))


def send_confirmation_email(request, instance):
    subject = ugettext('Nearly created your membership...')
    body = render_to_string('registration/registration_activation_email.html', {
            'name': instance.display_name,
            'link': request.build_absolute_uri(reverse('auth_register_activate', args=[instance.confirmation_key])),
        })
    send_email_confirm_task.delay(subject, body, instance.email)


def register(request):
    return render(request, 'registration/registration.html')

def register_email(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.is_active = False
            instance.name = ('%s %s' % (instance.first_name, instance.last_name)).strip()
            instance.confirmation_key = uuid.uuid4().hex
            instance.save()

            # Send confirmation email
            send_confirmation_email(request, instance)

            response = HttpResponseRedirect(reverse('auth_register_complete'))
            response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=instance.gender, max_age=365 * 24 * 60 * 60)

            return response

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
                send_confirmation_email(request, instance)

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

        # Send google analytics event
        google_analytics_event.delay(get_ga_cookie_cid(request), 'Member', 'Signup', user.slug)

        # Send welcome email
        send_welcome_mail(user)

        # XXX: Bypass authenticate step by settings backend on user
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth.login(request, user)
        reset_facebook_user(request)

        mail_subject = 'New email user activation: %s' % (user.display_name_live,)
        mail_managers_task.delay(mail_subject, 'URL: %s' % (request.build_absolute_uri(user.get_absolute_url()),))

        response = HttpResponseRedirect(reverse('login-flow-%s' % (user.login_flow)))
        response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=user.gender, max_age=365 * 24 * 60 * 60)
        return response

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
        return request.session.pop('next')
    elif 'next' in request.GET:
        return request.GET.get('next')
    elif 'next' in request.POST:
        return request.POST.get('next')

    return getattr(settings, 'LOGIN_REDIRECT_URL', '/')


def flow(request):
    try:
        if request.user.is_authenticated() and request.user.advertiser_store:
            return HttpResponseRedirect(reverse('advertiser-store-admin'))
    except ObjectDoesNotExist:
        pass

    if request.user.is_authenticated() and request.user.login_flow != 'complete' and not request.user.is_brand:
        if request.user.login_flow == 'brands' or request.user.login_flow == 'complete':
            url = reverse('login-flow-%s' % (request.user.login_flow))
        else:
            url = reverse('login-flow-brands')

        response = HttpResponseRedirect(url)
        response.set_cookie(settings.APPAREL_GENDER_COOKIE,
                            value=request.user.gender,
                            max_age=365 * 24 * 60 * 60)

        return response

    return HttpResponseRedirect(_get_next(request))


def facebook_redirect_login(request):
    if request.GET.get('code'):
        facebook_token_uri = 'https://graph.facebook.com/oauth/access_token?client_id={app_id}&redirect_uri={redirect_uri}&client_secret={app_secret}&code={code_parameter}'
        response = requests.get(facebook_token_uri.format(app_id=settings.FACEBOOK_APP_ID,
                                                          redirect_uri=request.build_absolute_uri(reverse('auth_facebook_login')),
                                                          app_secret=settings.FACEBOOK_SECRET_KEY,
                                                          code_parameter=request.GET.get('code')))
        if response.status_code == 200:
            query_dict = urlparse.parse_qs(response.text)
            access_token = query_dict.get('access_token')[0]

            facebook_debug_token_uri = 'https://graph.facebook.com/debug_token?input_token={access_token}&access_token={app_access_token}'
            response = requests.get(facebook_debug_token_uri.format(access_token=access_token,
                                                                    app_access_token=settings.FACEBOOK_APP_ACCESS_TOKEN))
            if response.status_code == 200:
                response_json = response.json()
                user = auth.authenticate(fb_uid=response_json['data']['user_id'], fb_graphtoken=access_token, request=request)
                if user and user.is_active:
                    auth.login(request, user)
                    reset_facebook_user(request)

                    return _login_flow(request, user)
    elif request.GET.get('error_reason'):
        if request.GET.get('error_reason') == 'user_denied' and request.GET.get('error') == 'access_denied':
            return HttpResponseRedirect('{0}?error=user_denied'.format(reverse('auth_login')))

        return HttpResponseRedirect('{0}?error=1'.format(reverse('auth_login')))

    return HttpResponseRedirect('/')


def facebook_login(request):
    if request.POST:
        access_token = request.POST.get('access_token', '')
        uid = request.POST.get('uid', '')

        user = auth.authenticate(fb_uid=uid, fb_graphtoken=access_token, request=request)
        if user and user.is_active:
            auth.login(request, user)
            reset_facebook_user(request)

            return _login_flow(request, user)

    return HttpResponseRedirect('/')


def _login_flow(request, user):
    if request.is_ajax():
        return JSONResponse({'uid': user.pk, 'next': _get_next(request)})

    disable_flow = request.POST.get('disable_flow', False)

    if user.login_flow != 'complete' and not disable_flow:
        response = HttpResponseRedirect(reverse('login-flow-%s' % (user.login_flow)))
        response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=user.gender, max_age=365 * 24 * 60 * 60)
        return response
    elif user.login_flow != 'complete' and disable_flow:
        follow_featured_auto(request)

    return HttpResponseRedirect(_get_next(request))


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


def login_as_user(request, user_id):
    if request.user.is_authenticated() and request.user.is_superuser:
        target_user = get_object_or_404(get_user_model(), pk=user_id)
        if target_user and target_user.is_active:
            for backend in auth.get_backends():
                if target_user == backend.get_user(target_user.pk):
                    target_user.backend = '%s.%s' % (backend.__module__, backend.__class__.__name__)
                    break

            auth.login(request, target_user)
            reset_facebook_user(request)

            return HttpResponseRedirect('/')

    raise Http404
