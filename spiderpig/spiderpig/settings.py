# Scrapy settings for spiderpig project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#
import os
import os.path


BOT_NAME = 'spiderpig'

CONCURRENT_REQUESTS_PER_DOMAIN = 2

DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True

SPIDER_MODULES = ['spiderpig.spiders']
NEWSPIDER_MODULE = 'spiderpig.spiders'

ITEM_PIPELINES = [
    'spiderpig.pipelines.CustomImagesPipeline',
    'spiderpig.pipelines.RequiredFieldsPipeline',
    'spiderpig.pipelines.PricePipeline',
]

EXTENSIONS = {
    'spiderpig.pipelines.DatabaseHandler': 500,
}

DOWNLOADER_MIDDLEWARES = {
    'spiderpig.middlewares.RelCanonicalMiddleware': 1000,
    #'spiderpig.middlewares.RandomUserAgentMiddleware': 1000,
    #'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
}

USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0'
]
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'


# DJANGO INTEGRATION
# TODO: this must work when deployed
import sys
sys.path.append('/home/tote/coding/apparelrow/apparelrow')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apparelrow.settings')
from django.conf import settings

IMAGES_EXPIRES = 90
#IMAGES_STORE = os.path.join(settings.PROJECT_ROOT, 'media', settings.APPAREL_PRODUCT_IMAGE_ROOT)
IMAGES_STORE = 's3://%s/%s/' % (settings.AWS_STORAGE_BUCKET_NAME,
                                settings.APPAREL_PRODUCT_IMAGE_ROOT)
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
