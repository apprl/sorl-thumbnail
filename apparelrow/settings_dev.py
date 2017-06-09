# -*- coding: utf-8 -*-
# Django settings for development server
from celery.schedules import crontab
import os
from apparelrow.settings_common import *

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SERVER_APP_ROOT = os.path.join(PROJECT_ROOT, '..', '..')
DEBUG = True
TEMPLATE_DEBUG = False
ALLOWED_HOSTS = ['apprl.local.com']
DATA_HOST = "localhost"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'
DATABASES = {
    'default':
        {'ENGINE': 'django.db.backends.postgresql_psycopg2',
         'NAME': 'apparel',
         'USER': 'postgres',
         'PASSWORD': 'postgres',
         'HOST': 'localhost',
         }
}

if os.environ.get('prod_copy'):
    print 'Using custom prod_copy host %s' % os.environ['prod_copy']
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'HOST': os.environ['prod_copy'],
            'NAME': 'apparel',
            'USER': 'apparel',
            'PASSWORD': 'Frikyrk4',
            'OPTIONS': {'connect_timeout': 2}  # in case we forget to turn on vpn :)
        }
    }

CONN_MAX_AGE = 600
# CACHE CONFIGURATION
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300,
    },
    'nginx': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 24 * 20,
        'KEY_FUNCTION': lambda key, x, y: key,
    },
    'importer': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 10,
    },
}
# Storage
LOCAL = True
if not LOCAL:
    AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME = AWS_S3_CUSTOM_DOMAIN = 's-staging.apprl.com'
    STATIC_URL = 'http://%s/' % AWS_STORAGE_BUCKET_NAME
    STATICFILES_STORAGE = 'apparelrow.storage.CachedStaticS3BotoStorage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
    STATIC_URL = '/static/'
AWS_S3_SECURE_URLS = False
STATIC_ROOT = os.path.join(PROJECT_ROOT, '../static')
# print STATIC_ROOT
# STATICFILES_DIRS = (
#     (os.path.join(PROJECT_ROOT, 'static_local')),
# )
APPAREL_DECOMPRESS_UTILS = {
    'gzip': '/bin/gunzip',
    'zip': '/bin/zip',
}
APPAREL_IMPORTER_WAREHOUSE = os.path.join(PROJECT_ROOT, '..', 'warehouse')
FACEBOOK_APP_ID = '1619044961728886'
FACEBOOK_SECRET_KEY = '6a2a6a3b2cea7d7af2c561f7a689005f'
SOLR_URL = 'http://%s:8983/solr' % DATA_HOST
SOLR_RELOAD_URL = 'http://%s:8983/solr/admin/cores?action=RELOAD&core=collection1' % DATA_HOST
SOLR_CONF_DIRECTORY = os.path.join(SERVER_APP_ROOT, 'apparelrow', 'solr-apprl', 'solr', 'example', 'solr',
                                   'collection1', 'conf')
SOLR_CURRENCY_FILE = os.path.join(SOLR_CONF_DIRECTORY, 'currency.xml')
SOLR_SYNONYM_FILE = os.path.join(SOLR_CONF_DIRECTORY, 'synonyms.txt')
BROKER_URL = "redis://localhost:6379/0"
THEIMP_REDIS_HOST = 'localhost'
THEIMP_REDIS_PORT = 6379
CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6379
CELERY_REDIS_DB = 0
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ALWAYS_EAGER = True
CELERY_TIMEZONE = 'Europe/Stockholm'

# just write out the email to the console instead of sending it
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

import djcelery

djcelery.setup_loader()
# --- Application wide init code goes here. 
# It would be nice to move this somewhere, but I'm not sure where to put it
# to ensure it is executed only *once* and after all settings has been evaluated
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)
INSTALLED_APPS += ('debug_toolbar',)
# PIPELINE_CSS_COMPRESSOR = None
# PIPELINE_JS_COMPRESSOR = None
# npm install -g cssmin
"""PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.cssmin.CSSMinCompressor'
PIPELINE_CSSMIN_BINARY = '/usr/bin/env cssmin'
PIPELINE_CSSMIN_ARGUMENTS = ''
# npm install -g uglify-js
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'
PIPELINE_UGLIFYJS_BINARY = '/usr/bin/env uglifyjs'
PIPELINE_UGLIFYJS_ARGUMENTS = ''
"""
# PIPELINE_ENABLED = True
# Has to be activated when running on osx. Works per default on ubuntu.
# PIPELINE_YUGLIFY_BINARY = '/usr/local/bin/yuglify'
# Rosetta Google Translate
# To register a site https://ssl.bing.com/webmaster/home/mysites
ROSETTA_MESSAGES_PER_PAGE = 5
ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'en'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Engelska'
ROSETTA_WSGI_AUTO_RELOAD = False
ROSETTA_UWSGI_AUTO_RELOAD = False
ROSETTA_EXCLUDED_APPLICATIONS = ()
ROSETTA_REQUIRES_AUTH = True
ROSETTA_STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'
# ROSETTA_HOME = 'http://apprl.local.com/rosetta/'
LOCALE_PATHS = (
    os.path.join(SERVER_APP_ROOT, 'locale'),
)
SKIP_SOUTH_TESTS = True
SOUTH_TESTS_MIGRATE = False
GEOIP_URL = 'http://localhost:4999/ip/%s'
GEOIP_DEBUG = True
GEOIP_RETURN_LOCATION = "SE"
LOCALE_INDEPENDENT_PATHS = (
    r'^/backend/',
    r'^/products/[\d]+/(like|unlike)',
    r'^/looks/[\w-]+?/(like|unlike)',
    r'^/look/',
    r'^/looks/',
    r'^/sitemap',
    r'^/embed',
    r'^/images/temporary/',
    r'^/a/link',
    r'^/a/conversion',
    r'^/track/',
    r'^/profile/',
    r'^/dialog/',
    r'^/api/',
    r'^/shop/',
    r'^/embed/',
    r'^/pd/',
    r'^/p/',
    r'^/apply/',
    r'^/publisher/',
    r'^/popup/',
    r'^/i/',
    r'^/s/',
    r'^/accounts/',
    r'^/admin/',
    r'^/store/',
    r'^/search/',
    r'^/users/',
    r'^/products/',
    r'^/community/',
    r'^/track/',
    r'^/brand/',
    r'^/notifications/',
    r'^/redirect/',
    r'^/productwidget/',
    r'^/widget/',
    r'^/brands/',
    r'^/follow/',
    r'^/',
)
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'localeurl.middleware.LocaleURLMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apparelrow.apparel.middleware.UpdateLocaleSessionMiddleware',
    'apparelrow.profile.middleware.ImpersonateMiddleware',
    'apparelrow.statistics.middleware.ActiveUsersMiddleware',
    'apparelrow.apparel.middleware.InternalReferralMiddleware',
    'apparelrow.apparel.middleware.GenderMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'apparelrow.apparel.middleware.LocationMiddleware',
    'apparelrow.dashboard.middleware.ReferralMiddleware',
)
# TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
# Variable for temporary tracking string for tailsweep campaign.
GINA_TRACKING = {"user_ids": [26976, 2, 3, 4, 5, 6, 7],
                 "tracking_string": "&utm_source=tailsweep_apprl&utm_medium=social&utm_campaign=conversions_2016_se"}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'NOTSET',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout
        },
    },
    'loggers': {
        'django': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['console'],
        },
        'pysolr': {
            'level': 'WARNING', # pysolr is too verbose by default
            'propagate': True,
            'handlers': ['console'],
        },
        '': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['console'],
        },
    }
}
import logging

if len(sys.argv) > 1 and sys.argv[1] == 'test':
    logging.disable(logging.CRITICAL)
