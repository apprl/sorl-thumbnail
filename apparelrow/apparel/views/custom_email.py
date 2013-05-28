# -*- coding: utf-8 -*-
import logging
import datetime
import itertools

from django import forms
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound
from django.db.models import Q, Count
from django.db.models.signals import pre_save, pre_delete
from django.db.models.loading import get_model
from django.dispatch import receiver
from django.template import RequestContext, loader
from django.utils.translation import activate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.views.decorators.csrf import csrf_exempt
from django.contrib.staticfiles.storage import staticfiles_storage

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from sorl.thumbnail import get_thumbnail

from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException

from apparelrow.apparel.email import update_subscribers

logger = logging.getLogger('apparelrow.apparel.views.custom_email')


MAILCHIMP_TEMPLATE_NAME = 'Custom Campaign Template'


class MultiURLField(forms.CharField):
    def to_python(self, value):
        if not value:
            return []
        return [x for x in value.splitlines() if x.strip()]

    def validate(self, value):
        super(MultiURLField, self).validate(value)

        #for email in value:
            #validate_email(email)


class CustomEmailForm(forms.Form):
    gender = forms.TypedChoiceField(
            widget=forms.RadioSelect,
            required=True,
            choices=(('M', 'Men'), ('W', 'Women'), ('A', 'Both')),
            initial='W')

    subject = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            max_length=128,
            required=False,
            help_text='If field is empty a generated subject will be used based on products')

    preview = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            max_length=160,
            required=True,
            initial='See this week\'s trending items, looks, members & brands!')

    product_title = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            max_length=100,
            initial='The items',
            required=False)

    product_urls = MultiURLField(
            widget=forms.Textarea(attrs={'class': 'input-xxlarge'}),
            required=False,
            help_text='Enter 1 product URL per row')

    look_title = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            max_length=100,
            initial='The looks',
            required=False)

    look_urls = MultiURLField(
            widget=forms.Textarea(attrs={'class': 'input-xxlarge'}),
            required=False,
            help_text='Enter 1 look URL per row')

    user_title = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            max_length=100,
            initial='Selected by',
            required=False)

    user_urls = MultiURLField(
            widget=forms.Textarea(attrs={'class': 'input-xxlarge'}),
            required=False,
            help_text='Enter 1 profile URL per row')

    tracking = forms.BooleanField(help_text='Product link will use ?sid=123 if a user is selected', required=False)

    create = forms.BooleanField(help_text='Create campaign and upload it to mailchimp', required=False)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        self.helper.add_input(Submit('submit', 'Submit'))
        super(CustomEmailForm, self).__init__(*args, **kwargs)

    def _clean_helper(self, field):
        data = self.cleaned_data[field]
        new_data = []
        for index, url in enumerate(data):
            validated_data = validate_url(url)
            if not validated_data:
                raise forms.ValidationError('Invalid url on line %s' % (index + 1,))

            new_data.append(validated_data)

        return new_data

    def clean(self):
        cleaned_data = super(CustomEmailForm, self).clean()

        subject = cleaned_data.get('subject')
        products = cleaned_data.get('product_urls')

        if not subject and not products:
            raise forms.ValidationError('Requires a subject if no product urls is entered')

        return cleaned_data

    def clean_product_urls(self):
        return self._clean_helper('product_urls')

    def clean_look_urls(self):
        return self._clean_helper('look_urls')

    def clean_user_urls(self):
        return self._clean_helper('user_urls')


def validate_url(url):
    """
    Validate url and turn it into a model object.
    """
    index = None
    url_parts = url.split('/')
    if 'products' in url_parts:
        index = url_parts.index('products') + 1
        model = get_model('apparel', 'Product')
    elif 'looks' in url_parts:
        index = url_parts.index('looks') + 1
        model = get_model('apparel', 'Look')
    elif 'profile' in url_parts:
        index = url_parts.index('profile') + 1
        model = get_user_model()

    try:
        slug = url_parts[index]
    except (TypeError, IndexError) as e:
        return None

    try:
        return model.objects.get(slug=slug)
    except model.DoesNotExist as e:
        return None


@login_required
def admin(request):
    """
    Admin form for creation of custom email.
    """
    if not request.user.is_superuser:
        return HttpResponseNotFound()

    if request.method == 'POST':
        form = CustomEmailForm(request.POST)
        if form.is_valid():
            gender = form.cleaned_data['gender']
            subject = form.cleaned_data['subject']
            preview = form.cleaned_data['preview']
            product_title = form.cleaned_data['product_title']
            products = form.cleaned_data['product_urls']
            look_title = form.cleaned_data['look_title']
            looks = form.cleaned_data['look_urls']
            user_title = form.cleaned_data['user_title']
            users = form.cleaned_data['user_urls']


            base_url = request.build_absolute_uri('/')[:-1]

            for user in users:
                avatar = user.avatar_medium
                if not avatar.startswith('http'):
                    avatar = ''.join([base_url, avatar])
                user.mail_image = avatar

            if not subject:
                product_names = list(set([product.manufacturer.name for product in products]))
                product_names = product_names[:min(len(product_names), 5)]
                subject = u'%s and more trending this week!' % (', '.join(product_names),)

            # Templates
            template_content = {}

            # Product template
            if products:
                sid = None
                if users and form.cleaned_data['tracking']:
                    sid = users[0].pk
                args = [iter(products)] * 3
                products = itertools.izip_longest(*args, fillvalue=None)
                template_product = loader.render_to_string('email/custom/product.html', {
                        'title': product_title,
                        'products': products,
                        'sid': sid,
                    })
                template_content['html_product_content'] = template_product

            # Look template
            if looks:
                template_look = loader.render_to_string('email/custom/look.html', {
                        'title': look_title,
                        'looks': looks,
                    })
                template_content['html_look_content'] = template_look

            # User template
            if users:
                template_user = loader.render_to_string('email/custom/user.html', {
                        'title': user_title,
                        'users': users,
                    })
                template_content['html_user_content'] = template_user

            # Text template
            template_content['text'] = loader.render_to_string('email/custom.txt', {'preview': preview})

            # Base template
            template = loader.render_to_string('email/custom/template.html', {
                    'base_url': base_url,
                    'preview': preview,
                    'products': products,
                    'looks': looks,
                    'users': users,
                })

            # If create is set, create mailchimp campaign
            if form.cleaned_data.get('create'):
                mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)

                try:
                    update_subscribers(mailchimp)
                except MailSnakeException, e:
                    return HttpResponse('Error: could not update subscribers list: %s' % (str(e),))

                # Upload template to Mailchimp
                mailchimp_templates = mailchimp.templates()
                template_lookup = dict((x['name'], x['id']) for x in mailchimp_templates['user'])
                if MAILCHIMP_TEMPLATE_NAME in template_lookup:
                    mailchimp.templateUpdate(id=template_lookup[MAILCHIMP_TEMPLATE_NAME],
                                             values={'html': template})
                else:
                    template_id = mailchimp.templateAdd(name=MAILCHIMP_TEMPLATE_NAME, html=template)
                    template_lookup[MAILCHIMP_TEMPLATE_NAME] = template_id

                # Mailchimp campaign setting
                campaign_name = 'Custom %s - %s' % (datetime.date.today(), gender)
                options = {
                        'list_id': settings.MAILCHIMP_NEWSLETTER_LIST,
                        'template_id': template_lookup[MAILCHIMP_TEMPLATE_NAME],
                        'subject': subject,
                        'from_email': 'postman@apprl.com',
                        'from_name': 'Apprl',
                        'to_name': '*|FNAME|*',
                        'inline_css': True,
                        'generate_text': True,
                        'title': campaign_name
                    }

                segment_options = None
                if gender != 'A':
                    segment_options = {'match': 'all',
                                       'conditions': [{'field': 'GENDER',
                                                       'op': 'eq',
                                                       'value': gender}]}

                try:
                    campaign_id = mailchimp.campaignCreate(type='regular', options=options, content=template_content, segment_opts=segment_options)
                except MailSnakeException, e:
                    return HttpResponse('Error [%s]: could not create campaign: %s' % (gender, e))

                return HttpResponse('Created campaign %s with ID %s' % (campaign_name, campaign_id))


            return render(request, 'email/custom/template.html', {
                    'base_url': base_url,
                    'preview': preview,
                    'products': products,
                    'looks': looks,
                    'users': users,
                    'product_content': template_content.get('html_product_content', ''),
                    'look_content': template_content.get('html_look_content', ''),
                    'user_content': template_content.get('html_user_content', ''),
                })
    else:
        form = CustomEmailForm()

    return render(request, 'apparel/custom_email.html', {'form': form})
