from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import get_language, activate
from django.core.management import call_command
from django.db.models.loading import get_model
from haystack import site
from celery.task import task, PeriodicTask
from celery.schedules import crontab

from apparelrow.apparel.messaging import process_search_index_updates
from apparelrow.statistics.messaging import process_clicks
from apparelrow.profile.messaging import process_notification

@task(name='apparelrow.tasks.search_index_update_task', max_retries=1, ignore_result=True)
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

class ProcessSearchIndexUpdatesTask(PeriodicTask):
    run_every = timedelta(minutes=10)
    ignore_result = True

    def run(self, **kwargs):
        process_search_index_updates()

class ProcessClicksTask(PeriodicTask):
    run_every = timedelta(minutes=15)
    ignore_result = True

    def run(self, **kwargs):
        process_clicks()

class ProcessPopularityTask(PeriodicTask):
    run_every = crontab(hour=4, minute=15)

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info('update popularity for products')
        call_command('popularity')

class ProcessNotificationTask(PeriodicTask):
    run_every = timedelta(minutes=2)
    ignore_result = True

    def run(self, **kwargs):
        process_notification()

@task(name='apparelrow.tasks.beta_email_task', max_retries=5, ignore_result=True)
def beta_email_task(name, email, password, **kwargs):
    """
    Beta invite email task. Should be in beta but this is easier.
    """
    logger = beta_email_task.get_logger(**kwargs)
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
        msg = EmailMultiAlternatives(subject, text_body, 'Apparelrow <no-reply@apparelrow.com>', recipients)
        msg.attach_alternative(html_body, 'text/html')
        msg.send()

        activate(current_language)
    except Exception, exc:
        logger.error(exc)
        beta_email_task.retry(exc=exc)
