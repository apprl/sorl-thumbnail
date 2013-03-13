import logging
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, resolve

import redis

logger = logging.getLogger('statistics.middleware')

class ActiveUsersMiddleware:
    def process_request(self, request):
        if request.user.is_authenticated():
            try:
                redis_connection = redis.StrictRedis(host=settings.CELERY_REDIS_HOST,
                                                     port=settings.CELERY_REDIS_PORT,
                                                     db=settings.CELERY_REDIS_DB)

                current_date = datetime.date.today()
                daily_key = 'active_daily_%s' % (current_date.isoformat(),)
                weekly_key = 'active_weekly_%s-%02d' % (current_date.isocalendar()[0],
                                                      current_date.isocalendar()[1])
                monthly_key = 'active_monthly_%s' % (current_date.strftime('%Y-%m'),)

                redis_connection.sadd(daily_key, request.user.pk)
                redis_connection.sadd(weekly_key, request.user.pk)
                redis_connection.sadd(monthly_key, request.user.pk)
            except Exception as e:
                logger.error('ActiveUsersMiddleware error: %s' % (str(e),))
