import datetime
import os
import logging
import re
import traceback
import sys
import itertools

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction
from django.db.models import Q
from django.db.models.loading import get_model

from apparelrow.importer.framework import fetcher, parser
from apparelrow.importer.api import API, SkipProduct, ImporterError, IncompleteDataSet

logger = logging.getLogger('apparel.importer.provider')


def load_provider(name, feed):
    module = __import__('apparelrow.importer.framework.provider.%s' % name, fromlist = ['Provider'])   
    
    return module.Provider(feed)

class Provider(object):
    """
    Base class for data providers.
    
    Properties:
     - feed         importer.models.VendorFeed instance
     - file         File handle pointing to the downloaded feed file
     - name         Name of the module the provider belongs to
     - extension    File extensions used when saving the file
     - mapper       Data mapper class.
     - count        Number of products successfully imported
     - url          The feed URL
     - username     Username used to download feed
     - password     Password used to download feed
    
    Synopsis
    
        provider = load_provider('grandpa')
        provider.run(from_warehouse=True, date=datetime.now()) 
    
    """
    
    def __init__(self, feed, **kwargs):
        self.feed      = feed
        self.name      = re.sub(r'[^a-z0-9_]', '_', feed.vendor.name.lower())
        self.file      = None
        self.extension = None
        self.mapper    = None
        self.count     = 0

        self.product_ids = set(get_model('apparel', 'Product').objects.filter(vendors=self.feed.vendor_id, availability=True).values_list('id', flat=True))

    def __del__(self, *args, **kwargs):
        if self.file and not self.file.closed:
            self.file.close()
    
    @property
    def url(self):
        return self.feed.url
    
    @property
    def username(self):
        return self.feed.username
    
    @property
    def password(self):
        return self.feed.password
    
    @property
    def decompress(self):
        return self.feed.decompress

    def run(self, from_warehouse=False, for_date=None):
        """
        Entry point for the import process. This will retrieve the file from
        the Internet or the warehouse, then hand it to the process() method
        for parsing.     
        
         - from_warehouse  - load the file from the warehouse, not the url property
         - for_date        - use this as_of_date. Format: YYYY-MM-DD
        
        """
        # If we are not able to fetch the feed, set all products for this
        # vendor as sold out and re raise the exception
        try:
            self.fetch(from_warehouse=from_warehouse, for_date=for_date)
        except Exception:
            self.update_availability()
            raise

        # If we are not able to process the feed, set all products for this
        # vendor that have not yet been proccessed as sold out and re raise the
        # exception
        try:
            self.process()
        except Exception:
            self.update_availability()
            raise

        self.update_availability()

    @transaction.commit_on_success
    def update_availability(self):
        """
        Set all products found in database but not found in the feed to sold out.

        Performance upgrade: only print the product name, no need to also get
        the manufacturer name
        """
        for product_id in self.product_ids:
            product = get_model('apparel', 'Product').objects.get(pk=product_id)
            product.availability=False
            product.vendorproduct.update(availability=0)
            product.save()

            logger.debug('Setting availability for product %s to sold out' % (product.product_name,))

    def fetch(self, from_warehouse=False, for_date=None):
        """
        Retrieves a file from the Internet, stores it in the warehouse and 
        opens it for reading. The open file object is stored in the file property
        """
        # NOTE: 
        #  If anyone needs to override "fetch", it might be a good idea to
        #  move the warehouse bit out so it can be re-used. It won't really
        #  change between providers.

        if not for_date:
            for_date = datetime.datetime.utcnow()

        date = for_date.strftime('%Y-%m-%d')
        path = os.path.join(
            settings.APPAREL_IMPORTER_WAREHOUSE,
            self.name,
            '%s.%s' % (date, self.extension) if self.extension else date
        )
        
        fetcher.fetch_feed(self.url, path, 
            from_warehouse=from_warehouse,
            username=self.username,
            password=self.password,
            decompress=self.decompress
        )
        
        self.file = open(path, 'r')
        return True
        
    def process(self):
        """
        Processes the file and calls the data mapper for each record. This will
        in turn call import_data with the mapped record
        """
        raise Exception("process() has to be implemented by subclass")
    
    def import_data(self, record):
        """
        Imports the given record using the API. The record is first mapped
        using the configured data mapper.
        """
        try:
            prod_id = record['product']['product-id']
        except KeyError:
            prod_id = '[unknown]'
                
        try:
            api = API(import_log=self.feed.latest_import_log)
            product = api.import_dataset(record)
            self.product_ids.discard(product.id)
            del api
            del product

        except (SkipProduct, IncompleteDataSet) as e:
            self.feed.latest_import_log.messages.create(
                status='warning',
                message="Skipping product\nProduct: %s\nError:%s" % (prod_id, e)
            )
            logger.warning(u'Record skipped: %s', e)

            # Try to set availability to zero if product already exists
            try:
                product = get_model('apparel', 'Product').objects.get(static_brand__exact=record['product']['manufacturer'], sku__exact=record['product']['product-id'])
                product.availability=False
                product.vendorproduct.update(availability=0)
                product.save()
                logger.debug('Setting availability for product %s to sold out' % (product.product_name,))
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                pass

        except ImporterError as e:
            self.feed.latest_import_log.messages.create(
                status='error', 
                message="Product skipped due to unexpected errors\nProduct: %s\nError: %s" % (
                    prod_id, e
                )
            )

            # Try to set availability to zero if product already exists
            try:
                product = get_model('apparel', 'Product').objects.get(static_brand__exact=record['product']['manufacturer'], sku__exact=record['product']['product-id'])
                product.availability=False
                product.vendorproduct.update(availability=0)
                product.save()
                logger.debug('Setting availability for product %s to sold out' % (product.product_name,))
            except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
                pass

        except Exception as e:
            exc_info = sys.exc_info()

            self.feed.latest_import_log.messages.create(
                status='error',
                message=u"Aborting import due to unhandled error.\nProduct: %s\nError: %s\n\nStacktrace:\n%s" % (
                    prod_id, unicode(e.__str__(), 'utf-8'), ''.join(traceback.format_tb(exc_info[2]))
                )
            )

            # Try to set availability to zero if product already exists
            try:
                product = get_model('apparel', 'Product').objects.get(static_brand__exact=record['product']['manufacturer'], sku__exact=record['product']['product-id'])
                product.availability=False
                product.vendorproduct.update(availability=0)
                product.save()
                logger.debug('Setting availability for product %s to sold out' % (product.product_name,))
            except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
                logger.warning(u'Failed to cleanup product during during unknown exception: %s' % (e))

            raise exc_info[0], exc_info[1], exc_info[2]
        else:
            self.count += 1

class CSVProvider(Provider):
    """
    A provider that parses CSV files. 
    Example usage:
    
        from apparelrow.importer.framework.parser import utils
        
        class MyProvider(ProviderCSV):
            def __init__(self, *args, **kwargs):
                super(MyProvider, self).__init__(*args, **kwargs)
                self.dialect = utils.CSVPipeDelimited
                self.encoding = 'latin-1',
                self.fieldnames = (
                    'list', 'of', '#ignore1', 'column', '#ignore2', 'headers'
                )
    
    New fields
    
     - fieldnames       List of fieldnames that will map the column values. They need to be unique.
     - dialect          CSV dialect used to parse the source. See importer.framework.parser and csv.Dialect
     - encoding         Defaults to "utf-8".
    
    If fieldnames is omitted in subclass, the first row will be used as headers
         
    Merging
    It's possible to merge a row from the source file with a previous row by 
    implementing two methods in the sub class:
    
    - should_merge(self, new_record)
    Return True if new_record should merge with the base record (in self.record)
    
    - merge(self, new_record)
    Merge new_record into self.record. This routine will only be invoked if we 
    should merge. It will also be invoked for the first element, to allow for 
    setting up the required data structure.
    
    """
    
    def __init__(self, *args, **kwargs):
        super(CSVProvider, self).__init__(*args, **kwargs)
        
        self.extension  = 'csv'
        self.fieldnames = None   # If none, read from first line
        self.dialect    = None
        self.encoding   = 'utf-8'
        self.record     = None   # Used for merging
        self.unique_fields = None
    
    def process(self):
        
        csv_reader = parser.CSVParser(self.file, 
            dialect=self.dialect,
            fieldnames=self.fieldnames,
            encoding=self.encoding,
        )
        
        # FIXME: Add merge test for parsing using mockobejcts

        duplicate_storage = dict()
        for row in csv_reader:
            try:
                self.record = self.mapper(self, row).translate()
            except SkipProduct, e:
                logger.info('Skipped product during mapping: %s' % (e,))
                continue

            if self.unique_fields:
                unique_fields = self.unique_fields
                duplicate_key = tuple(self.record['product'][field] for field in unique_fields)
                if duplicate_key in duplicate_storage:
                    # FIXME: Replace...
                    logger.info('merge duplicate %s' % (duplicate_key,))
                    # ...with
                    # logger.debug(u"merge duplicate %s", duplicate_key)
                    # if you have an environment that can run the code..
                    self.merge_duplicate(duplicate_storage[duplicate_key], self.record)
                else:
                    duplicate_storage[duplicate_key] = self.record
            else:
                self.import_data(self.record)

        if self.unique_fields:
            for key, record in duplicate_storage.items():
                self.import_data(record)

    def merge_duplicate(self, old_record, new_record):
        pass
