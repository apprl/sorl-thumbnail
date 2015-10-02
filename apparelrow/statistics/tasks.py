import datetime

from django.conf import settings
from django.db.models import get_model
from django.template.defaultfilters import floatformat

from celery.task import task, periodic_task
from celery.schedules import crontab

import redis


@task(name='statistics.tasks.product_buy_click', max_retries=5, ignore_result=True)
def product_buy_click(product_id, referer, ip, user_agent, user_id, page, cookie_already_exists):
    """
    Buy click stats for products
    """
    product = None
    try:
        product = get_model('apparel', 'Product').objects.get(pk=product_id)
    except get_model('apparel', 'Product').DoesNotExist:
        if page != 'Ext-Store' and page != 'Ext-Link':
            return

    if product_id:
        get_model('statistics', 'ProductClick').objects.increment_clicks(product_id)

    if product and product.default_vendor:
        slug = product.slug
        vendor = product.default_vendor.vendor
        price = floatformat(product.default_vendor.lowest_price_in_sek, 0)
    else:
        slug = None
        vendor = None
        price = None

    action = 'BuyReferral'
    if page == 'Ext-Store':
        action = 'StoreLinkClick'

    get_model('statistics', 'ProductStat').objects.create(
        action=action,
        product=slug,
        vendor=vendor,
        price=price,
        user_id=user_id,
        page=page,
        referer=referer,
        ip=ip,
        user_agent=user_agent,
        is_valid=bool(not cookie_already_exists))


@periodic_task(name='statistics.tasks.active_users', run_every=crontab(hour='04', minute='55'), max_retries=2, ignore_result=True)
def active_users():
    """
    Move daily, weekly and monthly active user data from redis to database
    every day at 04:55.
    """
    redis_connection = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                                         port=settings.CELERY_REDIS_PORT,
                                         db=settings.CELERY_REDIS_DB)
    current_date = datetime.date.today()
    partial_daily_key = current_date.isoformat()
    partial_weekly_key = '%s-%02d' % (current_date.isocalendar()[0],
                                      current_date.isocalendar()[1])
    partial_monthly_key = current_date.strftime('%Y-%m')

    # Daily
    for key in redis_connection.keys('active_daily_*'):
        period_key = key[13:]
        if period_key < partial_daily_key:
            period_value = redis_connection.scard(key)
            get_model('statistics', 'ActiveUser').objects.create(period_type='D',
                                                                 period_key=period_key,
                                                                 period_value=period_value)
            redis_connection.delete(key)

    # Weekly
    for key in redis_connection.keys('active_weekly_*'):
        period_key = key[14:]
        if period_key < partial_weekly_key:
            period_value = redis_connection.scard(key)
            get_model('statistics', 'ActiveUser').objects.create(period_type='W',
                                                                 period_key=period_key,
                                                                 period_value=period_value)
            redis_connection.delete(key)

    # Monthly
    for key in redis_connection.keys('active_monthly_*'):
        period_key = key[15:]
        if period_key < partial_monthly_key:
            period_value = redis_connection.scard(key)
            get_model('statistics', 'ActiveUser').objects.create(period_type='M',
                                                                 period_key=period_key,
                                                                 period_value=period_value)
            redis_connection.delete(key)
