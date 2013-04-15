from django.conf import settings
from django.core.mail import send_mail

from celery.task import task

@task(name='advertiser.tasks.send_text_email_task', max_retries=5, ignore_result=True)
def send_text_email_task(subject, body, recipients, **kwargs):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
