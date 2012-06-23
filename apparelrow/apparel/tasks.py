import logging
import datetime

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from mailsnake import MailSnake
from mailsnake.exceptions import MailSnakeException
from celery.task import task, periodic_task
from celery.schedules import crontab
from actstream.models import Action

from apparel.models import Brand, Product

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
