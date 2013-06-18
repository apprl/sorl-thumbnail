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
    'scrapy.contrib.pipeline.images.ImagesPipeline',
    'spiderpig.pipelines.VendorRequiredPipeline',
    'spiderpig.pipelines.StockPipeline',
    'spiderpig.pipelines.PricePipeline',
    'spiderpig.pipelines.PushJSONPipeline',
]

IMAGES_STORE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'images')
IMAGES_EXPIRES = 90

#DOWNLOADER_MIDDLEWARES = {
    #'spiderpig.middlewares.RandomUserAgentMiddleware': 1000,
    #'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
#}

#USER_AGENT_LIST = [
    #'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'
    #'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0'
#]
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0'


# DJANGO INTEGRATION
import sys
sys.path.append('/home/tote/coding/apparelrow/apparelrow')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apparelrow.settings')
#def setup_django_env(path):
    #print path
    #import imp, os
    #from django.core.management import setup_environ

    #f, filename, desc = imp.find_module('settings', [path])
    #project = imp.load_module('settings', f, filename, desc)

    #setup_environ(project)

    #import sys
    #sys.path.append(os.path.abspath(os.path.join(path, os.path.pardir)))

#setup_django_env('/home/tote/coding/apparelrow/apparelrow/')
#setup_django_env(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'apparelrow')))
