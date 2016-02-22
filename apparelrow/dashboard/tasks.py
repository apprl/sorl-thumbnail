from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_managers
from django.utils.html import strip_tags
from celery.task import task

@task(name='dashboard.tasks.send_email_task', max_retries=5, ignore_result=True)
def send_email_task(subject, body, recipient, sender, **kwargs):
    text_body = strip_tags(body)
    msg = EmailMultiAlternatives(subject, text_body, sender, [recipient])
    msg.attach_alternative(body, 'text/html')
    msg.send()
