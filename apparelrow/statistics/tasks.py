from celery.task import task
from statistics.models import ProductClick

@task(name='statistics.tasks.increment_click', max_retries=5, ignore_result=True)
def increment_click(product_id):
    ProductClick.objects.increment_clicks(product_id)
