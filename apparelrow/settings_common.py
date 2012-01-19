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
    ('en', gettext('English')),
    ('sv', gettext('Swedish')),
)
SHORT_LANGUAGES = (
    ('en', gettext('Eng')),
    ('sv', gettext('Swe')),
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
   ('django.template.loaders.cached.Loader', (
       'django.template.loaders.filesystem.Loader',
       'django.template.loaders.app_directories.Loader',
   )),
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'apparelrow.middleware.SwedishOnlyLocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'trackback.middleware.PingbackUrlInjectionMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'beta.middleware.BetaMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'profile.auth.FacebookProfileBackend',
    'django.contrib.auth.backends.ModelBackend',
)


ROOT_URLCONF = 'apparelrow.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)

HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False
HAYSTACK_DEFAULT_OPERATOR = 'AND'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    
    "context_processors.exposed_settings",
    "context_processors.next_redirects",
    "context_processors.gender",
    
    "announcements.context_processors.site_wide_announcements",
)

INSTALLED_APPS = (
    # included
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.flatpages',
    'django.contrib.comments',
    
    # external
    'django_facebook',  # Only used for loading facebook js sdk through templatetags
#    'mailer',          # FIXME: Includes e-mail manager, set this up later
    'announcements',
    'pagination',
    'mptt',
    'sorl.thumbnail',

    'djcelery',
    'haystack',
    'actstream',
    'tagging',
    'pagination',
    'ajaxcomments',
    'django_extensions',
    'trackback',
    'south',
    'modeltranslation',
    'jsmin',
    'compress',

    'apparel',
    'beta',
    'scale',
    'watcher',
    'profile',
    'importer',
    'apparel_comments',
    'statistics',
    
        
    'tinymce',
    'flatpages_tinymce',
    'django.contrib.admin',
    'apparelrow',
)

COMMENTS_APP = 'apparel_comments'

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
                             'js/jquery/jquery.html5-placeholder-shim.js',
                             'js/jquery/autoresize.jquery.min.js',
                             'js/jquery/jquery.scrollable.js'),
        'output_filename': 'js/compiled/jquery.js',
    }
}

COMPRESS = True

CSRF_FAILURE_VIEW = 'apparel.views.csrf_failure'

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/profile/%s/" % o.username,
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
SITE_NAME = "Apparelrow"


# ACCOUNT/LOGIN AND OTHER STUFF
ACCOUNT_ACTIVATION_DAYS = 7

LOGIN_REDIRECT_URLNAME = "what_next"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

AUTH_PROFILE_MODULE='profile.ApparelProfile'

# django-modeltranslation
TRANSLATION_REGISTRY='translation'

# django-tinymce
TINYMCE_DEFAULT_CONFIG = {
    'theme': 'advanced'
}

# FACEBOOK CONFIGURATION
FACEBOOK_APP_ID = '177090790853'
FACEBOOK_API_KEY = '44d47ef3e7285cace9a4c7c88f645742'
FACEBOOK_SECRET_KEY = '1701399a0a6126f84d08d7e702285c56'
FACEBOOK_PERMS = ['email']

DEFAULT_FROM_EMAIL = 'Apparelrow <no-reply@apparelrow.com>'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_HOST_USER     = 'postman@apparelrow.com'
EMAIL_HOST_PASSWORD = 'lat3Del!vEry'
EMAIL_USE_TLS       = True

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_TEMPLATE_TIMEOUT = 60 * 15

APPAREL_DOMAIN = '.apparelrow.com' # FIXME: We should probably get this from the Sites framework
GOOGLE_ANALYTICS_ACCOUNT = 'UA-21990268-1'
GOOGLE_ANALYTICS_DOMAIN = APPAREL_DOMAIN


APPAREL_GENDER_COOKIE = 'gender'
APPAREL_MANUFACTURERS_PAGE_SIZE = 500
APPAREL_BASE_CURRENCY = 'SEK'
APPAREL_FXRATES_URL = 'http://themoneyconverter.com/SEK/rss.xml'
APPAREL_DEFAULT_AVATAR       = os.path.join('/', MEDIA_URL, 'images', 'avatar_small.png')
APPAREL_DEFAULT_AVATAR_LARGE = os.path.join('/', MEDIA_URL, 'images', 'avatar.jpg')
APPAREL_MISC_IMAGE_ROOT = 'static/images'
APPAREL_BACKGROUND_IMAGE_ROOT = 'static/images/background'
APPAREL_PRODUCT_IMAGE_ROOT = 'static/products'
APPAREL_LOOK_IMAGE_ROOT = 'static/looks'
APPAREL_LOGO_IMAGE_ROOT = 'static/logos'
APPAREL_PROFILE_IMAGE_ROOT='static/profile'
APPAREL_LOOK_MAX_SIZE      = 470
APPAREL_LOOK_FEATURED      = 3
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

