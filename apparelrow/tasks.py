from django.db.models.loading import get_model

from haystack import site

from celery.task import task

#from celery.task import Task
#class SearchIndexUpdateTask(Task):
    #name = 'search.index.update'
    #routing_key = 'search.index.update'
    #default_retry_delay = 5 * 60
    #max_retries = 1

    #def run(self, app_name, model_name, pk, **kwargs):
        #logger = self.get_logger(**kwargs)
        #try:
            #model_class = get_model(app_name, model_name)
            #instance = model_class.objects.get(pk=pk)
            #search_index = site.get_index(model_class)
            #search_index.update_object(instance)
        #except Exception, exc:
            #logger.error(exc)
            #self.retry([app_name, model_name, pk], kwargs, exc=exc)

@task(name='apparelrow.tasks.search_index_update_task', max_retries=1)
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
