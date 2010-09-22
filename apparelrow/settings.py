# -*- coding: utf-8 -*-
# Django settings for basic pinax project.

import os.path
import posixpath
import logging
import logging.config

gettext = lambda s: s

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# tells Pinax to use the default theme

DEBUG = True
TEMPLATE_DEBUG = DEBUG
FORCE_SCRIPT_NAME = ''

LOGGING_CONFIG = os.path.join(PROJECT_ROOT, '..', 'etc', 'logging.conf') # logging configuration file

if not hasattr(logging, 'initialised'):
    logging.config.fileConfig(LOGGING_CONFIG)
    
    if DEBUG:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logging.debug('Using debug logger')
    
    logging.info('Initialised application logger')
    setattr(logging, 'initialised', True)


# tells Pinax to serve media through django.views.static.serve.
SERVE_MEDIA = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'     # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'apparelrow_dev'  #os.path.join(PROJECT_ROOT, 'dev.db')       # Or path to database file if using sqlite3.
DATABASE_USER = 'apparelrow'             # Not used with sqlite3.
DATABASE_PASSWORD = 'r0W'
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Stockholm'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LANGUAGE_CODE = 'sv'
LANGUAGES = (
#    ('en', gettext('English')), 
    ('sv', gettext('Swedish')), 
)


# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/media/'

# Absolute path to the directory that holds static files like app media.
# Example: "/home/media/media.lawrence.com/apps/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = '/_media/static/'

# Additional directories which hold static files
STATICFILES_DIRS = (
    ('apparelrow', os.path.join(PROJECT_ROOT, 'media')),
#    ('pinax', os.path.join(PINAX_ROOT, 'media', PINAX_THEME)),
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'zb*p6d^l!by6hhugm+^f34m@-yex9c90yz)c_71t=+lxo%mn(3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'facebook.djangofb.FacebookMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'facebookconnect.middleware.FacebookConnectMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'trackback.middleware.PingbackUrlInjectionMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'facebookconnect.models.FacebookBackend',
    'django.contrib.auth.backends.ModelBackend',
)


ROOT_URLCONF = 'apparelrow.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)


TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    
    "context_processors.settings",
    "context_processors.js_templates",
    "notification.context_processors.notification",
    "announcements.context_processors.site_wide_announcements",
)

INSTALLED_APPS = (
    # included
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.humanize',
    
    
    # external
    'notification', # must be first
    'facebookconnect',
    'registration',
#    'mailer',          # FIXME: Includes e-mail manager, set this up later
    'announcements',
    'pagination',
    'mptt',
    'sorl.thumbnail',
    
    'tagging',
    'pagination',
    'voting',
    'django.contrib.comments',
    'ajaxcomments',
    'django_extensions',
    'trackback',
    'recommender',
    #'south',
    'jsmin',
    'compress',

    'apparel',
    'scale',
    'watcher',
    'profile',
    'importer',
    
        
    # internal (for now)
    'django.contrib.admin',
    'apparelrow',
)



# - COMPRESS SETTINGS -
COMPRESS_CSS = {}
COMPRESS_JS = {
    'widget': {
        'source_filenames': ('js/jquery/jquery-1.4.2.js',
                             'js/jquery/jquery.tools.min.js',
                             'js/widget.js'),
        'output_filename': 'js/compiled/widget.js',
    },
    'jquery': {
        'source_filenames': ('js/jquery/jquery.hypersubmit.js',
                             'js/jquery/jquery.tools.min.js',
                             'js/jquery/jquery.tmpl.js',
                             'js/jquery/jquery.history.js',
                             'js/jquery/jquery.ui.rotatable.js',
                             'js/jquery/jquery.autogrow.js'),
        'output_filename': 'js/compiled/jquery.js',
    },
}

COMPRESS = True

CSRF_FAILURE_VIEW = 'apparel.views.csrf_failure'

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/profiles/profile/%s/" % o.username,
}

MARKUP_FILTER_FALLBACK = 'none'
MARKUP_CHOICES = (
    ('restructuredtext', u'reStructuredText'),
    ('textile', u'Textile'),
    ('markdown', u'Markdown'),
    ('creole', u'Creole'),
)
WIKI_MARKUP_CHOICES = MARKUP_CHOICES



EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = DEBUG
CONTACT_EMAIL = "support@hanssonlarsson.se"
SITE_NAME = "ApparelRow"


# ACCOUNT/LOGIN AND OTHER STUFF
ACCOUNT_ACTIVATION_DAYS = 7

LOGIN_REDIRECT_URLNAME = "what_next"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

AUTH_PROFILE_MODULE='profile.ApparelProfile'

# FACEBOOK CONFIGURATION
FACEBOOK_API_KEY = '44d47ef3e7285cace9a4c7c88f645742'
FACEBOOK_SECRET_KEY = '1701399a0a6126f84d08d7e702285c56'
FACEBOOK_INTERNAL = True
FACEBOOK_CACHE_TIMEOUT = 1800
DUMMY_FACEBOOK_INFO = {
    'uid':0,
    'name':'(Private)',
    'first_name':'(Private)',
    'pic_square_with_logo':'http://www.facebook.com/pics/t_silhouette.gif',
    'affiliations':None,
    'status':None,
    'proxied_email':None,
}

EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_HOST_USER     = 'postman@hanssonlarsson.se'
EMAIL_HOST_PASSWORD = 'K6kb4Lle'
EMAIL_USE_TLS       = True



APPAREL_DEFAULT_AVATAR     = os.path.join('/', MEDIA_URL, 'images', 'avatar.jpg')
APPAREL_PRODUCT_IMAGE_ROOT = 'products'
APPAREL_LOOK_MAX_SIZE      = 470
APPAREL_LOOK_FEATURED      = 3
APPAREL_IMPORTER_WAREHOUSE = os.path.join(PROJECT_ROOT, '..', 'warehouse')
APPAREL_IMPORTER_COLORS = (
    (u'black'  , u'svart',),
    (u'grey'   , u'grå', u'gray'),
    (u'white'  , u'vit',),
    (u'beige'  , u'khaki',),
    (u'brown'  , u'brun',),
    (u'red'    , u'röd',),
    (u'yellow' , u'gul',),
    (u'green'  , u'grön', u'olive', u'oliv'),
    (u'blue'   , u'blå', u'navy'),
    (u'silver' , u'silver',),
    (u'gold'   , u'guld',),
    (u'pink'   , u'rosa',),
    (u'orange' , ),
    (u'magenta', u'magenta',),
)

# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
try:
    from settings_local import *
except ImportError:
    pass
