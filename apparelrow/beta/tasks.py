from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import get_language, activate
from celery.task import task

@task(name='beta.tasks.send_email_task', max_retries=5, ignore_result=True)
def send_email_task(name, email, password, **kwargs):
    """
    Beta invite email task. Should be in beta but this is easier.
    """
    logger = send_email_task.get_logger(**kwargs)
    try:
        context = {}
        context['domain'] = 'http://%s' % (Site.objects.get_current().domain,)
        context['name'] = name
        context['email'] = email
        context['password'] = password

        subject_template_name = 'beta/mail_subject.html'
        body_template_name = 'beta/mail_body.html'

        current_language = get_language()
        activate(settings.LANGUAGE_CODE)

        subject = ''.join(render_to_string(subject_template_name, context).splitlines())
        html_body = render_to_string(body_template_name, context)
        text_body = strip_tags(html_body)
        recipients = [email]
        msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients)
        msg.attach_alternative(html_body, 'text/html')
        msg.send()

        activate(current_language)
    except Exception, exc:
        logger.error(exc)
        send_email_task.retry(exc=exc)
