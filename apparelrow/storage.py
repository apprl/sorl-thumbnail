from django.conf import settings
from storages.backends.s3boto import S3BotoStorage
from django.contrib.staticfiles.storage import CachedFilesMixin
from pipeline.storage import PipelineMixin

class CachedStaticS3BotoStorage(PipelineMixin, CachedFilesMixin, S3BotoStorage):
    """Extends S3BotoStorage to save static files with hashed filenames."""
