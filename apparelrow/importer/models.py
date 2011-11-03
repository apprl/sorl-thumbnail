import sys, traceback, logging, decimal
from datetime import datetime

from django.conf import settings
from django.db import models, connection, transaction
from django.utils.translation import get_language, ugettext_lazy as _
from django.template.defaultfilters import slugify

from apparel import models as apparel
from importer.framework.provider import load_provider

logger = logging.getLogger('apparel.importer.models')

AVAILABLE_UTILS = [(v, v,) for v in settings.APPAREL_DECOMPRESS_UTILS.keys()]

class VendorFeed(models.Model):
    vendor   = models.ForeignKey(apparel.Vendor)
    name     = models.CharField(max_length=15, unique=True, help_text=_('a-z, 0-9 and _'))
    url      = models.CharField(max_length=2550)
    username = models.CharField(max_length=50, null=True, blank=True)
    password = models.CharField(max_length=50, null=True, blank=True)
    decompress = models.CharField(max_length=10, choices=AVAILABLE_UTILS, null=True, blank=True, help_text=_('Decompress the file before importing it'))
    provider_class = models.CharField(max_length=50)
    comment  = models.TextField(blank=True, default='')

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
        provider = None
        
        try:
            # First try specific provider dependent on the name
            try:
                name = slugify(self.name)
                provider = load_provider(name, self)
            # Fall back to generic provider provider if the specific one fails
            except Exception:
                logger.info("Couldnt find specific provider %s, falling back on generic one: %s" % 
                        (name, self.provider_class))
                provider = load_provider(self.provider_class, self)
            provider.run(from_warehouse=from_warehouse, for_date=for_date)
        except Exception, e:
            logger.fatal(unicode(e.__str__(), 'utf-8'))
            logger.debug(''.join(traceback.format_tb(sys.exc_info()[2])))
            log.messages.create(status='error', message='Fatal exception:\n%s' % e)
            log.status = 'failed'
        else:
            log.status = 'completed'
        finally:
            if provider:
                log.imported_products = provider.count
                        
            log.save()
            log = None


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
    imported_products = models.IntegerField(_('Products imported'), default=0, help_text=_('Number of products created or updated'))
    
    def save(self, *args, **kwargs):
        if self.status != 'running':
            self.end_time = datetime.utcnow()
        
        return super(ImportLog, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return u'%s - %s' % (self.vendor_feed, self.get_status_display())
    
    class Meta:
        get_latest_by = 'start_time'
        ordering = ['-start_time']


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
    
    def __unicode__(self):
        return u'[%20s] %s' % (self.get_status_display(), self.message)



class FXRate(models.Model):
    base_currency = models.CharField(_('Base currency'), max_length=3, null=False, blank=False)
    currency      = models.CharField(_('Currency'), max_length=3, null=False, blank=False)
    rate          = models.DecimalField(_('Exchange rate'), max_digits=10, decimal_places=6)
    
    
    def update_prices(self):
        """
        Update the price of all products whose original currency matches this
        """
        
        # NOTE: We should really execute the statement below, however MySQLs 
        # handling of the Decimal type is flawed. This issue is described here 
        # http://bugs.mysql.com/bug.php?id=24541 and seems to be fixed in 
        # MySQL 5.5, so maybe we whould update.
        # In the mean time, we execute this raw MySQL-specific query, rounding 
        # the result.
        
        #apparel.VendorProduct.objects.filter(
        #    original_currency=self.currency
        #).update( 
        #    price=1 / self.rate * models.F('original_price'),
        #    currency=self.base_currency
        #)
        
        cursor   = connection.cursor()
        affected = cursor.execute("""
            UPDATE
              %(table)s
            SET
                price    = Round(%(price)f * original_price)
              , currency = '%(base_currency)s'
            WHERE
              original_currency = '%(currency)s'
        """ % {
            'table': apparel.VendorProduct._meta.db_table,
            'currency': self.currency,
            'base_currency': self.base_currency,
            'price': 1 / self.rate
        })
        transaction.commit_unless_managed()
        
        logger.info('Converted %i prices in %s to %s' % (
            affected,
            self.currency,
            self.base_currency
        ))
    
    def convert(self, amount):
        """
        Converts the amount from currency to base_currency according to rate
        """
        # FIXME 2.7: Switch the two lines below once upgraded to 2.7 
        #return decimal.Decimal.from_float(float(1 / self.rate) * amount)
        return decimal.Decimal('%f' % (float(1 / self.rate) * amount))
    
    def __unicode__(self):
        return u'1 %s in %s = %f' % (
            self.base_currency,
            self.currency,
            self.rate
        )
    
    class Meta:
        unique_together = (('base_currency', 'currency'),)


class ColorMapping(models.Model):
    color = models.CharField(max_length=100, unique=True, null=False, blank=False)
    aliases = models.TextField(null=False, blank=False,
            help_text=_('Aliases should be separated with a single comma and no spaces, example: "svart,night,coal"'))

    def color_list(self):
        return [self.color] + self.aliases.split(',')

    def __unicode__(self):
        return u'%s: %s' % (self.color, self.aliases)
