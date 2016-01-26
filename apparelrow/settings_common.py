# -*- coding: utf-8 -*-

import sys
import os.path
import posixpath

gettext = lambda s: s

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SERVER_APP_ROOT = os.path.join(PROJECT_ROOT, '..')

WSGI_APPLICATION = 'apparelrow.wsgi.application'

DEBUG = False
TEMPLATE_DEBUG = DEBUG

FORCE_SCRIPT_NAME = ''

ADMINS = (
    # ('Joel Bohman', 'joelboh@gmail.com'),
    ('Klas Wikblad', 'klas@apprl.com'),
    ('Emily Benitez', 'emily@apprl.com'),
)

MANAGERS = ADMINS + (
    ('Martin', 'martin@apprl.com'),
    ('Gustav', 'gustav@apprl.com'),
)

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
DECIMAL_SEPARATOR = '.'

# Locale paths
LOCALE_PATHS = (
    os.path.join(SERVER_APP_ROOT, 'var', 'locale'),
)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', gettext(u'English ($)')),
    ('sv', gettext(u'Swedish (SEK)')),
    ('da', gettext(u'Danish (DKK)')),
    ('no', gettext(u'Norwegian (NOK)')),
    ('fi', gettext(u'Finnish (EUR)')),
)

# These languages get static templates in solr
LANGUAGES_DISPLAY = (
    ('en', gettext(u'English ($)')),
    ('sv', gettext(u'Swedish (SEK)')),
    ('da', gettext(u'Danish (DKK)')),
    ('no', gettext(u'Norwegian (NOK)')),
    ('fi', gettext(u'Finnish (EUR)')),
)
SHORT_LANGUAGES = (
    ('en', gettext(u'Eng ($)')),
    ('sv', gettext(u'Swe (SEK)')),
    ('da', gettext(u'Dnk (DKK)')),
    ('no', gettext(u'Nor (NOK)')),
    ('fi', gettext(u'Fin (EUR)')),
)
SHORT_LANGUAGES_DISPLAY = (
    ('en', gettext(u'Eng ($)')),
    ('sv', gettext(u'Swe (SEK)')),
    ('da', gettext(u'Dnk (DKK)')),
    ('no', gettext(u'Nor (NOK)')),
    ('fi', gettext(u'Fin (EUR)')),
)
SHORT_LANGUAGES_LIST_DISPLAY = ('en', 'sv', 'no')
LANGUAGE_TO_CURRENCY = {
    'en': 'USD',
    'sv': 'SEK',
    'da': 'DKK',
    'no': 'NOK',
    'fi': 'EUR',
}
MAX_MIN_CURRENCY = {
    'en': 1000,
    'sv': 10000,
    'da': 10000,
    'no': 10000,
    'fi': 1000,
}

VENDOR_LOCATION_MAPPING = {
    "Shirtonomy": ["DK", "SE"],
    "Ted & Teresa": ["SE"],
    "ConfidentLiving": ["SE"],
    "MQ": ["SE"],
    "Care of Carl": ["SE", "NO"],
    "ALDO": ["US"],
    "ASOS": ["FI", "SE", "NO", "DK", "ALL"],
    "Eleven": ["SE"],
    "Happy Socks": ["SE"],
    "Elevenfiftynine": ["SE"],
    "Frontmen": ["ALL", "SE", "NO", "DK", "FI"],
    "Flattered": ["SE", "DK", "NO", "FI", "ALL"],
    "Filippa K": ["SE"],
    "Filippa K DK": ["DK"],
    "Filippa K NO": ["NO"],
    "JC": ["SE"],
    "Nelly": ["SE"],
    "Nelly No": ["NO"],
    "Gina Tricot NO": ["NO"],
    "Gina Tricot SE": ["SE"],
    "Gina Tricot DK": ["DK"],
    "Gina Tricot FI": ["FI"],
    "Panos Emporio": ["SE"],
    "Boozt se": ["SE"],
    "Boozt no": ["NO"],
    "Boozt dk": ["DK"],
    "ASOS no": ["NO"],
    "QVC": ["US"],
    "Room 21 no": ["NO"],
    "Rum 21 se": ["SE"],
    "default": ["ALL", "SE", "NO", "US", "DK", "FI"],
}

LOCATION_MAPPING = (
    ('SE', gettext('Sweden (SEK)')),
    ('DK', gettext('Denmark (DKK)')),
    ('NO', gettext('Norway (NOK)')),
    ('FI', gettext('Finland (EUR)')),
    ('US', gettext('USA (USD)')),
    ('ALL', gettext('International (USD)')),
)

LOCATION_LANGUAGE_MAPPING = (
    ("SE", gettext("Sweden (SEK)"), LANGUAGES_DISPLAY[1]),
    ("DK", gettext("Denmark (DKK)"), LANGUAGES_DISPLAY[2]),
    ("NO", gettext("Norway (NOK)"), LANGUAGES_DISPLAY[3]),
    ("FI", gettext("Finland (EUR)"), LANGUAGES_DISPLAY[4]),
    ("US", gettext("USA (USD)"), LANGUAGES_DISPLAY[0]),
    ("ALL", gettext("International (USD)"), LANGUAGES_DISPLAY[0]),
)

# Locale url plugin
LOCALEURL_USE_ACCEPT_LANGUAGE = True
LOCALEURL_USE_SESSION = True
LOCALE_INDEPENDENT_PATHS = (
    r'^/backend/',
    r'^/products/[\d]+/(like|unlike)',
    r'^/looks/[\w-]+?/(like|unlike)',
    r'^/sitemap',
    r'^/embed',
    r'^/images/temporary/',
    r'^/a/link',
    r'^/a/conversion',
    r'^/track/',
)
LOCALEURL_SUPPORTED_LOCALES = LANGUAGES



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

    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Django-storages
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
# AWS_ACCESS_KEY_ID = 'AKIAIK3KEJCJEMGA2LTA'
# AWS_SECRET_ACCESS_KEY = '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'
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME = AWS_S3_CUSTOM_DOMAIN = 's.apprl.com'
AWS_HEADERS = {
    'Expires': 'Sat, Nov 01 2016 20:00:00 GMT',
    'Cache-Control': 'max-age=86400, public',
}
AWS_QUERYSTRING_AUTH = False
AWS_S3_SECURE_URLS = False
# TODO: use if django-storages is upgraded
#AWS_PRELOAD_METADATA = True
STATICFILES_STORAGE = 'apparelrow.storage.CachedStaticS3BotoStorage'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'zb*p6d^l!by6hhugm+^f34m@-yex9c90yz)c_71t=+lxo%mn(3'

# List of callables that know how to import templates from various sources.
'''TEMPLATE_LOADERS = (
   ('django.template.loaders.cached.Loader', (
       'django.template.loaders.filesystem.Loader',
       'django.template.loaders.app_directories.Loader',
   )),
)'''
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
    "django.contrib.messages.context_processors.messages",
    "apparelrow.context_processors.exposed_settings",
    "apparelrow.context_processors.next_redirects",
    "apparelrow.context_processors.currency",
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'localeurl.middleware.LocaleURLMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
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

AUTHENTICATION_BACKENDS = (
    'apparelrow.profile.auth.FacebookProfileBackend',
    'apparelrow.profile.auth.UsernameAndEmailBackend',
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
    'mptt',  # External: Category tree
    'sorl.thumbnail',  # External: Thumbnail module
    'djcelery',
    'tagging',
    'django_extensions',  # External: Used for auto-slug field
    'south',  # External: Database migration
    'modeltranslation',  # External: Used for category translation
    'jsmin',
    'pipeline',
    'storages',
    'static_sitemaps',
    'djrill',
    'crispy_forms',
    'localeurl',
    'jsonfield',

    # Internal
    'theimp',
    'advertiser',
    'apparelrow.profile',  # Internal: User related module
    'apparelrow.apparel',  # Internal: Product display module
    'apparelrow.importer',  # Internal: Product importer module
    'apparelrow.statistics',  # Internal: Click statistics module
    'apparelrow.dashboard',
    'apparelrow.activity_feed',
    'apparelrow.scheduledjobs',
    'rosetta',
    'raven.contrib.django.raven_compat',
    'django_user_agents'
)

# - STATIC SITEMAP -
STATICSITEMAPS_DOMAIN = 'apprl.com'
STATICSITEMAPS_ROOT_SITEMAP = 'apparelrow.sitemaps.sitemaps'
STATICSITEMAPS_ROOT_DIR = os.path.join(PROJECT_ROOT, 'sitemaps')
STATICSITEMAPS_USE_GZIP = True
STATICSITEMAPS_PING_GOOGLE = False
STATICSITEMAPS_REFRESH_AFTER = 60  # every hour in minutes

# - PIPELINE SETTINGS -
PIPELINE_COMPILERS = (
    'pipeline.compilers.less.LessCompiler',
)
PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.cssmin.CSSMinCompressor'
PIPELINE_CSS = {
    'bootstrap': {
        'source_filenames': (
            'less/base.less',
            'js/vendor/add2home.css',
        ),
        'output_filename': 'css/ender.css',
        'extra_context': {
            'media': 'screen,projection',
        },
    },
    'homepage': {
        'source_filenames': (
            'less/home.less',
        ),
        'output_filename': 'css/home.css',
        'extra_context': {
            'media': 'screen,projection',
        }
    },
    'normalize': {
        'source_filenames': (
            'less/normalize.css',
        ),
        'output_filename': 'css/normalize.css',
        'extra_context': {
            'media': 'screen,projection',
        }
    }
}
#PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.jsmin.JSMinCompressor'
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'
PIPELINE_JS = {
    'bootstrap': {
        'source_filenames': ('bootstrap/js/transition.js',
                             'bootstrap/js/alert.js',
                             'bootstrap/js/modal.js',
                             'bootstrap/js/dropdown.js',
                             'bootstrap/js/scrollspy.js',
                             'bootstrap/js/tab.js',
                             'bootstrap/js/tooltip.js',
                             'bootstrap/js/popover.js',
                             'bootstrap/js/button.js',
                             'bootstrap/js/collapse.js',
                             'bootstrap/js/carousel.js',
                             'bootstrap/js/typeahead.js',
                             'bootstrap/js/affix.js'),
        'output_filename': 'js/compiled/b.js',
    },
    'embed': {
        'source_filenames': ('js/embed.js',
                             'js/jquery/jquery.apprl-tooltip.js'),
        'output_filename': 'js/compiled/embed.js',
    },
    'product_widget': {
        'source_filenames': ('js/product_widget.js',
                             'js/vendor/hammer.min.js'),
        'output_filename': 'js/compiled/product_widget.js',
    },
    'main': {
        'source_filenames': ('js/vendor/underscore.js',
                             'js/vendor/jquery-2.1.1.js',
                             'js/vendor/jquery-ui-1.9.2.custom.js',
                             'js/vendor/add2home.js',
                             'js/jquery/jquery.ui.touch-punch.min.js',
                             'js/jquery/jquery.cookie-1.4.1.min.js',
                             'js/vendor/detect-mobile.js',
                             'bootstrap/js/transition.js',
                             'bootstrap/js/alert.js',
                             'bootstrap/js/modal.js',
                             'bootstrap/js/dropdown.js',
                             'bootstrap/js/scrollspy.js',
                             'bootstrap/js/tab.js',
                             'bootstrap/js/tooltip.js',
                             'bootstrap/js/popover.js',
                             'bootstrap/js/button.js',
                             'bootstrap/js/collapse.js',
                             'bootstrap/js/carousel.js',
                             'bootstrap/js/typeahead.js',
                             'bootstrap/js/affix.js',
                             'js/vendor/jquery.history.js',
                             'js/jquery/jquery.infinitescroll.js',
                             #'js/jquery/jquery.html5-placeholder-shim.js',
                             #'js/jquery/jquery.autosize-min.js',
                             #'js/jquery/jquery.scrollable.js',
                             'js/jquery/jquery.iosslider.js',
                             'js/jquery/jquery.apprl-sticky.js',
                             'js/jquery/jquery.apprl-tooltip.js',
                             'js/jquery/jquery.textarea.js',
                             'js/apparel.js',
                             'js/filtersetup.js',
                             'js/browse.js',
        ),
        'output_filename': 'js/compiled/main.js',
    },
    'shop': {
        'source_filenames': ('js/vendor/jquery-2.1.1.js',
                             'js/vendor/jquery-ui-1.9.2.custom.js',
                             'js/jquery/jquery.ui.touch-punch.min.js',
                             'js/vendor/jquery.history.js',
                             'bootstrap/js/collapse.js',
                             'bootstrap/js/transition.js',
                             'js/filtersetup.js',
                             'js/browse.js',
                             'js/jquery/jquery.infinitescroll.js',),
        'output_filename': 'js/compiled/shop.js',
    },
    'create_store': {
        'source_filenames': (
            'js/vendor/underscore.js',
            'js/vendor/json2.js',
            'js/vendor/backbone.js',
            'js/vendor/backbone-localstorage.js',
            'js/vendor/jquery.iframe-transport.js',
            'js/vendor/jquery.fileupload.js',
            'js/jquery/jquery.ui.rotatable.js',
            'js/app/main.js',

            'js/app/base/models/WidgetModelBase.js',
            'js/app/base/models/product_filter.js',
            'js/app/base/models/facet.js',
            'js/app/base/models/product.js',
            'js/app/base/models/facet_container.js',
            'js/app/shop_editor/models/shop.js',
            'js/app/shop_editor/models/shop_component.js',
            'js/app/base/collections/facets.js',
            'js/app/base/collections/products.js',
            'js/app/shop_editor/collections/shop_components.js',
            'js/app/base/views/WidgetBase.js',
            'js/app/base/views/popup_dispatcher.js',
            'js/app/base/views/dialog_reset.js',
            'js/app/base/views/dialog_delete.js',
            'js/app/base/views/dialog_unpublish.js',
            'js/app/base/views/dialog_save.js',
            'js/app/base/views/dialog_login.js',
            'js/app/base/views/dialog_no_products.js',
            'js/app/shop_editor/views/shop_create.js',
            'js/app/shop_editor/views/shop_edit_popup.js',
            'js/app/look_editor/views/look_edit_filter_tabs.js',
            'js/app/base/views/header.js',
            'js/app/base/views/dialog_header_mobile.js',
            'js/app/base/views/filter_product.js',
            'js/app/base/views/filter_product_category.js',
            'js/app/base/views/filter_product_subcategory.js',
            'js/app/base/views/filter_product_color.js',
            'js/app/base/views/filter_product_manufacturer.js',
            'js/app/base/views/filter_product_price.js',
            'js/app/base/views/filter_product_reset.js',
            'js/app/base/views/products.js',
            'js/app/base/views/product.js',
            'js/app/shop_editor/views/shop_component.js',
            'js/app/shop_editor/views/shop_component_product.js',

            'js/app/shop_editor/shop_creator.js',
        ),
        'output_filename': 'js/compiled/create_store.js',
    },
    'create_product_widget': {
        'source_filenames': (
            'js/vendor/underscore.js',
            'js/vendor/json2.js',
            'js/vendor/backbone.js',
            'js/vendor/backbone-localstorage.js',
            'js/vendor/jquery.iframe-transport.js',
            'js/vendor/jquery.fileupload.js',
            'js/jquery/jquery.ui.rotatable.js',
            'js/vendor/hammer.min.js',
            'js/app/main.js',

            'js/app/base/models/WidgetModelBase.js',
            'js/app/base/models/product_filter.js',
            'js/app/base/models/facet.js',
            'js/app/base/models/product.js',
            'js/app/base/models/facet_container.js',
            'js/app/product_widget_editor/models/product_widget.js',
            'js/app/product_widget_editor/models/product_widget_component.js',
            'js/app/base/collections/facets.js',
            'js/app/base/collections/products.js',
            'js/app/product_widget_editor/collections/product_widget_components.js',
            'js/app/base/views/WidgetBase.js',
            'js/app/base/views/popup_dispatcher.js',
            'js/app/base/views/dialog_reset.js',
            'js/app/base/views/dialog_delete.js',
            'js/app/base/views/dialog_unpublish.js',
            'js/app/base/views/dialog_save.js',
            'js/app/base/views/dialog_login.js',
            'js/app/base/views/dialog_no_products.js',
            'js/app/product_widget_editor/views/product_widget_create.js',
            'js/app/product_widget_editor/views/product_widget_edit_popup.js',
            'js/app/look_editor/views/look_edit_filter_tabs.js',
            'js/app/base/views/header.js',
            'js/app/base/views/dialog_header_mobile.js',
            'js/app/base/views/filter_product.js',
            'js/app/base/views/filter_product_category.js',
            'js/app/base/views/filter_product_subcategory.js',
            'js/app/base/views/filter_product_color.js',
            'js/app/base/views/filter_product_manufacturer.js',
            'js/app/base/views/filter_product_price.js',
            'js/app/base/views/filter_product_reset.js',
            'js/app/base/views/products.js',
            'js/app/base/views/product.js',
            'js/app/product_widget_editor/views/product_widget_component.js',
            'js/app/product_widget_editor/views/product_widget_component_product.js',

            'js/app/product_widget_editor/product_widget_creator.js',
        ),
        'output_filename': 'js/compiled/create_product_widget.js',
    },
    'look_editor': {
        'source_filenames': ('js/vendor/underscore.js',
                             'js/vendor/json2.js',
                             'js/vendor/backbone.js',
                             'js/vendor/backbone-localstorage.js',
                             'js/vendor/jquery.iframe-transport.js',
                             'js/vendor/jquery.fileupload.js',
                             'js/jquery/jquery.ui.rotatable.js',
                             'js/vendor/hammer.min.js',
                             'js/app/main.js',
                             'js/app/base/models/WidgetModelBase.js',
                             'js/app/base/models/product_filter.js',
                             'js/app/base/models/facet.js',
                             'js/app/base/models/product.js',
                             'js/app/base/models/facet_container.js',
                             'js/app/look_editor/models/look.js',
                             'js/app/look_editor/models/look_component.js',
                             'js/app/base/collections/facets.js',
                             'js/app/base/collections/products.js',
                             'js/app/look_editor/collections/look_components.js',
                             'js/app/base/views/WidgetBase.js',
                             'js/app/base/views/popup_dispatcher.js',
                             'js/app/base/views/dialog_reset.js',
                             'js/app/base/views/dialog_delete.js',
                             'js/app/base/views/dialog_unpublish.js',
                             'js/app/base/views/dialog_save.js',
                             'js/app/base/views/dialog_login.js',
                             'js/app/base/views/dialog_no_products.js',
                             'js/app/look_editor/views/look_edit_filter_tabs.js',
                             'js/app/base/views/header.js',
                             'js/app/base/views/dialog_header_mobile.js',
                             'js/app/base/views/filter_product.js',
                             'js/app/base/views/filter_product_category.js',
                             'js/app/base/views/filter_product_subcategory.js',
                             'js/app/base/views/filter_product_color.js',
                             'js/app/base/views/filter_product_manufacturer.js',
                             'js/app/base/views/filter_product_price.js',
                             'js/app/base/views/filter_product_reset.js',
                             'js/app/base/views/products.js',
                             'js/app/base/views/product.js',
                             'js/app/look_editor/views/temporary_image_upload_form.js',
                             'js/app/look_editor/views/look_edit.js',
                             'js/app/look_editor/views/look_edit_popup.js',
                             'js/app/look_editor/views/look_component.js',
                             'js/app/look_editor/views/look_component_photo.js',
                             'js/app/look_editor/views/look_component_collage.js',
                             'js/app/look_editor/views/look_edit_toolbar.js',
                             'js/app/look_editor/views/custom_link.js',
                             'js/app/look_editor/look_editor.js',
        ),
        'output_filename': 'js/compiled/look_editor.js',
    },
}

CSRF_FAILURE_VIEW = 'apparelrow.apparel.views.csrf_failure'

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = DEBUG
CONTACT_EMAIL = "klas@apprl.com"

# ACCOUNT/LOGIN AND OTHER STUFF
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

AUTH_USER_MODEL = 'profile.User'

# django-modeltranslation
TRANSLATION_REGISTRY = 'apparelrow.apparel.translation'

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
FACEBOOK_APP_ACCESS_TOKEN = '177090790853|sX7Yr41ov0I_267HjmJYHs6GgO8'

# EMAIL CONFIGURATION
MANDRILL_API_KEY = '7dDF82r91MHKJ68Q0t6egQ'
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"
DEFAULT_FROM_EMAIL = 'Apprl <no-reply@apprl.com>'
SERVER_EMAIL = 'Apprl <no-reply@apprl.com>'
#EMAIL_HOST          = 'smtp.gmail.com'
#EMAIL_PORT          = 587
#EMAIL_HOST_USER     = 'postman@apparelrow.com'
#EMAIL_HOST_PASSWORD = 'apprl2010'
#EMAIL_USE_TLS       = True

MAILCHIMP_API_KEY = '320bdd6a4c1815a8f093f1c29e1fc08f-us4'
MAILCHIMP_API_URL = 'http://us4.api.mailchimp.com/1.3/'
MAILCHIMP_MEMBER_LIST = '18083c690f'
MAILCHIMP_NEWSLETTER_LIST = '6fa805a815'
MAILCHIMP_PUBLISHER_LIST = '9497b26019'

# CACHE CONFIGURATION
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
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

# GOOGLE ANALYTICS CONFIGURATION
APPAREL_DOMAIN = '.apprl.com'  # FIXME: We should probably get this from the Sites framework
GOOGLE_ANALYTICS_ACCOUNT = 'UA-21990268-1'
GOOGLE_ANALYTICS_DOMAIN = APPAREL_DOMAIN
GOOGLE_ANALYTICS_UNIVERSAL_ACCOUNT = 'UA-21990268-2'
GOOGLE_ANALYTICS_UNIVERSAL_DOMAIN = 'apprl.com'
GOOGLE_TAG_MANAGER_CONTAINER_ID = 'GTM-T2Q72N'

# Rosetta Google Translate
# To register a site https://ssl.bing.com/webmaster/home/mysites
ROSETTA_MESSAGES_PER_PAGE = 30
ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'en'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Engelska'
ROSETTA_WSGI_AUTO_RELOAD = False
ROSETTA_UWSGI_AUTO_RELOAD = False
ROSETTA_EXCLUDED_APPLICATIONS = ()
ROSETTA_REQUIRES_AUTH = True
ROSETTA_STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'
#ROSETTA_HOME = 'http://apprl.local.com/rosetta/'


# SOLR COMMON
#SOLR_HOSTNAME = '146.185.137.189'
SOLR_CURRENCY_LOCAL = True
SOLR_RELOAD_URL = 'http://127.0.0.1:8983/solr/admin/cores?action=RELOAD&core=collection1'

# ADVERTISER
APPAREL_ADVERTISER_MINIMUM_STORE_INVOICE = 60  # EUR

# DASHBOARD
APPAREL_DASHBOARD_CUT_DEFAULT = '0.67'
APPAREL_DASHBOARD_MINIMUM_PAYOUT = 100  # EUR
APPAREL_DASHBOARD_REFERRAL_CUT_DEFAULT = '0.15'
APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME = 'referral_cookie'
APPAREL_DASHBOARD_INITIAL_PROMO_COMMISSION = '50'
APPAREL_DASHBOARD_PENDING_AGGREGATED_DATA = 'cache_aggregated_link'

# INTERNAL APPAREL CONFIGURATIONS
APPAREL_DEFAULT_CLICKS_LIMIT = 7500
APPAREL_GENDER_COOKIE = 'gender'
APPAREL_MULTI_GENDER_COOKIE = 'multigender'
APPAREL_LOCATION_COOKIE = 'location'
APPAREL_PRODUCT_MAX_AGE = 24 * 60 * 60
APPAREL_MANUFACTURERS_PAGE_SIZE = 500
APPAREL_BASE_CURRENCY = 'SEK'
NGINX_SHOP_RESET_KEY = "shopembed-reset-%s"
APPAREL_RATES_CACHE_KEY = 'currency_rates_base_%s' % (APPAREL_BASE_CURRENCY,)
APPAREL_FXRATES_URL = 'http://themoneyconverter.com/rss-feed/SEK/rss.xml'
APPAREL_DEFAULT_AVATAR = 'images/brand-avatar.png'
APPAREL_DEFAULT_AVATAR_CIRCULAR = 'images/brand-avatar-circular.png'
APPAREL_DEFAULT_AVATAR_MEDIUM = 'images/brand-avatar-medium.png'
APPAREL_DEFAULT_AVATAR_MEDIUM_CIRCULAR = 'images/brand-avatar-medium-circular.png'
APPAREL_DEFAULT_AVATAR_LARGE = 'images/brand-avatar-large.png'
APPAREL_DEFAULT_AVATAR_LARGE_CIRCULAR = 'images/brand-avatar-large-circular.png'
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
APPAREL_PROFILE_IMAGE_ROOT = 'static/profile'
APPAREL_LOOK_MAX_SIZE = 470
APPAREL_LOOK_FEATURED = 3
APPAREL_LOOK_SIZE = (696, 526)
APPAREL_IMPORTER_WAREHOUSE = os.path.join(PROJECT_ROOT, '..', '..', '..', 'shared', 'warehouse')
APPAREL_IMPORTER_COLORS = (
    (u'black', u'svart', u'night', u'coal',),
    (u'grey', u'grå', u'mörkgrå', u'ljusgrå', u'gray', u'smut', u'charcoal', u'meadow', u'thyme', u'stone', u'cement',
     u'slate', u'salvia',),
    (u'white', u'vit', u'chalk',),
    (u'beige', u'khaki', u'sand', u'creme', u'camel', u'rye', u'chino', u'oatmeal',),
    (u'brown', u'brun', u'mörkbrun', u'ljusbrun', u'chocolate', u'hickory', u'chicory', u'rum', u'herb',),
    (u'red', u'röd', u'mörkröd', u'merlot', u'wine', u'bubble gum',),
    (u'yellow', u'gul',),
    (u'green', u'grön', u'ljusgrön', u'mörkgrön', u'olive', u'oliv', u'arme', u'army', u'armé', u'sage', u'fatigue',
     u'military',),
    (u'blue', u'blå', u'navy', u'bahama', u'sapphire', u'mörkblå', u'ljusblå'),
    (u'silver', u'silver',),
    (u'gold', u'guld',),
    (u'pink', u'rosa', u'cerise', u'ceris',),
    (u'orange', u'tangerine', ),
    (u'magenta', u'magenta',),
)
APPAREL_DECOMPRESS_UTILS = {
    'gzip': '/usr/bin/gunzip',
    'zip': '/usr/bin/unzip',
}
APPAREL_DECOMPRESS_SUFFIX = {
    'gzip': '.gz',
    'zip': '.zip',
}

# THUMBNAIL CONFIGURATION
THUMBNAIL_ENGINE = 'apparelrow.apparel.sorl_extension.Engine'
THUMBNAIL_BACKEND = 'apparelrow.apparel.sorl_extension.NamedThumbnailBackend'
THUMBNAIL_PREFIX = 'cache/'

# FEED
FEED_REDIS_DB = 1

# SPIDERPIG / THEIMP
THEIMP_REDIS_HOST = 'localhost'
THEIMP_REDIS_PORT = 6380
THEIMP_REDIS_DB = 10
THEIMP_QUEUE_PARSE = 'theimp.parse'
THEIMP_QUEUE_SITE = 'theimp.site'

# CELERY CONFIGURATION
CELERY_DEFAULT_QUEUE = 'standard'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'standard'
CELERY_CREATE_MISSING_QUEUES = True
CELERY_QUEUES = {
    'standard': {'exchange': 'standard', 'exchange_type': 'direct', 'routing_key': 'standard'},
    'background': {'exchange': 'background', 'exchange_type': 'direct', 'routing_key': 'background'},
}
CELERY_ROUTES = ({
                     'static_sitemaps.tasks.GenerateSitemap': {'queue': 'standard'},
                     'profile.notifications.process_comment_look_comment': {'queue': 'standard'},
                     'profile.notifications.process_comment_look_created': {'queue': 'standard'},
                     'profile.notifications.process_comment_product_comment': {'queue': 'standard'},
                     'profile.notifications.process_comment_product_wardrobe': {'queue': 'standard'},
                     'profile.notifications.process_follow_user': {'queue': 'standard'},
                     'profile.notifications.process_like_look_created': {'queue': 'standard'},
                     'profile.notifications.process_sale_alert': {'queue': 'standard'},
                     'profile.notifications.facebook_friends': {'queue': 'standard'},
                     'profile.views.send_email_confirm_task': {'queue': 'standard'},
                     'profile.views.send_welcome_email_task': {'queue': 'standard'},
                     'dashboard.tasks.send_email_task': {'queue': 'standard'},
                     'apparel.email.mailchimp_subscribe': {'queue': 'standard'},
                     'apparel.email.mailchimp_unsubscribe': {'queue': 'standard'},
                     'apparel.email.mailchimp_subscribe_members': {'queue': 'standard'},
                     'apparel.facebook_push_graph': {'queue': 'standard'},
                     'apparel.facebook_pull_graph': {'queue': 'standard'},
                     'apparelrow.apparel.tasks.google_analytics_event': {'queue': 'standard'},
                     'apparelrow.apparel.tasks.empty_embed_shop_cache': {'queue': 'standard'},
                     'apparelrow.apparel.tasks.empty_embed_look_cache': {'queue': 'standard'},
                     'apparelrow.apparel.tasks.look_popularity': {'queue': 'background'},
                     'apparelrow.apparel.tasks.product_popularity': {'queue': 'background'},
                     'apparelrow.apparel.tasks.build_static_look_image': {'queue': 'standard'},
                     'apparelrow.profile.tasks.mail_managers_task': {'queue': 'standard'},
                     'statistics.tasks.active_users': {'queue': 'standard'},
                     'advertiser.tasks.send_text_email_task': {'queue': 'standard'},
                     'advertiser.tasks.set_accepted_after_40_days': {'queue': 'standard'},
                     'apparelrow.activity_feed.tasks.featured_activity': {'queue': 'standard'},
                     'apparelrow.scheduledjobs.tasks.run_importer': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.initiate_products_importer': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.run_vendor_product_importer': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.popularity': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.check_availability': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.dashboard_import': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.dashboard_payment': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.vendor_check': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.clicks_summary': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.update_clicks_summary': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.recalculate_earnings': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.check_chrome_extension': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.collect_calculate_earnings': {'queue': 'background'},
                     'apparelrow.scheduledjobs.tasks.check_clicks_limit_per_vendor': {'queue': 'standard'},
                     'apparelrow.scheduledjobs.tasks.clearsessions': {'queue': 'background'},
                     'apparel.notifications.look_like_daily': {'queue': 'background'},
                     'apparel.notifications.look_like_weekly': {'queue': 'background'},
                     'apparel.notifications.product_like_daily': {'queue': 'background'},
                     'apparel.notifications.product_like_weekly': {'queue': 'background'},
                     'apparel.notifications.user_activity_daily': {'queue': 'background'},
                     'apparel.notifications.user_activity_weekly': {'queue': 'background'},
                     'apparel.notifications.earnings_daily': {'queue': 'background'},
                     'apparel.notifications.earnings_weekly': {'queue': 'background'}},)

# LOGGING CONFIGURATION
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'DEBUG',
        'handlers': ['sentry'],
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
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'NOTSET',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout
        },
        'app_core': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'app_logger.log'),
            'maxBytes': 3000000,
            'backupCount': 8
        },
        'apparel_debug': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'apparel_debug.log'),
            'maxBytes': 3000000,
            'backupCount': 8
        },
        'importer': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'importer.log'),
            'maxBytes': 8000000,
            'backupCount': 10
        },
        #'mail_admins': {
        #    'level': 'ERROR',
        #    'filters': ['require_debug_false'],
        #    'class': 'django.utils.log.AdminEmailHandler',
        #},
        'dashboard': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'dashboard.log'),
            'maxBytes': 3000000,
            'backupCount': 8,
        },
        'theimp': {
            'level': 'NOTSET',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'theimp.log'),
            'maxBytes': 50000000,
            'backupCount': 10,
        },
        'affiliate_networks': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'affiliate_networks.log'),
            'backupCount': 30,
        },
        'live_test': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'live_test.log'),
            'backupCount': 30,
        },
        'check_urls': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': os.path.join(SERVER_APP_ROOT, '..', 'logs', 'check_urls.log'),
            'maxBytes': 3000000,
            'backupCount': 8
        }
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['app_core', 'sentry'],
        },
        'requests': {
            'level': 'WARNING',
            'propagate': False,
            'handlers': ['app_core'],
        },
        'pysolr': {
            'level': 'WARNING',
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
            'handlers': ['app_core'],
        },
        'apparelrow': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': ['app_core'],
        },
        'advertiser': {
            'level': 'ERROR',
            'propagate': False,
            'handlers': ['app_core'],
        },
        'apparel.importer': {
            'level': 'INFO',
            'propagate': False,
            'handlers': ['importer', 'console'],
        },
        'dashboard': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': ['dashboard'],
        },
        'theimp': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['theimp'],
        },
        'affiliate_networks': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': ['affiliate_networks'],
        },
        'live_test': {
            'level': 'INFO',
            'propagate': False,
            'handlers': ['live_test'],
        },
        'url_redirect_tests': {
            'level': 'INFO',
            'propagate': False,
            'handlers': ['check_urls'],
        }
    }
}

GEOIP_URL = 'http://production-geoip.apprl.com/ip/%s'
GEOIP_DEBUG = False
GEOIP_RETURN_LOCATION = "ONLYFORDEBUG"
