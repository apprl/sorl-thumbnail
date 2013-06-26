import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import get_model

from celery.task import task, periodic_task
from celery.schedules import crontab


@task(name='advertiser.tasks.send_text_email_task', max_retries=5, ignore_result=True)
def send_text_email_task(subject, body, recipients, **kwargs):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)


@periodic_task(name='advertiser.tasks.set_accepted_after_40_days', run_every=crontab(minute=0, hour=5), max_retries=5, ignore_result=True)
def set_accepted_after_40_days():
    Transaction = get_model('advertiser', 'Transaction')
    today = datetime.date.today()
    forty_days_ago = today - datetime.timedelta(days=40)
    for transaction in Transaction.objects.filter(status=Transaction.PENDING) \
                                          .filter(created__lte=forty_days_ago):
        transaction.automatic_accept = True
        transaction.accept()
