from django.conf import settings
from django.core.mail import EmailMessage

from apparelrow.profile.notifications import get_global_variables
from celery.task import task

# Code for handling this with mandrill instead
@task(name='dashboard.tasks.send_email_task', max_retries=5, ignore_result=True)
def send_email_task(email, referral_name, profile_url, profile_photo_url, **kwargs):
    msg = EmailMessage(from_email=settings.DEFAULT_FROM_EMAIL, to=[email])
    msg.template_name = "referralMail"

    merge_vars = {}
    merge_vars['PROFILEURL'] = profile_url
    merge_vars['REFERRALNAME'] = referral_name
    merge_vars['PROFILEPHOTOURL'] = profile_photo_url

    # this is not currently used, but for some reason the API fails if this is not set.
    # it could say anything, none of this lands in the final email
    msg.template_content = { # Content blocks to fill in
        'EMPTY_BLOCK': "<a href='apprl.com/*|URL|*'>Hello there!</a>"
    }

    global_dict = get_global_variables()
    msg.global_merge_vars = global_dict
    msg.global_merge_vars.update(merge_vars)
    msg.send()