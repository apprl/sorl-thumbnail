from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from apparelrow.profile.models import Follow
from apparelrow.profile.models import NotificationCache
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
        raise forms.ValidationError(self.error_messages['duplicate_username'])


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_filter = ('is_brand', 'is_partner', 'is_active', 'is_staff', 'is_superuser')
    raw_id_fields = ('brand',)
    fieldsets = (
        (None, {'fields': [('username', 'password'),]}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'name',
                                         'email', 'image', 'about', 'gender',
                                         'language', 'blog_url')}),
        (_('Facebook'), {'fields': ('facebook_user_id',
                                    'facebook_access_token',
                                    'facebook_access_token_expire')}),
        (_('Brand'), {'fields': ('is_brand', 'brand')}),
        (_('Partner'), {'fields': ('is_partner', 'partner_group')}),
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

admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.unregister(Group)


#
# Rest
#

admin.site.register(NotificationCache)


class FollowAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified')
    raw_id_fields = ['user', 'user_follow']
    list_display = ('user', 'user_follow', 'created', 'modified', 'active')
    list_filter = ('active',)

admin.site.register(Follow, FollowAdmin)


class PaymentDetailAdmin(admin.ModelAdmin):
    list_display = ('custom_user', 'name', 'company', 'orgnr', 'clearingnr', 'banknr')
    raw_id_fields = ('user',)

    def custom_user(self, obj):
        return u'%s' % (obj.user.display_name,)

admin.site.register(PaymentDetail, PaymentDetailAdmin)
