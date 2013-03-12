from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from celery.task import task

@task(name='profile.views.send_email_confirm_task', max_retries=5, ignore_result=True)
def send_email_confirm_task(subject, body, recipient, **kwargs):
    text_body = strip_tags(body)
    msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient])
    #msg.attach_alternative(body, 'text/html')
    msg.send()
