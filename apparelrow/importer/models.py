from datetime import datetime

from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _

from apparel import models as apparel
from importer.framework.provider import load_provider



class VendorFeed(models.Model):
    vendor   = models.ForeignKey(apparel.Vendor)
    name     = models.CharField(max_length=15, unique=True, help_text=_('a-z, 0-9 and _'))
    url      = models.CharField(max_length=255)
    username = models.CharField(max_length=50, null=True, blank=True)
    password = models.CharField(max_length=50, null=True, blank=True)
    provider_class = models.CharField(max_length=50)
    
    @property
    def latest_import_log(self):
        """
        Returns the ImportLog for lastest import, completed or running
        """
        
        try:
            return self.import_log.latest()
        except ImportLog.DoesNotExist:
            pass        
    
    def __unicode__(self):
        return u'%s' % self.vendor.name
    
    def run_import(self, from_warehouse=False, for_date=None):
        log = self.import_log.create()
        
        try:
            load_provider(self.provider_class, self).run(from_warehouse=from_warehouse, for_date=for_date)
        except Exception, e:
            import sys, traceback
            traceback.print_tb(sys.exc_info()[2])
            log.messages.create(status='error', message='Fatal exception: %s' % e)
            log.status = 'failed'
        else:
            log.status = 'completed'
        
        log.save()




class ImportLog(models.Model):
    """
    Synopsis
    
        log = ImportLog()
        try:
            ... do work ...
        except:
            log.messages.add(status='error', message='some error')
            log.status = 'failure'
        else:
            log.status = 'complete'
        
        log.save()
            
    
    """
    STATUS = (
        ('running',   _('Running')),   # The import is currently running
        ('completed', _('Completed')), # The import has completed
        ('failed',    _('Failed')),    # There were fatal errors and the import did not complete
    )
    
    start_time   = models.DateTimeField(_('Start time'), auto_now_add=True)
    end_time     = models.DateTimeField(_('End time'), null=True)
    status       = models.CharField(max_length=10, choices=STATUS, default='running')
    vendor_feed  = models.ForeignKey(VendorFeed, related_name='import_log')
    
    def save(self, *args, **kwargs):
        if self.status != 'running':
            self.end_time = datetime.utcnow()
        
        return super(ImportLog, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return u'%s - %s' % (self.vendor_feed, dict(self.STATUS)[self.status])
    
    class Meta:
        get_latest_by = 'start_time'


class ImportLogMessage(models.Model):
    STATUS = (
        ('info',      _('Info')),                 # Information about the feed
        ('attention', _('Attention required')),   # Something needs fixing before it can be published
        ('error',     _('Error')),                # Something went wrong
        
    )
    import_log = models.ForeignKey(ImportLog, related_name='messages')
    status     = models.CharField(_('Status'), max_length=10, choices=STATUS, default='info')
    message    = models.TextField(_('Message'), null=True, blank=True)
    datetime   = models.DateTimeField(_('Date'), auto_now_add=True)


