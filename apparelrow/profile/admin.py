from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from apparelrow.profile.models import Follow
from apparelrow.profile.models import NotificationCache, NotificationEvent
from apparelrow.profile.models import PaymentDetail


#
# Custom User Model Admin
#

class CustomUserChangeForm(UserChangeForm):
    """
    Extend UserChangeForm to use our custom user model.
    """
    class Meta:
        model = get_user_model()

    def clean_facebook_user_id(self):
        """
        Return None instead of empty string.
        """
        return self.cleaned_data.get('facebook_user_id') or None

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            return email

        try:
            if self.instance and hasattr(self.instance, 'pk'):
                get_user_model()._default_manager.exclude(pk=self.instance.pk).get(email=email)
            else:
                get_user_model()._default_manager.get(email=email)
        except get_user_model().DoesNotExist:
            return email
        except get_user_model().MultipleObjectsReturned:
            pass

        raise forms.ValidationError(_('A user with that e-mail already exists.'))


class CustomUserCreationForm(UserCreationForm):
    """
    Extend UserCreationForm to use our custom user model.
    """
    class Meta:
        model = get_user_model()

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return username
        except get_user_model().MultipleObjectsReturned:
            pass

        raise forms.ValidationError(self.error_messages['duplicate_username'])


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    change_form_template = 'profile/admin_change_form.html'

    list_display = ('username', 'slug', 'name', 'first_name', 'last_name', 'email', 'is_brand', 'is_hidden', 'date_joined')
    list_filter = ('is_brand', 'is_partner', 'is_active', 'is_staff', 'is_superuser', 'is_hidden')
    raw_id_fields = ('brand', 'referral_partner_parent','owner_network')
    search_fields = ('username', 'name', 'slug', 'first_name', 'last_name')
    readonly_fields = ('referral_partner_code', 'referral_partner_url')
    fieldsets = (
        (None, {'fields': [('username', 'password'),]}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'name',
                                         'email', 'image', 'about', 'gender',
                                         'language','location', 'blog_url', 'manual_about_en', 'manual_about_sv', 'is_hidden',
                                         )}),
        (_('Facebook'), {'fields': ('facebook_user_id',
                                    'facebook_access_token',
                                    'facebook_access_token_expire')}),
        (_('Brand'), {'fields': ('is_brand', 'brand')}),
        (_('Publisher'), {'fields': ('is_partner',
                                     'partner_group',
                                     'owner_network',
                                     'is_subscriber',
                                     'owner_network_cut',
                                     'referral_partner',
                                     'referral_partner_code',
                                     'referral_partner_url',
                                     'referral_partner_parent',
                                     'referral_partner_parent_date')}),
        (_('Extra'), {'fields': ('slug', 'login_flow', 'popularity', 'popularity_men', 'followers_count')}),
        (_('Settings'), {'fields': ('newsletter', 'discount_notification',
                                    'fb_share_like_product', 'fb_share_like_look',
                                    'fb_share_follow_profile', 'fb_share_create_look',
                                    'comment_product_wardrobe',
                                    'comment_product_comment',
                                    'comment_look_created',
                                    'comment_look_comment',
                                    'like_look_created',
                                    'follow_user',
                                    'facebook_friends')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions'),
                            'classes': ('collapse',)}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        # if obj and obj.is_referral_parent_valid():
        #    readonly_fields.extend(['referral_partner'])
        return readonly_fields

    def referral_partner_url(self, obj):
        return obj.get_referral_url()
    referral_partner_url.allow_tags = False
    referral_partner_url.short_description = 'Referral URL'

admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.unregister(Group)


#
# Rest
#

admin.site.register(NotificationCache)

class NotificationEventAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)
    list_display = ('owner', 'actor', 'type', 'product', 'look', 'seen')

admin.site.register(NotificationEvent, NotificationEventAdmin)

class FollowAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    raw_id_fields = ['user', 'user_follow']
    list_display = ('user', 'user_follow', 'created', 'modified', 'active')
    list_filter = ('active',)

admin.site.register(Follow, FollowAdmin)


class PaymentDetailAdmin(admin.ModelAdmin):
    list_display = ('custom_user', 'name', 'company', 'orgnr', 'bank_name', 'banknr', 'clearingnr')
    raw_id_fields = ('user',)

    def custom_user(self, obj):
        return u'%s' % (obj.user.display_name,)

admin.site.register(PaymentDetail, PaymentDetailAdmin)
