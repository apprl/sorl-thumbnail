##
## The apparelrow Project
##

import os

gettext = lambda s: s

__install_dir = os.path.realpath(os.path.dirname(__file__))


DEBUG = True
TEMPLATE_DEBUG = DEBUG
FORCE_SCRIPT_NAME = ''

ADMINS = (
    ('Site Admin', 'admin@example.com'),
)

MANAGERS = ADMINS

# H&L: Standard setting
DATABASE_ENGINE = 'sqlite3'                 # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'apparelrow.db'     # Or path to database file if using sqlite3.
DATABASE_USER = ''                          # Not used with sqlite3.
DATABASE_PASSWORD = ''                      # Not used with sqlite3.
DATABASE_HOST = ''                          # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''                          # Set to empty string for default. Not used with sqlite3.


TIME_ZONE = 'Europe/Stockholm'

LANGUAGE_CODE = 'en'


SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.

USE_I18N = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"

MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'VNTg_UtKuARrlc0;oY1\8s5IF'

ROOT_URLCONF = 'apparelrow.urls'

TEMPLATE_DIRS = (
    os.path.join(__install_dir, 'templates'),
)


# FIXME: Specify list of languages
LANGUAGES = (
    ('sv', gettext('Swedish')),
    ('en', gettext('English')),
)



# --- DJANGO CMS 2 SETTINGS ---
CMS_TEMPLATES = (
    # SET THESE
    #('your_template.html',   gettext('Your Template')), 
)

CMS_MEDIA_PATH = '/admin_media/cms/'
#CMS_DEFAULT_TEMPLATE = 'your_template.html'     # SET THIS
CMS_PERMISSION = True
CMS_SOFTROOT = True
CMS_SHOW_START_DATE = True
CMS_SHOW_END_DATE = True
CMS_LANGUAGE_FALLBACK = True
CMS_DEFAULT_LANGUAGE = 'en'
CMS_PLACEHOLDER_CONF = {
    'content': {
        'plugins': ('TextPlugin'), # SET THESE
        'name': gettext("Content"),
    },
}

CMS_APPLICATIONS_URLS = (
    # SET THIS 
    # Lets the CMS handle define pages for 3rd party apps
    #('your.app.urls', 'Your app'),
)


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    "django.core.context_processors.request",

    "cms.context_processors.media",

    # YOUR CONTEXT PROCESSORS
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.multilingual.MultilingualURLMiddleware',
)



INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.comments',
    'django.contrib.markup',
    'tagging',

    # Basic apps
    'basic.blog',
    'basic.inlines',


    # CMS
    'cms',
    'cms.plugins.text',

    # YOUR MODULES HERE        

    'mptt',
    # Publisher *has* to be last for CMS 2 to work
    'publisher',

)


from settings_local import *
