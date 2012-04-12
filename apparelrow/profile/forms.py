from django.forms import ModelForm, EmailField, BooleanField
from django.forms.widgets import RadioSelect
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from profile.models import ApparelProfile

class ProfileImageForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('image',)

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
