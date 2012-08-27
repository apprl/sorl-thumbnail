import logging
import datetime

from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException
from celery.task import task, periodic_task, PeriodicTask
from celery.schedules import crontab
import requests

from apparel.models import Product, VendorBrand, VendorCategory, FacebookAction

logger = logging.getLogger('apparel.tasks')

@task(name='apparel.email.mailchimp_subscribe', max_retries=5, ignore_result=True)
def mailchimp_subscribe(user):
    try:
        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listSubscribe(id=settings.MAILCHIMP_WEEKLY_LIST,
                                email_address=user.email,
                                merge_vars={'EMAIL': user.email, 'FNAME': user.first_name, 'LNAME': user.last_name, 'GENDER': user.get_profile().gender},
                                double_optin=False,
                                update_existing=True,
                                send_welcome=False)
    except MailSnakeException, e:
        logger.error('Could not subscribe user to mailchimp: %s' % (e,))

@task(name='apparel.email.mailchimp_unsubscribe', max_retries=5, ignore_result=True)
def mailchimp_unsubscribe(user, delete=False):
    try:
        mailchimp = MailSnake(settings.MAILCHIMP_API_KEY)
        mailchimp.listUnsubscribe(id=settings.MAILCHIMP_WEEKLY_LIST,
                                  email_address=user.email,
                                  delete_member=delete,
                                  send_goodbye=False,
                                  send_notify=False)
    except MailSnakeException, e:
        logger.error('Could not unsubscribe user from mailchimp: %s' % (e,))


ACTION_TRANSLATION = {'like': 'og.likes', 'follow': 'og.follows', 'create': '%s:create' % (settings.FACEBOOK_OG_TYPE,)}

@task(name='apparel.facebook_push_graph', max_retries=5, ignore_result=True)
def facebook_push_graph(user_id, access_token, action, object_type, object_url):
    url = 'https://graph.facebook.com/me/%s' % (ACTION_TRANSLATION[action],)
    response = requests.post(url, data={object_type: object_url, 'access_token': access_token})
    data = response.json

    logger.info(data)

    if 'id' in data:
        FacebookAction.objects.get_or_create(user_id=user_id, action=action, action_id=data['id'], object_type=object_type, object_url=object_url)
    elif 'error' in data and data['error']['code'] == 2:
        facebook_push_graph.retry(countdown=15)

@task(name='apparel.facebook_pull_graph', max_retries=1, ignore_result=True)
def facebook_pull_graph(user_id, access_token, action, object_type, object_url):
    try:
        facebook_action = FacebookAction.objects.get(user_id=user_id, action=action, object_type=object_type, object_url=object_url)
        facebook_action.delete()
        url = 'https://graph.facebook.com/%s' % (facebook_action.action_id,)
        response = requests.delete(url, data={'access_token': access_token})
        logger.info(response.json)
    except FacebookAction.DoesNotExist:
        logger.warning('No facebook action_id found for uid=%s action=%s type=%s' % (user_id, action, object_type))


# XXX: offline
#@periodic_task(name='apparel.tasks.update_vendor_data', run_every=crontab(minute='0,15,30,45'), max_retries=1, ignore_result=True)
def update_vendor_data():
    """
    Updates vendor data every half hour.
    """
    timestamp = datetime.datetime.now() - datetime.timedelta(minutes=20)
    for vendor_brand in VendorBrand.objects.filter(modified__gt=timestamp).iterator():
        if vendor_brand.brand:
            for product in Product.objects.filter(vendorproduct__vendor_brand_id=vendor_brand.id).iterator():
                if product.manufacturer_id != vendor_brand.brand_id:
                    product.manufacturer_id = vendor_brand.brand_id
                    product.save()
        else:
            queryset = Product.objects.filter(vendorproduct__vendor_brand_id=vendor_brand.id, manufacturer__isnull=False)
            for product in queryset:
                product.manufacturer_id = None
                product.save()

    for vendor_category in VendorCategory.objects.filter(modified__gt=timestamp).iterator():
        if vendor_category.category:
            queryset = Product.objects.filter(vendorproduct__vendor_category=vendor_category)
            for product in queryset:
                product.category = self.category
                product.published = True
                product.save()
        else:
            queryset = Product.objects.filter(vendorproduct__vendor_category=vendor_category, category__isnull=False)
            for product in queryset:
                product.category = None
                product.save()


class ProcessPopularityTask(PeriodicTask):
    run_every = crontab(hour=4, minute=15)
    ignore_result = True

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info('update popularity for products')
        call_command('popularity')

class ProcessLookPopularity(PeriodicTask):
    run_every = crontab(minute='*/30')
    ignore_result = True

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info('update popularity for looks')
        call_command('look_popularity')
