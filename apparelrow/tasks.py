from datetime import timedelta

from django.core.management import call_command
from django.db.models.loading import get_model
from celery.task import task, PeriodicTask
from celery.schedules import crontab

from apparel.search import product_save

# Keep this because it is used in a migration
@task(name='apparelrow.tasks.search_index_update_task', max_retries=1, ignore_result=True)
def search_index_update_task(app_name, model_name, pk, **kwargs):
    logger = search_index_update_task.get_logger(**kwargs)
    try:
        model_class = get_model(app_name, model_name)
        instance = model_class.objects.get(pk=pk)
        product_save(instance)
    except Exception, exc:
        logger.error(exc)
        search_index_update_task.retry(exc=exc)

class ProcessPopularityTask(PeriodicTask):
    run_every = crontab(hour=4, minute=15)
    ignore_result = True

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info('update popularity for products')
        call_command('popularity')
