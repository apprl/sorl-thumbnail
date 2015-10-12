# -*- coding: utf-8 -*-
from theimp.importer import Importer

__author__ = 'klaswikblad'

from celery.schedules import crontab
from celery.task import periodic_task, task

import logging
log = logging.getLogger('celery_scheduled')

# Run importer at midnight
@periodic_task(name='apparelrow.scheduledjobs.tasks.run_importer', run_every=crontab(minute='0',hour='0'), max_retries=1, ignore_result=True)
def run_importer():
    from django.core import management
    log.info('Running arfxrates job, no update.')

    try:
        management.call_command('arfxrates',refresh=True,no_update='no-update-please',solr=True)
    except Exception, msg:
        log.warn('Arfxrates job1 failed %s' % msg)

    #log.info('Running run_importer job.')
    #management.call_command('run_importer')
    try:
        log.info('Running arfxrates job, update true.')
        management.call_command('arfxrates',refresh=True,solr=True)
    except Exception, msg:
        log.warn('Arfxrates job2 failed %s' % msg)

    log.info('Running brand updates job.')
    management.call_command('brand_updates')

# Run importer at midnight
@periodic_task(name='apparelrow.scheduledjobs.tasks.initiate_products_importer', run_every=crontab(minute='0',hour='17'), max_retries=1, ignore_result=True)
def initiate_product_importer():
    from django.core import management
    from theimp.models import Vendor
    log.info('Initiating product import job.')
    vendors = Vendor.objects.filter(vendor__isnull=False)
    for vendor in vendors:
        run_vendor_importer.delay(vendor)

#daily
@periodic_task(name='apparelrow.scheduledjobs.tasks.update_clicks_summary', run_every=crontab(minute='0',hour='2'), max_retries=1, ignore_result=True)
def update_clicks_summary():
    from django.core import management
    log.info('Running update click earnings job.')
    management.call_command('update_clicks_earnings_status')

#daily
@periodic_task(name='apparelrow.scheduledjobs.tasks.clicks_summary', run_every=crontab(minute='0',hour='5'), max_retries=1, ignore_result=True)
def clicks_summary():
    from django.core import management
    log.info('Running click summary job.')
    management.call_command('clicks_summary',verbosity=0, interactive=False)


#weekly
@periodic_task(name='apparelrow.scheduledjobs.tasks.popularity', run_every=crontab(minute='0',hour='0',day_of_week='sunday'), max_retries=1, ignore_result=True)
def popularity():
    from django.core import management
    log.info('Running popularity job.')
    management.call_command('popularity')
    log.info('Running look popularity job.')
    management.call_command('look_popularity')

#weekly (takes long time)
@periodic_task(name='apparelrow.scheduledjobs.tasks.check_availability', run_every=crontab(minute='0',hour='0',day_of_week='sunday'), max_retries=1, ignore_result=True)
def check_availability():
    from django.core import management
    log.info('Running availability job.')
    management.call_command('check_availability',email=True)

#daily takes long time
@periodic_task(name='apparelrow.scheduledjobs.tasks.dashboard_import', run_every=crontab(minute='0',hour='0'), max_retries=5, ignore_result=True)
def dashboard_import():
    from django.core import management
    log.info('Running dashboard_import job.')
    management.call_command('dashboard_import',days=365)

#daily
@periodic_task(name='apparelrow.scheduledjobs.tasks.dashboard_payment', run_every=crontab(minute='0',hour='0',day_of_month='1'), max_retries=5, ignore_result=True)
def dashboard_payment():
    from django.core import management
    log.info('Running dashboard_payment job.')
    management.call_command('dashboard_payment')

# daily
@periodic_task(name='apparelrow.scheduledjobs.tasks.vendor_check', run_every=crontab(minute='0',hour='0'), max_retries=5, ignore_result=True)
def vendor_check():
    from django.core import management
    log.info('Running daily vendor_check job.')
    management.call_command('vendor_check')

# weekly
@periodic_task(name='apparelrow.scheduledjobs.tasks.clearsessions', run_every=crontab(minute='0',hour='0',day_of_week='saturday'), max_retries=5, ignore_result=True)
def clearsessions():
    from django.core import management
    log.info('Running clearsessions job.')
    management.call_command('clearsessions')

# daily just before midnight
@periodic_task(name='apparelrow.scheduledjobs.tasks.recalculate_earnings', run_every=crontab(minute='59',hour='23'), max_retries=3, ignore_result=True)
def recalculate_earnings():
    from django.core import management
    management.call_command('update_aggregated_data')

# daily just after midnight
@periodic_task(name='apparelrow.scheduledjobs.tasks.collect_calculate_earnings', run_every=crontab(minute='30',hour='0'), max_retries=3, ignore_result=True)
def calculate_earnings():
    from django.core import management
    management.call_command('collect_aggregated_data')


# daily afternoon
@periodic_task(name='apparelrow.scheduledjobs.tasks.check_chrome_extension', run_every=crontab(minute='30',hour='15'), ignore_result=True)
def check_chrome_extension():
    from django.core import management
    management.call_command('deeplink_live_test')


@task(name='apparelrow.scheduledjobs.tasks.run_vendor_product_importer', max_retries=5, ignore_result=True)
def run_vendor_importer(vendor):
    log.info('Initiating import for vendor %s.' % vendor)
    Importer().run(dry=False, vendor=vendor)

@periodic_task(name='apparelrow.scheduledjobs.tasks.check_clicks_limit_per_vendor', run_every=crontab(minute='5'), max_retries=5, ignore_result=True)
def check_clicks_limit_per_vendor():
    from django.core import management
    management.call_command('check_clicks_limit_per_vendor')
