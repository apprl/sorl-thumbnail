# -*- coding: utf-8 -*-
# Django settings for development server 

import os.path

from settings_common import *

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SERVER_APP_ROOT = os.path.join(PROJECT_ROOT, '..','..')

DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default':
        {'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'apprl',
            'USER': 'postgres',
            'PASSWORD': 'admin',
            'HOST': 'localhost',
    }
}
CONN_MAX_AGE = 600

LOGGING['handlers']['app_core']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'app_logger.log')
LOGGING['handlers']['apparel_debug']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'app_logger.log')
LOGGING['handlers']['importer']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'app_logger.log')
LOGGING['handlers']['dashboard']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'app_logger.log')
LOGGING['handlers']['theimp']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'app_logger.log')
LOGGING['handlers']['theimp_links']['filename'] = os.path.join(SERVER_APP_ROOT, 'var', 'logs', 'pending_requests.log')

# CACHE CONFIGURATION
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 12,
    },
    'nginx': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 24 * 20,
        'KEY_FUNCTION': lambda key, x, y: key,
    },
}


# Storage
#AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME = AWS_S3_CUSTOM_DOMAIN = 's-jdev.apprl.com'

#DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

STATIC_URL = '/static/'
#STATIC_URL = 'http://s.apprl.com/'
STATIC_ROOT = os.path.join(PROJECT_ROOT,'static')
STATICFILES_DIRS = (
    (os.path.join(PROJECT_ROOT, 'static_local')),
)

APPAREL_DECOMPRESS_UTILS = {
    'gzip': '/bin/gunzip',
    'zip':  '/bin/zip',
}

APPAREL_IMPORTER_WAREHOUSE = os.path.join(PROJECT_ROOT, '..', 'warehouse')

FACEBOOK_APP_ID = '151961958184186'
FACEBOOK_API_KEY = '2c74b09ea8dae83e4b9699a72ee55db2'
FACEBOOK_SECRET_KEY = '0e53ad32bdd85a49bb972fa2f6985908'

#CACHE_MIDDLEWARE_KEY_PREFIX = 'ar-demo'
#CACHE_MIDDLEWARE_SECONDS = 120

SOLR_URL = 'http://127.0.0.1:8983/solr'
SOLR_RELOAD_URL = 'http://127.0.0.1:8983/solr/admin/cores?action=RELOAD&core=collection1'
SOLR_CONF_DIRECTORY = os.path.join(PROJECT_ROOT, '..', 'solr', 'solr', 'collection1', 'conf')
SOLR_CURRENCY_FILE = os.path.join(SOLR_CONF_DIRECTORY, 'currency.xml')
SOLR_SYNONYM_FILE = os.path.join(SOLR_CONF_DIRECTORY, 'synonyms.txt')

BROKER_URL = "redis://localhost:6380/0"

THEIMP_REDIS_HOST = 'localhost'
THEIMP_REDIS_PORT = 6380

CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6380
CELERY_REDIS_DB = 0
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ALWAYS_EAGER=DEBUG

if CELERY_ALWAYS_EAGER:
    print 'Celery set to always eager.'

EMAIL_BACKEND = 'django.core.mail.backends.file.EmailBackend'


import djcelery
djcelery.setup_loader()

DEFAULT_FILE_STORAGE = 'apparelrow.storage.HybridStorage'

HYBRID_STORAGE_BACKENDS= ('django.core.files.storage.FileSystemStorage',
                          #'storages.backends.s3boto.S3BotoStorage'
                        )


# --- Application wide init code goes here. 
# It would be nice to move this somewhere, but I'm not sure where to put it
# to ensure it is executed only *once* and after all settings has been evaluated

#INTERNAL_IPS = ('127.0.0.1',)
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
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
INSTALLED_APPS += ('debug_toolbar',
                   'raven.contrib.django.raven_compat',
                  )

RAVEN_CONFIG = {
    'dsn': 'https://3d0e910228c343f38f69e4640a1243f0:f27b835e983a404d82a4871f97b39807@sentry.local.com/2',
}

SENTRY_DSN='https://3d0e910228c343f38f69e4640a1243f0:f27b835e983a404d82a4871f97b39807@sentry.local.com/2'


#PIPELINE_CSS_COMPRESSOR = None
#PIPELINE_JS_COMPRESSOR = None
# npm install -g cssmin
"""PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.cssmin.CSSMinCompressor'
PIPELINE_CSSMIN_BINARY = '/usr/bin/env cssmin'
PIPELINE_CSSMIN_ARGUMENTS = ''

# npm install -g uglify-js
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'
PIPELINE_UGLIFYJS_BINARY = '/usr/bin/env uglifyjs'
PIPELINE_UGLIFYJS_ARGUMENTS = ''
"""
#PIPELINE_ENABLED = False
PIPELINE_LESS_BINARY = '/usr/local/bin/lessc'
#PIPELINE_YUGLIFY_BINARY = '/usr/local/bin/yuglify'

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
#ROSETTA_HOME = 'http://apprl.local.com/rosetta/'

LOCALE_PATHS = (
    os.path.join(SERVER_APP_ROOT, 'locale'),
)