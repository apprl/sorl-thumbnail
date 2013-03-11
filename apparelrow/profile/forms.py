# -*- coding: utf-8 -*-
import random
import string

from django.forms import Form, ModelForm, EmailField, BooleanField, CharField, ChoiceField, ValidationError
from django.forms.widgets import RadioSelect, FileInput, Textarea
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from profile.models import PaymentDetail


class ProfileImageForm(ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('image',)
        widgets = {'image': FileInput}


class ProfileAboutForm(ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('about',)
        widgets = {'about': Textarea}


class BioForm(ModelForm):
    name = CharField(required=True, label=_('Your name'))
    gender = ChoiceField(required=True, choices=(('M', _('Man')), ('W', _('Woman'))), widget=RadioSelect, label='')
    email = EmailField(required=True, label=_('Your e-mail address'))
    about = CharField(required=False, widget=Textarea, label=_('Write something about yourself, include links to your blog or website'))

    def __init__(self, *args, **kwargs):
        super(BioForm, self).__init__(*args, **kwargs)

        self.fields['email'].initial = self.instance.email

        if self.instance.facebook_user_id and self.instance.gender:
            self.fields['gender'].widget = self.fields['gender'].hidden_widget()

        if self.instance.email:
            self.fields['email'].widget = self.fields['email'].hidden_widget()

    def save(self, *args, **kwargs):
        super(BioForm, self).save(*args, **kwargs)

        self.instance.email = self.cleaned_data.get('email')
        self.instance.save()

    class Meta:
        model = get_user_model()
        fields = ('name', 'gender', 'email', 'about')


class EmailForm(ModelForm):
    email = EmailField(label=_('New e-mail address'))

    class Meta:
        model = get_user_model()
        fields = ('email',)


class NotificationForm(ModelForm):
    class Meta:
        model = get_user_model()
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
        model = get_user_model()
        fields = ('discount_notification', 'newsletter')


class FacebookSettingsForm(ModelForm):
    fb_share_like_product = BooleanField(required=False, help_text=_(u'When you ♥ a product'))
    fb_share_like_look = BooleanField(required=False, help_text=_(u'When you ♥ a look'))
    fb_share_create_look = BooleanField(required=False, help_text=_(u'When you follow someone'))
    fb_share_follow_profile = BooleanField(required=False, help_text=_(u'When you create a look'))

    class Meta:
        model = get_user_model()
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
        model = get_user_model()
        fields = ('blog_url',)


class RegisterForm(UserCreationForm):
    email = EmailField(label=_('E-mail address'), required=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email')

    def clean_username(self):
        # Since get_user_model().username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data['username']
        try:
            get_user_model()._default_manager.get(username=username)
        except get_user_model().DoesNotExist:
            return username
        raise ValidationError(self.error_messages['duplicate_username'])

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            get_user_model()._default_manager.get(email=email)
        except get_user_model().DoesNotExist:
            return email
        raise ValidationError(_('A user with that e-mail already exists.'))

class RegisterCompleteForm(Form):
    email = EmailField(label=_('E-mail address'), required=True)

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            get_user_model()._default_manager.get(email=email, is_active=False)
        except get_user_model().DoesNotExist:
            raise ValidationError(_('E-mail does not exist or account is already confirmed.'))

        return email
