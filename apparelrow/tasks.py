import logging
from datetime import timedelta

from django.db.models.loading import get_model
from haystack import site
from celery.task import task, PeriodicTask

from apparelrow.statistics.messaging import process_clicks

logger = logging.getLogger(__name__)

@task(name='apparelrow.tasks.search_index_update_task', max_retries=1, ignore_result=True)
def search_index_update_task(app_name, model_name, pk, **kwargs):
    try:
        model_class = get_model(app_name, model_name)
        instance = model_class.objects.get(pk=pk)
        search_index = site.get_index(model_class)
        logger.info('update solr index for instance %s' % (instance,))
        search_index.update_object(instance)
    except Exception, exc:
        logger.error(exc)
        search_index_update_task.retry(exc=exc)

class ProcessClicksTask(PeriodicTask):
    run_every = timedelta(minutes=15)

    def run(self, **kwargs):
        process_clicks()
