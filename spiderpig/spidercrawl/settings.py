# Scrapy settings for spiderpig project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#
import os
import os.path


BOT_NAME = 'spidercrawl'
LOG_LEVEL = 'INFO'

RAVEN_CONFIG = {
    'dsn': 'https://d9f9d656ce4f43b8b0e180337c81ac20:9bec16b72e9f45eca4b0a4361c72e8a8@sentry.wordex.se/9',
}

SENTRY_DSN='https://d9f9d656ce4f43b8b0e180337c81ac20:9bec16b72e9f45eca4b0a4361c72e8a8@sentry.wordex.se/9'


CONCURRENT_REQUESTS_PER_DOMAIN = 2

DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True

SPIDER_MODULES = ['spidercrawl.spiders']
NEWSPIDER_MODULE = 'spidercrawl.spiders'

ITEM_PIPELINES = [
    'spiderpig.spidercrawl.pipelines.CustomImagesPipeline',
    'spiderpig.spidercrawl.pipelines.RequiredFieldsPipeline',
    'spiderpig.spidercrawl.pipelines.PricePipeline',
]

EXTENSIONS = {
    'scrapy_sentry.extensions.Errors':10,
    'spidercrawl.pipelines.DatabaseHandler': 500,
}

DOWNLOADER_MIDDLEWARES = {
    'spiderpig.spidercrawl.middlewares.RelCanonicalMiddleware': 1000,
    'spiderpig.spidercrawl.middlewares.DownloadGzipMiddleware': 10,
    'scrapy.contrib.downloadermiddleware.httpauth.HttpAuthMiddleware': 500,
    'scrapy.contrib.downloadermiddleware.httpcompression.HttpCompressionMiddleware': 1,
    #'spiderpig.middlewares.RandomUserAgentMiddleware': 1000,
    #'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
}

USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0'
]
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'


# DJANGO INTEGRATION
import sys
import os.path
#sys.path.append(os.path.abspath('../../'))
sys.path.append(os.path.abspath('../'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apparelrow.settings')
from django.conf import settings

IMAGES_EXPIRES = 300
#IMAGES_STORE = os.path.join(settings.PROJECT_ROOT, 'media', settings.APPAREL_PRODUCT_IMAGE_ROOT)
IMAGES_STORE = 's3://%s/%s/' % (settings.AWS_STORAGE_BUCKET_NAME,
                                settings.APPAREL_PRODUCT_IMAGE_ROOT)
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

try:
    from .local import *
except ImportError:
    pass
