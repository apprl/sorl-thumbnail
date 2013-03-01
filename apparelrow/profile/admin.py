from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group

from profile.models import ApparelProfile
from profile.models import Follow
from profile.models import NotificationCache
from profile.models import PaymentDetail


#
# Custom User Model Admin
#

class CustomUserChangeForm(UserChangeForm):
    """
    Extend UserChangeForm to use our custom user model.
    """
    class Meta:
        model = get_user_model()


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

admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.unregister(Group)


#
# Rest
#

class ApparelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'brand', 'slug', 'is_brand', 'language', 'followers_count', 'popularity')
    list_filter = ('is_brand', 'is_partner')
    search_fields = ('name',)
    raw_id_fields = ('user', 'brand')

admin.site.register(ApparelProfile, ApparelProfileAdmin)


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
        return u'%s' % (obj.user.get_profile().display_name,)

admin.site.register(PaymentDetail, PaymentDetailAdmin)
