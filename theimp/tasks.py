import datetime

from django.conf import settings
from django.db.models import get_model
from django.utils import timezone

from celery.task import periodic_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from hotqueue import HotQueue


logger = get_task_logger(__name__)


@periodic_task(name='theimp.tasks.update_old', run_every=crontab(minute=30, hour=5), max_retries=5, ignore_result=True)
def update_old():
    """
    Scraped products that have not been updated in 72 hours should be added to
    the site queue as not validated.
    """
    Product = get_model('theimp', 'Product')
    site_queue = HotQueue(settings.THEIMP_QUEUE_SITE,
                          host=settings.THEIMP_REDIS_HOST,
                          port=settings.THEIMP_REDIS_PORT,
                          db=settings.THEIMP_REDIS_DB)

    count = 0
    modified_delta = timezone.now() - datetime.timedelta(hours=72)
    for product_id in Product.objects.filter(modified__lte=modified_delta) \
                                     .values_list('id', flat=True):
        site_queue.put((product_id, False))
        count = count + 1

    logger.info('Found %s old products' % (count,))
