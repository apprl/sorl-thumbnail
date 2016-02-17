# -*- coding: utf-8 -*-
import random
import string

from django import forms
from django.db.models.loading import get_model
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

#
# Custom widgets for rendering Radio buttons and Checkboxes
#


class CustomRadioSelect(forms.RadioSelect):
    """
    Widget for Radio Buttons select with customized output.
    """
    class CustomRadioInput(forms.widgets.RadioInput):

        def __unicode__(self):
            return self.render()

        def render(self, name=None, value=None, attrs=None, choices=()):
            name = name or self.name
            value = value or self.value
            attrs = attrs or self.attrs
            if 'id' in self.attrs:
                label_for = " for='%s_%s'" % (self.attrs['id'], self.index)
            else:
                label_for = ''
            choice_label = conditional_escape(force_unicode(self.choice_label))
            return mark_safe(u'<label%s> %s <span></span> %s</label>' % (label_for, self.tag(), choice_label))

    class CustomRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
        def __iter__(self):
            for i, choice in enumerate(self.choices):
                yield CustomRadioSelect.CustomRadioInput(self.name, self.value,
                                       self.attrs.copy(), choice, i)

        def __getitem__(self, idx):
            choice = self.choices[idx]
            return CustomRadioSelect.CustomRadioInput(self.name, self.value,
                                    self.attrs.copy(), choice, idx)

        def render(self, *args, **kwargs):
            return mark_safe(u'<ul class="form-button-radio">\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>'
                    % force_unicode(w) for w in self]))

    renderer = CustomRadioFieldRenderer


class CustomCheckboxInput(forms.widgets.CheckboxInput):
    """
    Widget for Checkboxes with customized output.
    """
    input_type = 'checkbox'

    def __unicode__(self):
        return self.render()

    def render(self, *args, **kwargs):
        output = super(CustomCheckboxInput, self).render(*args,**kwargs)
        if 'id' in self.attrs:
            label_for = " for='%s_%s'" % (self.attrs['id'], self.index)
        else:
            label_for = ''
        #output = '<label%s>%s <span><i class="fa fa-check"></i></span></label>' % (label_for,output)
        output = '<label{label}>{output}<span><i class="fa fa-check"></i></span></label>'.format(label=label_for, output=output)
        return mark_safe(output)

#
# Forms
#


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('image',)
        widgets = {'image': forms.FileInput}


class ProfileAboutForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('about',)
        widgets = {'about': forms.Textarea}


class BioForm(forms.ModelForm):
    name = forms.CharField(required=True, label=_('Your name'))
    gender = forms.ChoiceField(required=True, choices=(('M', _('Man')), ('W', _('Woman'))), widget=CustomRadioSelect, label='')
    email = forms.EmailField(required=True, label=_('Your e-mail address'))
    about = forms.CharField(required=False, widget=forms.Textarea,
                            label=_('Write something about yourself, include links to your blog or website'))

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


class EmailForm(forms.ModelForm):
    email = forms.EmailField(label=_('New e-mail address'), required=False)

    class Meta:
        model = get_user_model()
        fields = ('email',)


class NotificationForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('like_look_created', 'follow_user', 'facebook_friends', 'summary_mails', 'product_like_summaries', 'look_like_summaries')
        #fields = ('comment_product_wardrobe', 'comment_product_comment', 'comment_look_created', 'comment_look_comment', 'like_look_created', 'follow_user', 'facebook_friends')
        widgets = {
            'comment_product_wardrobe': CustomRadioSelect,
            'comment_product_comment': CustomRadioSelect,
            'comment_look_created': CustomRadioSelect,
            'comment_look_comment': CustomRadioSelect,
            'like_look_created': CustomRadioSelect,
            'follow_user': CustomRadioSelect,
            'facebook_friends': CustomRadioSelect,
            'summary_mails': CustomRadioSelect,
            'product_like_summaries': CustomRadioSelect,
            'look_like_summaries': CustomRadioSelect,
            #'earning_summaries': CustomRadioSelect,
            'friend_summaries': CustomRadioSelect,
            'brand_summaries': CustomRadioSelect,
            'follow_recommendations': CustomRadioSelect,
        }

    def __init__(self, *args, **kwargs):
        from django.forms.widgets import HiddenInput
        is_publisher = kwargs.pop('is_publisher',None)
        super(NotificationForm, self).__init__(*args, **kwargs)
        #if not is_publisher:
        #    self.fields['earning_summaries'].widget = HiddenInput()


class NewsletterForm(forms.ModelForm):
    newsletter = forms.BooleanField(required=False, help_text=_(u'I\'d like to receive e-mails with trending products, looks and other inspiration.'), widget=CustomCheckboxInput)
    discount_notification = forms.BooleanField(required=False, help_text=_(u'I want to receive sale alerts on items that I ♥.'), widget=CustomCheckboxInput)

    class Meta:
        model = get_user_model()
        fields = ('discount_notification', 'newsletter')


class LocationForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('location',)


class FacebookSettingsForm(forms.ModelForm):
    fb_share_like_product = forms.BooleanField(required=False, help_text=_(u'When you ♥ a product'), widget=CustomCheckboxInput)
    fb_share_like_look = forms.BooleanField(required=False, help_text=_(u'When you ♥ a look'), widget=CustomCheckboxInput)
    fb_share_create_look = forms.BooleanField(required=False, help_text=_(u'When you create a look'), widget=CustomCheckboxInput)
    fb_share_follow_profile = forms.BooleanField(required=False, help_text=_(u'When you follow someone'), widget=CustomCheckboxInput)

    class Meta:
        model = get_user_model()
        fields = ('fb_share_like_product', 'fb_share_like_look', 'fb_share_follow_profile', 'fb_share_create_look')


class PartnerPaymentDetailForm(forms.ModelForm):
    name = forms.CharField(label=_('Name'))
    orgnr = forms.CharField(label=_('Personal / Organization number'))
    clearingnr = forms.CharField(label=_('Bank clearing number'))
    banknr = forms.CharField(label=_('Bank account number'))
    address = forms.CharField(label=_('Address'))
    postal_code = forms.CharField(label=_('Postal code'))
    city = forms.CharField(label=_('City'))
    notes = forms.CharField(label=_('Other notes'), widget=forms.Textarea(attrs={'rows':4, 'cols': 30}), required=False)

    class Meta:
        model = get_model('profile', 'PaymentDetail')
        fields = ('company', 'name', 'orgnr', 'clearingnr', 'banknr', 'address', 'postal_code', 'city', 'notes')
        widgets = {
            'company': forms.RadioSelect # TODO Falta arreglar aca
        }


class PartnerSettingsForm(forms.ModelForm):
    blog_url = forms.CharField(label=_('http://'), required=False)

    class Meta:
        model = get_user_model()
        fields = ('blog_url',)


class RegisterFormSimple(forms.Form):
    email = forms.EmailField(label=_('E-mail address'), required=True, error_messages={'invalid': _('Please enter a valid email address.')})
    password = forms.CharField(label=_('Password'), required=True, widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label=_('First name'), required=True, error_messages={'required': _('At least a first name is required.')})
    last_name = forms.CharField(label=_('Last name'), required=False)
    email = forms.EmailField(label=_('E-mail address'), required=True, error_messages={'invalid': _('Please enter a valid email address.')})
    gender = forms.ChoiceField(required=True, choices=(('M', _('Man')), ('W', _('Woman'))), widget=CustomRadioSelect, label=_('Gender'))
    password1 = forms.CharField(label=_('Password'),
        widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Password confirmation'),
        widget=forms.PasswordInput,
        help_text=_('Enter the same password as above, for verification.'))

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'username', 'email', 'gender')

    def clean_username(self):
        # Since get_user_model().username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data['username']
        try:
            get_user_model()._default_manager.get(username=username)
        except get_user_model().DoesNotExist:
            return username
        except get_user_model().MultipleObjectsReturned:
            pass

        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            get_user_model()._default_manager.get(email=email)
        except get_user_model().DoesNotExist:
            return email
        except get_user_model().MultipleObjectsReturned:
            pass

        raise forms.ValidationError(_('A user with that e-mail already exists.'))

class RegisterCompleteForm(forms.Form):
    email = forms.EmailField(label=_('E-mail address'), required=True)

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            get_user_model()._default_manager.get(email=email, is_active=False)
        except get_user_model().DoesNotExist:
            raise forms.ValidationError(_('E-mail does not exist or account is already confirmed.'))

        return email
