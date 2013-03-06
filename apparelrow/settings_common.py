# -*- coding: utf-8 -*-

import os.path
import posixpath

gettext = lambda s: s

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

FORCE_SCRIPT_NAME = ''

ADMINS = (
    ('Hansson & Larsson', 'admin@hanssonlarsson.se'),
    ('Joel Bohman', 'joelboh@gmail.com'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = ['.apprl.com']

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Stockholm'



SITE_ID = 1
SITE_NAME = "Apprl"

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3

# Locale paths
LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, 'locale'),
)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'sv'
LANGUAGES = (
    ('en', gettext(u'English (€)')),
    ('sv', gettext(u'Swedish (SEK)')),
)
SHORT_LANGUAGES = (
    ('en', gettext(u'Eng (€)')),
    ('sv', gettext(u'Swe (SEK)')),
)
LANGUAGE_TO_CURRENCY = {
    'en': 'EUR',
    'sv': 'SEK',
}
MAX_MIN_CURRENCY = {
    'en': 1000,
    'sv': 10000,
    }


# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/media/'

# Absolute path to the directory that holds static files like app media.
# Example: "/home/media/media.lawrence.com/apps/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static_root')

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = 'http://s.apprl.com/'

# Additional directories which hold static files
STATICFILES_DIRS = (
    ('', os.path.join(PROJECT_ROOT, 'static')),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Django-storages
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
AWS_ACCESS_KEY_ID = 'AKIAIK3KEJCJEMGA2LTA'
AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME = AWS_S3_CUSTOM_DOMAIN = 's.apprl.com'
AWS_HEADERS = {
        'Expires': 'Sat, Nov 01 2014 20:00:00 GMT',
        'Cache-Control': 'max-age=86400, public',
}
AWS_QUERYSTRING_AUTH = False
AWS_S3_SECURE_URLS = False
# TODO: use if django-storages is upgraded
#AWS_PRELOAD_METADATA = True
STATICFILES_STORAGE = 'storage.CachedStaticS3BotoStorage'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'zb*p6d^l!by6hhugm+^f34m@-yex9c90yz)c_71t=+lxo%mn(3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
   ('django.template.loaders.cached.Loader', (
       'django.template.loaders.filesystem.Loader',
       'django.template.loaders.app_directories.Loader',
   )),
)
TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.core.context_processors.static",
    "context_processors.exposed_settings",
    "context_processors.next_redirects",
    "context_processors.gender",
    "context_processors.currency",
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'profile.middleware.ImpersonateMiddleware',
    'profile.middleware.LoginFlowMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'profile.auth.FacebookProfileBackend',
    'django.contrib.auth.backends.ModelBackend',
)


ROOT_URLCONF = 'apparelrow.urls'

INSTALLED_APPS = (
    # Django
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.flatpages',
    'django.contrib.comments',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',

    # External
    'mptt',                 # External: Category tree
    'sorl.thumbnail',       # External: Thumbnail module
    'djcelery',
    'tagging',
    'django_extensions',    # External: Used for auto-slug field
    'south',                # External: Database migration
    'modeltranslation',     # External: Used for category translation
    'jsmin',
    'pipeline',
    'storages',
    'static_sitemaps',

    # Internal
    'apparel',              # Internal: Product display module
    'profile',              # Internal: User related module
    'importer',             # Internal: Product importer module
    'apparel_comments',
    'statistics',           # Internal: Click statistics module
    'newsletter',
    'dashboard',

    'activity_feed',
)

COMMENTS_APP = 'apparel_comments'

# - STATIC SITEMAP -
STATICSITEMAPS_DOMAIN = 'apprl.com'
STATICSITEMAPS_ROOT_SITEMAP = 'apparelrow.sitemaps.sitemaps'
STATICSITEMAPS_ROOT_DIR = os.path.join(PROJECT_ROOT, 'sitemaps')
STATICSITEMAPS_USE_GZIP = True
STATICSITEMAPS_PING_GOOGLE = False
STATICSITEMAPS_REFRESH_AFTER = 60 * 8 # 8 hours in minutes

# - PIPELINE SETTINGS -
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.jsmin.JSMinCompressor'
PIPELINE_JS = {
    'apparel': {
        'source_filenames': ('js/apparel.js',),
        'output_filename': 'js/compiled/apparel.js',
    },
    'widget': {
        'source_filenames': ('js/jquery/jquery-1.8.2.min.js',
                             'js/widget.js'),
        'output_filename': 'js/compiled/widget.js',
    },
    'embed': {
        'source_filenames': ('js/embed.js',
                             'js/jquery/jquery.apprl-tooltip.js'),
        'output_filename': 'js/compiled/embed.js',
    },
    'jquery': {
        'source_filenames': ('js/jquery/jquery.hypersubmit.js',
                             'js/jquery/jquery.tools.min.js',
                             'js/jquery/jquery.tmpl.js',
                             'js/jquery/jquery.history.js',
                             'js/jquery/jquery.html5-placeholder-shim.js',
                             'js/jquery/jquery.autosize-min.js',
                             'js/jquery/jquery.scrollable.js',
                             'js/jquery/jquery.apprl-sticky.js',
                             'js/jquery/jquery.apprl-tooltip.js'),
        'output_filename': 'js/compiled/jquery.js',
    },
    'look_editor': {
        'source_filenames': ('js/vendor/underscore.js',
                             'js/vendor/json2.js',
                             'js/vendor/backbone.js',
                             'js/vendor/backbone-localstorage.js',
                             'js/vendor/jquery.iframe-transport.js',
                             'js/vendor/jquery.fileupload.js',
                             'js/jquery/jquery.ui.rotatable.js',
                             'js/app/main.js',
                             'js/app/models/product_filter.js',
                             'js/app/models/facet.js',
                             'js/app/models/product.js',
                             'js/app/models/facet_container.js',
                             'js/app/models/look.js',
                             'js/app/models/look_component.js',
                             'js/app/collections/facets.js',
                             'js/app/collections/products.js',
                             'js/app/collections/look_components.js',
                             'js/app/views/popup_dispatcher.js',
                             'js/app/views/dialog_reset.js',
                             'js/app/views/dialog_delete.js',
                             'js/app/views/dialog_unpublish.js',
                             'js/app/views/dialog_save.js',
                             'js/app/views/dialog_login.js',
                             'js/app/views/look_edit_filter_tabs.js',
                             'js/app/views/filter_product.js',
                             'js/app/views/filter_product_category.js',
                             'js/app/views/filter_product_subcategory.js',
                             'js/app/views/filter_product_color.js',
                             'js/app/views/filter_product_manufacturer.js',
                             'js/app/views/filter_product_price.js',
                             'js/app/views/products.js',
                             'js/app/views/product.js',
                             'js/app/views/temporary_image_upload_form.js',
                             'js/app/views/look_edit.js',
                             'js/app/views/look_edit_popup.js',
                             'js/app/views/look_component.js',
                             'js/app/views/look_component_photo.js',
                             'js/app/views/look_component_collage.js',
                             'js/app/look_editor.js',
                             ),
        'output_filename': 'js/compiled/look_editor.js',
    },
}

CSRF_FAILURE_VIEW = 'apparel.views.csrf_failure'

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = DEBUG
CONTACT_EMAIL = "support@hanssonlarsson.se"

# ACCOUNT/LOGIN AND OTHER STUFF
LOGIN_REDIRECT_URLNAME = "what_next"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

AUTH_USER_MODEL = 'profile.User'

# django-modeltranslation
TRANSLATION_REGISTRY = 'apparel.translation'

# django-tinymce
TINYMCE_DEFAULT_CONFIG = {
    'theme': 'advanced'
}

# FACEBOOK CONFIGURATION
FACEBOOK_APP_ID = '177090790853'
FACEBOOK_API_KEY = '44d47ef3e7285cace9a4c7c88f645742'
FACEBOOK_SECRET_KEY = '1701399a0a6126f84d08d7e702285c56'
FACEBOOK_SCOPE = 'email,publish_actions'
FACEBOOK_OG_TYPE = 'apprlcom'

# EMAIL CONFIGURATION
DEFAULT_FROM_EMAIL = 'Apprl <no-reply@apprl.com>'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_HOST_USER     = 'postman@apparelrow.com'
EMAIL_HOST_PASSWORD = 'apprl2010'
EMAIL_USE_TLS       = True

MAILCHIMP_API_KEY = '320bdd6a4c1815a8f093f1c29e1fc08f-us4'
MAILCHIMP_API_URL = 'http://us4.api.mailchimp.com/1.3/'
MAILCHIMP_MEMBER_LIST = '18083c690f'
MAILCHIMP_NEWSLETTER_LIST = '6fa805a815'

# CACHE CONFIGURATION
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 12,
    }
}

# GOOGLE ANALYTICS CONFIGURATION
APPAREL_DOMAIN = '.apprl.com' # FIXME: We should probably get this from the Sites framework
GOOGLE_ANALYTICS_ACCOUNT = 'UA-21990268-1'
GOOGLE_ANALYTICS_DOMAIN = APPAREL_DOMAIN

# SOLR COMMON
SOLR_RELOAD_URL = 'http://localhost:8983/solr/admin/cores?action=RELOAD&core=collection1'

# DASHBOARD
APPAREL_DASHBOARD_CUT_DEFAULT = 0.5
APPAREL_DASHBOARD_MINIMUM_PAYOUT = 500 # SEK

# INTERNAL APPAREL CONFIGURATIONS
APPAREL_GENDER_COOKIE = 'gender'
APPAREL_MANUFACTURERS_PAGE_SIZE = 500
APPAREL_BASE_CURRENCY = 'SEK'
APPAREL_RATES_CACHE_KEY = 'currency_rates_base_%s' % (APPAREL_BASE_CURRENCY,)
APPAREL_FXRATES_URL = 'http://themoneyconverter.com/rss-feed/SEK/rss.xml'
APPAREL_DEFAULT_AVATAR = 'images/brand-avatar.png'
APPAREL_DEFAULT_AVATAR_MEDIUM = 'images/brand-avatar-medium.png'
APPAREL_DEFAULT_AVATAR_LARGE = 'images/brand-avatar-large.png'
APPAREL_DEFAULT_BRAND_AVATAR = 'images/brand-avatar.png'
APPAREL_DEFAULT_BRAND_AVATAR_MEDIUM = 'images/brand-avatar-medium.png'
APPAREL_DEFAULT_BRAND_AVATAR_LARGE = 'images/brand-avatar-large.png'
APPAREL_MISC_IMAGE_ROOT = 'static/images'
APPAREL_BACKGROUND_IMAGE_ROOT = 'static/images/background'
APPAREL_TEMPORARY_IMAGE_ROOT = 'static/images/temp'
APPAREL_PRODUCT_IMAGE_ROOT = 'static/products'
APPAREL_LOOK_IMAGE_ROOT = 'static/looks'
APPAREL_EMAIL_IMAGE_ROOT = 'static/email'
APPAREL_LOGO_IMAGE_ROOT = 'static/logos'
APPAREL_PROFILE_IMAGE_ROOT ='static/profile'
APPAREL_LOOK_MAX_SIZE = 470
APPAREL_LOOK_FEATURED = 3
APPAREL_LOOK_SIZE = (696, 526)
APPAREL_IMPORTER_WAREHOUSE = os.path.join(PROJECT_ROOT, '..', '..', '..', 'shared', 'warehouse')
APPAREL_IMPORTER_COLORS = (
    (u'black'  , u'svart', u'night', u'coal',),
    (u'grey'   , u'grå', u'mörkgrå', u'ljusgrå', u'gray', u'smut', u'charcoal', u'meadow', u'thyme', u'stone', u'cement', u'slate', u'salvia',),
    (u'white'  , u'vit', u'chalk',),
    (u'beige'  , u'khaki', u'sand', u'creme', u'camel', u'rye', u'chino', u'oatmeal',),
    (u'brown'  , u'brun', u'mörkbrun', u'ljusbrun', u'chocolate', u'hickory', u'chicory', u'rum', u'herb',),
    (u'red'    , u'röd', u'mörkröd', u'merlot', u'wine', u'bubble gum',),
    (u'yellow' , u'gul',),
    (u'green'  , u'grön', u'ljusgrön', u'mörkgrön', u'olive', u'oliv', u'arme', u'army', u'armé', u'sage', u'fatigue', u'military',),
    (u'blue'   , u'blå', u'navy', u'bahama', u'sapphire', u'mörkblå', u'ljusblå'),
    (u'silver' , u'silver',),
    (u'gold'   , u'guld',),
    (u'pink'   , u'rosa', u'cerise', u'ceris',),
    (u'orange' , u'tangerine', ),
    (u'magenta', u'magenta',),
)
APPAREL_DECOMPRESS_UTILS = {
    'gzip': '/usr/bin/gunzip',
    'zip':  '/usr/bin/unzip',
}
APPAREL_DECOMPRESS_SUFFIX = {
    'gzip': '.gz',
    'zip': '.zip',
}

# THUMBNAIL CONFIGURATION
THUMBNAIL_ENGINE = 'apparel.sorl_extension.Engine'
THUMBNAIL_BACKEND = 'apparel.sorl_extension.NamedThumbnailBackend'
THUMBNAIL_PREFIX = 'cache/'

# FEED
FEED_REDIS_DB = 1

# CELERY CONFIGURATION
CELERY_DEFAULT_QUEUE = 'standard'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'standard'
CELERY_CREATE_MISSING_QUEUES = True
CELERY_QUEUES = {
    'celery': {'exchange': 'celery', 'exchange_type': 'direct', 'routing_key': 'celery'},
}
CELERY_ROUTES = ({
    'apparel.tasks.ProcessPopularityTask': {'queue': 'importer'},
    'apparel.tasks.ProcessLookPopularity': {'queue': 'importer'},
    'static_sitemaps.tasks.GenerateSitemap': {'queue': 'importer'},
    'profile.notifications.process_comment_look_comment': {'queue': 'standard'},
    'profile.notifications.process_comment_look_created': {'queue': 'standard'},
    'profile.notifications.process_comment_product_comment': {'queue': 'standard'},
    'profile.notifications.process_comment_product_wardrobe': {'queue': 'standard'},
    'profile.notifications.process_follow_user': {'queue': 'standard'},
    'profile.notifications.process_like_look_created': {'queue': 'standard'},
    'profile.views.send_email_confirm_task': {'queue': 'standard'},
    'apparel.email.mailchimp_subscribe': {'queue': 'standard'},
    'apparel.email.mailchimp_unsubscribe': {'queue': 'standard'},
    'apparel.facebook_push_graph': {'queue': 'standard'},
    'apparel.facebook_pull_graph': {'queue': 'standard'},
    'apparel.tasks.generate_brand_list_template': {'queue': 'standard'},
},)

# LOGGING CONFIGURATION
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
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
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'NOTSET',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'app_core': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': '../../../var/logs/app_logger.log',
            'maxBytes': 3000000,
            'backupCount': 8
        },
        'importer': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': '../../../var/logs/importer.log',
            'maxBytes': 3000000,
            'backupCount': 8
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'dashboard': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': '../../../var/logs/dashboard.log',
            'maxBytes': 3000000,
            'backupCount': 8,
        },
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['app_core'],
        },
        'pysolr': {
            'level': 'ERROR',
            'propagate': False,
            'handlers': ['app_core'],
        },
        'django': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['app_core'],
        },
        'django.request': {
            'level': 'ERROR',
            'propagate': False,
            'handlers': ['mail_admins', 'app_core'],
        },
        'apparel.importer': {
            'level': 'INFO',
            'propagate': False,
            'handlers': ['importer', 'console'],
        },
        'dashboard': {
            'level': 'DEBUG',
            'propgate': False,
            'handlers': ['dashboard'],
        },
    }
}
