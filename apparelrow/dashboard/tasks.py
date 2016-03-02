"""
from django.conf import settings
from django.core.mail import EmailMessage

from apparelrow.profile.notifications import get_global_variables
from celery.task import task

Code for handling this with mandrill instead
@task(name='dashboard.tasks.send_email_task', max_retries=5, ignore_result=True)
def send_email_task(email, referral_name, profile_url, profile_photo_url, recipient, sender, **kwargs):
    msg = EmailMessage(from_email=settings.DEFAULT_FROM_EMAIL, to=[email])
    msg.template_name = "invitation"

    merge_vars = {}
    merge_vars['PROFILEURL'] = profile_url
    merge_vars['REFERRALNAME'] = referral_name
    merge_vars['PROFILEPHOTOURL'] = profile_photo_url

    global_dict = get_global_variables()
    msg.global_merge_vars = global_dict
    msg.global_merge_vars.update(merge_vars)
    msg.send()
"""

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from celery.task import task

@task(name='dashboard.tasks.send_email_task', max_retries=5, ignore_result=True)
def send_email_task(subject, body, recipient, sender, **kwargs):
    text_body = strip_tags(body)
    msg = EmailMultiAlternatives(subject, text_body, sender, [recipient])
    msg.attach_alternative(body, 'text/html')
    msg.send()
