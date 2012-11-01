from django.conf import settings
from storages.backends.s3boto import S3BotoStorage
from django.contrib.staticfiles.storage import CachedFilesMixin

class CachedStaticS3BotoStorage(CachedFilesMixin, S3BotoStorage):
    """Extends S3BotoStorage to save static files with hashed filenames."""
    # URL KORS LOKALT
    def url(self, name):
        return settings.STATIC_URL + '/' + name
