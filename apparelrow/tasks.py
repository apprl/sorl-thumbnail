from datetime import timedelta

from django.core.management import call_command
from django.db.models.loading import get_model
from haystack import site
from celery.task import task, PeriodicTask
from celery.schedules import crontab

from apparelrow.apparel.messaging import process_search_index_updates
from apparelrow.statistics.messaging import process_clicks

@task(name='apparelrow.tasks.search_index_update_task', max_retries=1, ignore_result=True)
def search_index_update_task(app_name, model_name, pk, **kwargs):
    logger = search_index_update_task.get_logger(**kwargs)
    try:
        model_class = get_model(app_name, model_name)
        instance = model_class.objects.get(pk=pk)
        search_index = site.get_index(model_class)
        search_index.update_object(instance)
    except Exception, exc:
        logger.error(exc)
        search_index_update_task.retry(exc=exc)

class ProcessSearchIndexUpdatesTask(PeriodicTask):
    run_every = timedelta(minutes=10)
    ignore_result = True

    def run(self, **kwargs):
        process_search_index_updates()

class ProcessClicksTask(PeriodicTask):
    run_every = timedelta(minutes=15)
    ignore_result = True

    def run(self, **kwargs):
        process_clicks()

class ProcessPopularityTask(PeriodicTask):
    run_every = crontab(hour=4, minute=15)

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info('update popularity for products')
        call_command('popularity')
