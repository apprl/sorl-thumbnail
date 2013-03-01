# -*- coding: utf-8 -*-
from django.forms import ModelForm, EmailField, BooleanField, CharField
from django.forms.widgets import RadioSelect, FileInput, Textarea
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from profile.models import ApparelProfile, PaymentDetail


class ProfileImageForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('image',)
        widgets = {'image': FileInput}


class ProfileAboutForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('about',)
        widgets = {'about': Textarea}


class BioForm(ModelForm):
    email = EmailField(label=_('Your e-mail address'))
    about = CharField(widget=Textarea, label=_('Write something about yourself, include links to your blog or website'))

    def __init__(self, *args, **kwargs):
        super(BioForm, self).__init__(*args, **kwargs)

        self.fields['email'].initial = self.instance.user.email

    def save(self, *args, **kwargs):
        super(BioForm, self).save(*args, **kwargs)

        self.instance.user.email = self.cleaned_data.get('email')
        self.instance.user.save()

    class Meta:
        model = ApparelProfile
        fields = ('email', 'about')


class EmailForm(ModelForm):
    email = EmailField(label=_('New e-mail address'))

    class Meta:
        model = get_user_model()
        fields = ('email',)


class NotificationForm(ModelForm):
    class Meta:
        model = ApparelProfile
        fields = ('comment_product_wardrobe', 'comment_product_comment', 'comment_look_created', 'comment_look_comment', 'like_look_created', 'follow_user', 'facebook_friends')
        widgets = {
            'comment_product_wardrobe': RadioSelect,
            'comment_product_comment': RadioSelect,
            'comment_look_created': RadioSelect,
            'comment_look_comment': RadioSelect,
            'like_look_created': RadioSelect,
            'follow_user': RadioSelect,
            'facebook_friends': RadioSelect,
        }


class NewsletterForm(ModelForm):
    newsletter = BooleanField(required=False, help_text=_(u'I\'d like to receive e-mails with trending products, looks and other inspiration.'))
    discount_notification = BooleanField(required=False, help_text=_(u'I want to receive sale alerts on items that I ♥.'))

    class Meta:
        model = ApparelProfile
        fields = ('discount_notification', 'newsletter')


class FacebookSettingsForm(ModelForm):
    fb_share_like_product = BooleanField(required=False, help_text=_(u'When you ♥ a product'))
    fb_share_like_look = BooleanField(required=False, help_text=_(u'When you ♥ a look'))
    fb_share_create_look = BooleanField(required=False, help_text=_(u'When you follow someone'))
    fb_share_follow_profile = BooleanField(required=False, help_text=_(u'When you create a look'))

    class Meta:
        model = ApparelProfile
        fields = ('fb_share_like_product', 'fb_share_like_look', 'fb_share_follow_profile', 'fb_share_create_look')


class PartnerPaymentDetailForm(ModelForm):
    name = CharField(label=_('Name'))
    orgnr = CharField(label=_('Personal/organization number'))
    clearingnr = CharField(label=_('Bank clearing number'))
    banknr = CharField(label=_('Bank account number'))

    class Meta:
        model = PaymentDetail
        fields = ('company', 'name', 'orgnr', 'clearingnr', 'banknr', 'address', 'postal_code', 'city')
        widgets = {
            'company': RadioSelect
        }

class PartnerSettingsForm(ModelForm):
    blog_url = CharField(label=_('http://'), required=False)

    class Meta:
        model = ApparelProfile
        fields = ('blog_url',)
