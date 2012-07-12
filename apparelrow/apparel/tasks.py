import logging
import datetime

from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException
from celery.task import task, periodic_task, PeriodicTask
from celery.schedules import crontab
from actstream.models import Action
import requests

from apparel.models import Brand, Product, VendorBrand, VendorCategory, FacebookAction

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


@task(name='apparel.facebook_push_graph', max_retries=5, ignore_result=True)
def facebook_push_graph(user_id, access_token, action, object_type, object_id, object_url):
    url = 'https://graph.facebook.com/me/%s:%s/?access_token=%s' % (settings.FACEBOOK_OG_TYPE, action, access_token)

    response = requests.post(url, data={object_type: object_url})
    data = response.json

    logger.info(data)

    if 'id' in data:
        FacebookAction.objects.get_or_create(user_id=user_id, action=action, action_id=data['id'], object_type=object_type, object_id=object_id)
    elif 'error' in data and data['error']['code'] == 2:
        facebook_push_graph.retry(countdown=15)


@task(name='apparel.facebook_pull_graph', max_retries=1, ignore_result=True)
def facebook_pull_graph(user_id, access_token, action, object_type, object_id, object_url):
    try:
        facebook_action = FacebookAction.objects.get(user_id=user_id, action=action, object_type=object_type, object_id=object_id)
        url = 'https://graph.facebook.com/%s/?access_token=%s' % (facebook_action.action_id, access_token)
        response = requests.delete(url)
        facebook_action.delete()

        logger.info(response.json)
    except FacebookAction.DoesNotExist:
        logger.warning('Could not find a matching facebook action id for uid=%s type=%s id=%s' % (user_id, object_type, object_id))

@periodic_task(name='apparel.brand_updates', run_every=crontab(minute=13), max_retries=1, ignore_result=True)
def brand_updates():
    """
    A task to check for brand updates.

    Every hour the task will iterate through all brands and check if any new
    products are added. If there are new products the task will create a new
    actstream action.
    """
    for brand in Brand.objects.iterator():
        first_product = None
        count_product = 0
        last_update = brand.last_update
        if last_update is None:
            last_update = datetime.datetime.now() - datetime.timedelta(days=365)
        for product in Product.valid_objects.filter(date_added__gt=last_update, manufacturer=brand).iterator():
            if first_product is None:
                first_product = product
            count_product += 1

        if first_product is not None:
            action_object = Action.objects.get_or_create(actor_content_type=ContentType.objects.get_for_model(brand.profile.user),
                                                         actor_object_id=brand.profile.user.pk,
                                                         verb='added_products',
                                                         description=count_product,
                                                         action_object_content_type=ContentType.objects.get_for_model(first_product),
                                                         action_object_object_id=first_product.pk)

        brand.last_update = datetime.datetime.now()
        brand.save()


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
