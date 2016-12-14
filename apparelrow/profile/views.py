import uuid
import urlparse
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.template import Context, Template, RequestContext
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseForbidden
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models.loading import get_model
from django.views.generic import RedirectView
from django.views.generic import TemplateView, ListView, View, DetailView, FormView
from django.views.decorators.csrf import csrf_protect

import requests
from apparelrow.apparel.models import Look

from apparelrow.apparel.utils import get_paged_result, JSONResponse, get_ga_cookie_cid
from apparelrow.apparel.tasks import facebook_push_graph, google_analytics_event

from apparelrow.profile.utils import get_facebook_user, send_welcome_mail, reset_facebook_user
from apparelrow.profile.forms import EmailForm, NotificationForm, NewsletterForm, FacebookSettingsForm, BioForm, \
    PartnerSettingsForm, PartnerPaymentDetailForm, RegisterForm, RegisterCompleteForm, \
    LocationForm, ProfileImageForm, PartnerNotificationsForm
from apparelrow.profile.models import EmailChange, Follow, PaymentDetail
from apparelrow.profile.tasks import send_email_confirm_task, mail_managers_task
from apparelrow.profile.decorators import avatar_change, get_current_user

from apparelrow.apparel.browse import browse_products

PROFILE_PAGE_SIZE = 24

logger = logging.getLogger('apparel.debug')
log = logging.getLogger("apparelrow")

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


class RedirectProfileView(RedirectView):
    def get_redirect_url(self, slug):
        return reverse_lazy('profile-likes', args=(slug,))


class RedirectWidgetView(RedirectView):
    def get_redirect_url(self, slug):
        return reverse_lazy('profile-shops', args=(slug,))


class ProfileView(TemplateView):
    template_name = 'profile/default.html'

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)
        image_form = ProfileImageForm(instance=context["profile"])
        forms = [('change_image_form', image_form)]
        context.update(get_profile_sidebar_info(self.request, context["profile"]))
        context.update({"is_brand": context["profile"].brand_id if context["profile"].is_brand else False,
                        "form": forms[0],
                        "avatar_absolute_uri":context["profile"].avatar_large_absolute_uri(self.request)})
        return context

    @method_decorator(get_current_user)
    def get(self, request, *args, **kwargs):
        """
        Displays the default page (all).
        """
        profile = args[0]
        context = self.get_context_data(profile=profile)
        return browse_products(request,
                               template=self.template_name,
                               gender=request.GET.get('gender', 'A'),
                               user_gender='A',
                               language=None,
                               user_id=profile.pk,
                               disable_availability=not context["is_brand"],
                               **context)

    @method_decorator(get_current_user)
    def post(self, request, *args, **kwargs):
        profile = args[0]
        if profile != request.user:
            return HttpResponseForbidden()

        if 'change_image_form' in request.POST:
            image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if image_form.is_valid():
                image_form.save()

        return HttpResponseRedirect(request.get_full_path())


class ProfileListLookView(ListView):
    template_name = 'profile/looks.html'
    template_name_ajax = 'apparel/fragments/look_list.html'
    profile = None
    user = None
    paginate_by = 12

    def get_queryset(self):
        if self.profile == self.user:
            return self.profile.look.order_by('-created')
        else:
            return self.profile.look.filter(published=True).order_by('-created')

    def get_context_data(self, **kwargs):
        context = super(ProfileListLookView, self).get_context_data(**kwargs)
        context.update(get_profile_sidebar_info(self.request, context["profile"]))
        context.update({"avatar_absolute_uri": context["profile"].avatar_large_absolute_uri(self.request),
                        "next":self.request.get_full_path(),
                        "form":None,
                        "current_page":context.pop("page_obj")})
        return context

    @method_decorator(get_current_user)
    def get(self, request, *args, **kwargs):
        self.profile = args[0]
        self.user = request.user
        self.object_list = self.get_queryset()
        context = self.get_context_data(profile=self.profile)
        #paged_result = get_paged_result(self.object_list, 12, request.GET.get('page', '1'))
        if request.is_ajax():
            return render(request, self.template_name_ajax, {
                'current_page': context["current_page"]
            })
        else:
            return render(request, self.template_name, context)

    @method_decorator(get_current_user)
    def post(self, request, *args, **kwargs):
        self.profile = args[0]
        if self.profile != request.user:
            return HttpResponseForbidden()

        if 'change_image_form' in request.POST:
            image_form = ProfileImageForm(request.POST, request.FILES, instance=self.profile)
            if image_form.is_valid():
                image_form.save()

        return HttpResponseRedirect(request.get_full_path())


class ProfileListLikedLookView(ProfileListLookView):
    def get_queryset(self):
        return get_model('apparel', 'Look').published_objects.filter(likes__user=self.profile, likes__active=True).order_by('-created')


class ProfileListBrandLookView(ProfileListLookView):
    def get_queryset(self):
        return get_model('apparel', 'Look').published_objects.filter(components__product__static_brand = self.profile.name)


class ProfileListShopView(ProfileListLookView):
    template_name = 'profile/shops.html'
    template_name_ajax = 'apparel/fragments/shop_list.html'

    def get_queryset(self):
        from itertools import chain
        if self.profile == self.user:
            queryset = sorted(chain(self.profile.shop.all(), self.profile.product_widget.all()),
            key=lambda instance: instance.modified, reverse=True)
            return queryset
            #return self.profile.shop.order_by('-modified')
        else:
            raise PermissionDenied("Unauthorized")


class ProfileListFollowersView(ProfileListLookView):
    template_name = 'profile/followers.html'
    template_name_ajax = 'apparel/fragments/user_list.html'
    paginate_by = PROFILE_PAGE_SIZE

    def get_queryset(self):
        return get_user_model().objects.filter(is_hidden=False, following__user_follow=self.profile, following__active=True) \
                                       .order_by('name', 'first_name', 'username')


class ProfileListFollowingView(ProfileListLookView):
    template_name = 'profile/following.html'
    template_name_ajax = 'apparel/fragments/user_list.html'
    paginate_by = PROFILE_PAGE_SIZE

    def get_queryset(self):
        return get_user_model().objects.filter(is_hidden=False, followers__user=self.profile, followers__active=True) \
                                       .order_by('name', 'first_name', 'username')


@DeprecationWarning
@get_current_user
@avatar_change
def default(request, profile, form, page=0):
    """
    Displays the default page (all). Id
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
                           template='profile/default.html',
                           gender=request.GET.get('gender', 'A'),
                           user_gender='A',
                           language=None,
                           user_id=profile.pk,
                           disable_availability=not is_brand,
                           is_brand=is_brand,
                           **content)

@DeprecationWarning
@get_current_user
@avatar_change
def likes(request, profile, form, page=0):
    """
    !!! Replaced with ProfileView !!!
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

@DeprecationWarning
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

@DeprecationWarning
@get_current_user
@avatar_change
def likedlooks(request, profile, form, page=0):
    #logger.info("looks called")

    #retrieve looks for which a like for the current user exists and is active
    looks = get_model('apparel', 'Look').published_objects.filter(likes__user=profile, likes__active=True).order_by('-created')

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

@DeprecationWarning
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

@DeprecationWarning
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
def widgets(request, profile, form, page=0):
    """

    :param request:
    :param profile:
    :param form:
    :param page:
    :return:
    """

    from itertools import chain
    if profile == request.user:
        queryset = sorted(chain(profile.shop.all(), profile.product_widget.all()),
            key=lambda instance: instance.modified, reverse=True)
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


@DeprecationWarning
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

@DeprecationWarning
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
@DeprecationWarning
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

        return HttpResponseRedirect(reverse('settings-notifications'))

    form = NotificationForm(instance=request.user, is_publisher=request.user.is_partner)
    newsletter_form = NewsletterForm(instance=request.user)

    return render(request, 'profile/settings_notification.html', {'notification_form': form, 'newsletter_form': newsletter_form})

class UserSettingsNotificationView(TemplateView):
    template_name = 'profile/settings_notification.html'

    def get_context_data(self, **kwargs):
        context = super(UserSettingsNotificationView, self).get_context_data(**kwargs)

        context.update({
            'newsletter_form': NewsletterForm(instance=self.request.user),
            'notification_form': NotificationForm(instance=self.request.user, is_publisher=self.request.user.is_partner),
        })
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        notification_form = NotificationForm(request.POST, request.FILES, instance=request.user)
        if notification_form.is_valid():
            notification_form.save()

        newsletter_form = NewsletterForm(request.POST, request.FILES, instance=request.user)
        if newsletter_form.is_valid():
            newsletter_form.save()

        context.update({'newsletter_form': newsletter_form,
                        'notification_form': notification_form})
        return render(request, self.template_name, context)

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

    return HttpResponseRedirect(reverse('settings-account'))


class UserSettingsUsernameView(TemplateView):
    template_name = "profile/username.html"


class UserSettingsEmailView(FormView):
    """
    View method for account settings in the profile/settings.
    """
    template_name = 'profile/settings_account.html'
    context_object_name = 'email_form'
    form_class = EmailForm

    def get_form_class(self):
        return EmailForm

    def get_context_data(self, **kwargs):
        context = super(UserSettingsEmailView, self).get_context_data(**kwargs)
        FormClass = PasswordChangeForm if self.request.user.password else SetPasswordForm
        try:
            email_change = EmailChange.objects.get(user=self.request.user)
        except EmailChange.DoesNotExist:
            email_change = None

        email_form = EmailForm()
        facebook_form = FacebookSettingsForm(instance=self.request.user)
        location_form = LocationForm(instance=self.request.user)
        location_warning_form = PartnerNotificationsForm(instance=self.request.user)
        context.update({
            'location_form': location_form,
            'email_form': email_form,
            'email_change': email_change,
            'form': FormClass(self.request.user),
            'facebook_settings_form': facebook_form,
            'location_warning_form': location_warning_form
        })
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        facebook_form = FacebookSettingsForm(request.POST, request.FILES, instance=request.user)
        location_form = LocationForm(request.POST, instance=request.user)
        FormClass = PasswordChangeForm if self.request.user.password else SetPasswordForm
        location_warning_form = PartnerNotificationsForm(request.POST, request.FILES, instance=request.user)

        if location_warning_form.is_valid():
            location_warning_form.save()
            context.update({'location_warning_form': location_warning_form})
        # Always save the facebook form
        if facebook_form.is_valid():
            facebook_form.save()
        else:
            context.update({'facebook_settings_form': facebook_form})

        email_form = EmailForm(request.POST, request.FILES, instance=request.user)
        if "email" in request.POST:
            # If the change email form has been sent
            if email_form.is_valid():
                # Remove old email change confirmations
                EmailChange.objects.filter(user=self.request.user).delete()

                token = uuid.uuid4().hex
                email = email_form.cleaned_data['email']
                # Create a new email change entry
                EmailChange.objects.create(email=email, token=token, user=request.user)
                subject = ''.join(render_to_string('profile/confirm_email_subject.html').splitlines())
                body = render_to_string('profile/confirm_email.html', {
                        'username': self.request.user.display_name,
                        'link': 'http://{host}{path}'.format(host=Site.objects.get_current().domain, path=reverse('user-confirm-email')),
                        'token': token,
                    })
                send_email_confirm_task.delay(subject, body, self.request.user.email)
                #return HttpResponseRedirect(reverse('settings-account'))
                context.update({"email_form": email_form})

        elif "old_password" in request.POST:
            # If the change password form has been sent
            password_form = FormClass(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()

                if request.user.password:
                    messages.success(request, _('Password was updated'))
                else:
                    messages.success(request, _('Password was added'))
                context.update({'form': password_form})

        elif "location" in request.POST:
            if location_form.is_valid():
                location_form.save()

        return render(request, self.template_name, context)

@DeprecationWarning
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

        location_warning_form = PartnerNotificationsForm(request.POST, request.FILES, instance=request.user)
        if location_warning_form.is_valid():
            location_warning_form.save()

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
            return render_to_response('profile/settings_account.html',
                                  {'email_form': form, 'email_change': email_change,
                                   'form': password_form, 'facebook_settings_form': facebook_form },
                                  context_instance=RequestContext(request))
        return HttpResponseRedirect(reverse('settings-account'))

    form = EmailForm()
    location_warning_form = PartnerNotificationsForm(instance=request.user)
    password_form = FormClass(request.user)
    facebook_form = FacebookSettingsForm(instance=request.user)

    return render(request, 'profile/settings_account.html', {
            'email_form': form,
            'email_change': email_change,
            'form': password_form,
            'facebook_settings_form': facebook_form,
            'location_warning_form': location_warning_form
        })

@DeprecationWarning
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
            return render_to_response('profile/settings_account.html',
                                  {'email_form': form, 'email_change': email_change,
                                   'form': password_form, 'facebook_settings_form': facebook_form},
                                  context_instance=RequestContext(request))
    password_form = FormClass(request.user)

    return render(request, 'profile/settings_account.html', {
        'email_form': form,
        'email_change': email_change,
        'form': password_form,
        'facebook_settings_form': facebook_form
    })

@DeprecationWarning
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
            return render_to_response('profile/settings_publisher.html', {'form': form, 'details_form': details_form }, context_instance=RequestContext(request))


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

class PublisherSettingsNotificationView(TemplateView):
    template_name = 'profile/settings_publisher.html'

    def get_context_data(self, **kwargs):
        context = super(PublisherSettingsNotificationView, self).get_context_data(**kwargs)
        try:
            instance = PaymentDetail.objects.get(user=self.request.user)
        except PaymentDetail.DoesNotExist:
            instance = None
        context.update({
            'instance': instance,
            'form': PartnerSettingsForm(instance=self.request.user),
            'details_form': PartnerPaymentDetailForm(instance=instance),
            'location_warning_form':PartnerNotificationsForm(instance=self.request.user)
        })
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context["form"] = PartnerSettingsForm(request.POST, request.FILES, instance=request.user)
        context["details_form"] = PartnerPaymentDetailForm(request.POST, request.FILES, instance=context['instance'])
        # Todo: change here
        context["location_warning_form"] = PartnerNotificationsForm(request.POST, request.FILES, instance=request.user)
        if context["location_warning_form"].is_valid():
            context["location_warning_form"].save()

        if context["form"].is_valid():
            context["form"].save()
        else:
            return render(request, self.template_name, context)

        if context["details_form"].is_valid():
            instance = context["details_form"].save(commit=False)
            instance.user = request.user
            instance.save()
        else:
            context.update({"form_errors": context["details_form"].errors})
        return render(request, self.template_name, context)

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


class RegisterView(TemplateView):
    template_name = 'registration/registration.html'

@DeprecationWarning
def register(request):
    return render(request, 'registration/registration.html')


class RegisterEmailFormView(FormView):
    # work in progress
    template_name = 'registration/registration_email.html'
    #template_name = 'registration/registration_email-2.html'
    form_class = RegisterForm

    def get_success_url(self):
        return reverse('auth_register_complete')

    def get_form_kwargs(self):
        kwargs = super(RegisterEmailFormView, self).get_form_kwargs()
        if "register_email" in self.request.session:
            kwargs["initial"].update({"email": self.request.session.pop("register_email"),
             "password1": self.request.session.get("register_password"),
             "password2": self.request.session.pop("register_password")})

        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.is_active = False
        instance.name = ('%s %s' % (instance.first_name, instance.last_name)).strip()
        instance.confirmation_key = uuid.uuid4().hex
        instance.save()

        # Send confirmation email
        send_confirmation_email(self.request, instance)
        response = HttpResponseRedirect(self.get_success_url())
        response.set_cookie(settings.APPAREL_GENDER_COOKIE, value=instance.gender, max_age=365 * 24 * 60 * 60)
        response.set_cookie(settings.APPAREL_WELCOME_COOKIE, value=True, max_age=5 * 365 * 24 * 60 * 60)
        return response

@DeprecationWarning
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
            response.set_cookie(settings.APPAREL_WELCOME_COOKIE, value=True, max_age=5 * 365 * 24 * 60 * 60)
            return response
    else:
        form = RegisterForm()

    return render(request, 'registration/registration_email.html', {'form': form})


class RegisterEmailCompleteFormView(FormView):
    template_name = 'registration/registration_complete.html'
    form_class = RegisterCompleteForm
    success_url = reverse_lazy('auth_register_complete')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            instance = get_user_model()._default_manager.get(email=email, is_active=False)
            instance.confirmation_key = uuid.uuid4().hex
            instance.save()

            # Send confirmation email
            send_confirmation_email(self.request, instance)
            return HttpResponseRedirect(self.get_success_url())

        except get_user_model().DoesNotExist:
            return render(self.request, self.template_name, {"form": form})


@DeprecationWarning
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


class RegisterActivateView(View):

    def get(self, request, *args, **kwargs):
        try:
            key = kwargs.get("key")
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


@DeprecationWarning
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

    if request.user.is_authenticated() and request.user.is_partner:
        return HttpResponseRedirect(reverse('publisher-tools'))

    return HttpResponseRedirect(_get_next(request))


def facebook_redirect_login(request):
    log.info(u"Received facebook login request, code received [{code}]".format(code=request.GET.get('code', None)))
    if request.GET.get('code'):
        facebook_token_uri = 'https://graph.facebook.com/oauth/access_token?client_id={app_id}&redirect_uri={redirect_uri}&client_secret={app_secret}&code={code_parameter}'
        request_url = facebook_token_uri.format(app_id=settings.FACEBOOK_APP_ID,
                                                          redirect_uri=request.build_absolute_uri(reverse('auth_facebook_login')),
                                                          app_secret=settings.FACEBOOK_SECRET_KEY,
                                                          code_parameter=request.GET.get('code'))
        log.info(u"Code exists, sending request to {}".format(request_url))
        response = requests.get(request_url)
        log.info(u"Responsecode: {}".format(response.status_code))
        if response.status_code == 200:
            query_dict = urlparse.parse_qs(response.text)
            access_token = query_dict.get('access_token')[0]

            facebook_debug_token_uri = 'https://graph.facebook.com/debug_token?input_token={access_token}&access_token={app_access_token}'
            request_url = facebook_debug_token_uri.format(access_token=access_token,
                                                                    app_access_token=settings.FACEBOOK_APP_ACCESS_TOKEN)
            log.info(u"Facebook debug token request: {}".format(request_url))
            response = requests.get(request_url)
            log.info(u"Responsecode: {}".format(response.status_code))
            if response.status_code == 200:
                response_json = response.json()
                log.info(u"Debug token request ok, facebook authenticating user!")
                for key in response_json.keys():
                    log.info("{}: {}".format(key, response_json.get(key, None)))
                user = auth.authenticate(fb_uid=response_json['data']['user_id'], fb_graphtoken=access_token, request=request)
                if user and user.is_active:
                    log.info(u"Authenticated user is {first_name} {last_name}.".format(first_name=user.first_name, last_name=user.last_name))
                    auth.login(request, user)
                    reset_facebook_user(request)
                    log.info(u"Request is Ajax: {}, redirect to {}".format(request.is_ajax(), _get_next(request)))
                    return _login_flow(request, user)
            else:
                log.info(u"Responsecode FAIL for debug_token url, just redirecting to front page: {}".format(response.status_code))
        else:
            log.info(u"Responsecode FAIL just redirecting to front page: {}".format(response.status_code))
    elif request.GET.get('error_reason'):
        log.info(u"Failed to login user to facebook, reason: {}".format(request.GET.get('error_reason')))
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
                return JSONResponse({'uid': request.user.pk, 'next': _get_next(request)})

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

@login_required
def notifications(request):
    return render(request, 'profile/notifications_list.html')

@csrf_protect
def password_reset(request, **kwargs):
    from django.contrib.auth.views import password_reset as orig_password_reset

    if request.method == "POST":
        email = request.POST.get('email', None)

        try:
            user = get_user_model().objects.get(email=email, is_active=False)
            send_confirmation_email(request, user)
            return HttpResponseRedirect(reverse('auth_register_complete'))
        except get_user_model().DoesNotExist:
            pass

    return orig_password_reset(request, **kwargs)