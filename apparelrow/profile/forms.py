from django.forms import ModelForm, EmailField, BooleanField
from django.forms.widgets import RadioSelect, FileInput
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from profile.models import ApparelProfile

class ProfileImageForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('image',)
        widgets = {'image': FileInput}

class EmailForm(ModelForm):
    email = EmailField(label=_('New e-mail address'))

    class Meta:
        model = User
        fields = ('email',)

class NotificationForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('comment_product_wardrobe', 'comment_product_comment', 'comment_look_created', 'comment_look_comment', 'like_look_created', 'follow_user')
        widgets = {
            'comment_product_wardrobe': RadioSelect,
            'comment_product_comment': RadioSelect,
            'comment_look_created': RadioSelect,
            'comment_look_comment': RadioSelect,
            'like_look_created': RadioSelect,
            'follow_user': RadioSelect
        }


class NewsletterForm(ModelForm):
    newsletter = BooleanField(required=False, help_text=_('I\'d like to receive e-mails with trending products, looks and other inspiration.'))

    class Meta:
        model = ApparelProfile
        fields = ('newsletter',)

class FacebookSettingsForm(ModelForm):
    fb_share_like_product = BooleanField(required=False, help_text=_('Share product likes on facebook'))
    fb_share_like_look = BooleanField(required=False, help_text=_('Share look likes on facebook'))
    fb_share_create_look = BooleanField(required=False, help_text=_('Share look creations on facebook'))
    fb_share_follow_profile = BooleanField(required=False, help_text=_('Share follows on facebook'))

    class Meta:
        model = ApparelProfile
        fields = ('fb_share_like_product', 'fb_share_like_look', 'fb_share_follow_profile', 'fb_share_create_look')
