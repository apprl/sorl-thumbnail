# -*- coding: utf-8 -*-
__author__ = 'klaswikblad'

from celery.schedules import crontab
from celery.task import periodic_task

import logging
log = logging.getLogger('celery_scheduled')

# Run importer at midnight
@periodic_task(name='apparelrow.scheduledjobs.tasks.run_importer', run_every=crontab(minute=0,hour=0), max_retries=1, ignore_result=True)
def run_importer():
    from django.core import management
    log.info('Running arfxrates job, no update.')

    try:
        management.call_command('arfxrates',refresh=True,no_update='no-update-please',solr=True)
    except Exception, msg:
        log.info('Arfxrates job1 failed %s' % msg)

    log.info('Running run_importer job.')
    management.call_command('run_importer')
    try:
        log.info('Running arfxrates job, update true.')
        management.call_command('arfxrates',refresh=True,solr=True)
    except Exception, msg:
        log.info('Arfxrates job2 failed %s' % msg)

    log.info('Running brand updates job.')
    management.call_command('brand_updates')

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
def vendor_check():
    from django.core import management
    log.info('Running clearsessions job.')
    management.call_command('clearsessions')

"""
@periodic_task(name='apparelrow.scheduledjobs.tasks.run_arfxrates', run_every=crontab(minute=0, hour=0), max_retries=1, ignore_result=True)
def run_arfxrates():
    from django.core import management
    management.call_command('arfxrates','refresh','no_update','solr'
    )
"""